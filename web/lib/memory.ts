/**
 * 个人工作记忆的受控状态机。
 *
 * 记忆仍然是 wiki Markdown 页面；本模块只负责约束状态转换，
 * 不调用 LLM，也不把普通对话自动写入磁盘。
 */
import path from "node:path";
import { getPage, listPages, type PageFull } from "./kb-service";
import { readFile, writeFile } from "./kb";
import { parseMarkdown, serializeMarkdown, type PageFrontmatter } from "./markdown";
import { checkWritePermissionAsync } from "./permissions";
import { gitAddAndCommit, type CommitResult } from "./git";
import { todayISO } from "./conflict-rewrite";
import {
  isConfirmedMemory,
  type MemoryRecord,
  type MemoryState,
} from "./memory-model";

export {
  confirmedMemoryText,
  isConfirmedMemory,
  type MemoryRecord,
  type MemoryState,
} from "./memory-model";

export const MEMORY_CANDIDATE_DIR = "wiki/memory/candidates";
export const CONFIRMED_MEMORY_PATH = "wiki/memory/confirmed.md";

const MEMORY_PATH_RE = /^wiki\/memory\/(?:candidates\/)?[^/]+\.md$/;
const CANDIDATE_PATH_RE = /^wiki\/memory\/candidates\/[^/]+\.md$/;

export interface MemoryProposal {
  title: string;
  content: string;
  scope: string;
  confidence: "high" | "medium" | "low";
}

function asStringArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === "string" && value.trim()) return [value];
  return [];
}

function memoryState(frontmatter: PageFrontmatter): MemoryState {
  if (isConfirmedMemory(frontmatter)) {
    return "confirmed";
  }
  if (frontmatter.status === "deprecated") return "rejected";
  return "candidate";
}

export function isMemoryFrontmatter(frontmatter: PageFrontmatter): boolean {
  return frontmatter.type === "memory";
}

function isValidMemoryPath(relPath: string): boolean {
  return MEMORY_PATH_RE.test(relPath.replace(/\\/g, "/"));
}

function isCandidatePath(relPath: string): boolean {
  return CANDIDATE_PATH_RE.test(relPath.replace(/\\/g, "/"));
}

function slugifyTitle(title: string): string {
  const slug = title
    .normalize("NFKC")
    .trim()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
  return slug || "memory";
}

function validateProposal(proposal: MemoryProposal): string | null {
  if (!proposal || typeof proposal !== "object") return "invalid_proposal";
  if (typeof proposal.title !== "string" || proposal.title.trim().length < 2 || proposal.title.length > 120) {
    return "invalid_title";
  }
  if (typeof proposal.content !== "string" || proposal.content.trim().length < 2 || proposal.content.length > 4000) {
    return "invalid_content";
  }
  if (typeof proposal.scope !== "string" || proposal.scope.trim().length < 2 || proposal.scope.length > 80) {
    return "invalid_scope";
  }
  if (!["high", "medium", "low"].includes(proposal.confidence)) return "invalid_confidence";
  return null;
}

function asRecord(page: PageFull): MemoryRecord {
  const fm = page.frontmatter;
  return {
    path: page.path,
    title: String(fm.title || page.path),
    content: page.content.trim(),
    scope: String(fm.scope || ""),
    confidence: String(fm.confidence || "medium"),
    status: String(fm.status || "draft"),
    memory_state: memoryState(fm),
    last_modified: String(fm.last_modified || ""),
    tags: asStringArray(fm.tags),
  };
}

export async function listMemoryRecords(): Promise<MemoryRecord[]> {
  const pages = await listPages();
  const records: MemoryRecord[] = [];
  for (const meta of pages.filter((p) => p.type === "memory" && p.path !== CONFIRMED_MEMORY_PATH)) {
    const page = await getPage(meta.path);
    if (page && isMemoryFrontmatter(page.frontmatter)) records.push(asRecord(page));
  }
  return records.sort((a, b) => a.path.localeCompare(b.path));
}

export async function saveMemoryCandidate(
  proposal: MemoryProposal,
): Promise<{ ok: boolean; path?: string; commit?: CommitResult; error?: string }> {
  const validationError = validateProposal(proposal);
  if (validationError) return { ok: false, error: validationError };

  const stamp = Date.now().toString();
  const relPath = `${MEMORY_CANDIDATE_DIR}/${stamp}-${slugifyTitle(proposal.title)}.md`;
  if (!isCandidatePath(relPath)) return { ok: false, error: "invalid_path" };

  const frontmatter: PageFrontmatter = {
    title: proposal.title.trim(),
    type: "memory",
    created_date: todayISO(),
    last_modified: todayISO(),
    last_modified_by: "LLM",
    status: "draft",
    confidence: proposal.confidence,
    source_count: 0,
    sources: [],
    tags: ["memory-candidate"],
    scope: proposal.scope.trim(),
    memory_state: "candidate",
  };
  const raw = serializeMarkdown(frontmatter, `## 记忆内容\n\n${proposal.content.trim()}\n\n## 适用范围\n\n${proposal.scope.trim()}\n`);
  const permission = await checkWritePermissionAsync(relPath, raw);
  if (!permission.allowed) return { ok: false, error: "permission_denied" };
  try {
    await writeFile(relPath, raw);
  } catch {
    return { ok: false, error: "write_failed" };
  }
  const commit = await gitAddAndCommit([relPath], `memory: save candidate ${proposal.title.trim()}`);
  if (!commit.ok) return { ok: false, path: relPath, error: "commit_failed", commit };
  return { ok: true, path: relPath, commit };
}

export async function transitionMemory(
  relPath: string,
  action: "confirm" | "reject",
): Promise<{ ok: boolean; commit?: CommitResult; error?: string }> {
  const normalized = relPath.replace(/\\/g, "/");
  if (!isCandidatePath(normalized)) return { ok: false, error: "invalid_candidate_path" };
  const permission = await checkWritePermissionAsync(normalized);
  if (!permission.allowed) return { ok: false, error: "permission_denied" };

  let raw: string;
  try {
    raw = await readFile(normalized);
  } catch {
    return { ok: false, error: "read_failed" };
  }
  const parsed = parseMarkdown(raw);
  if (!isMemoryFrontmatter(parsed.frontmatter)) return { ok: false, error: "not_memory" };
  if (parsed.frontmatter.status !== "draft" || parsed.frontmatter.memory_state !== "candidate") {
    return { ok: false, error: "not_candidate" };
  }

  const next = { ...parsed.frontmatter };
  const tags = asStringArray(next.tags).filter((tag) => tag !== "memory-candidate" && tag !== "memory-rejected" && tag !== "memory-confirmed");
  if (action === "confirm") {
    next.status = "reviewed";
    next.last_modified_by = "Human";
    next.memory_state = "confirmed";
    next.memory_confirmed_date = todayISO();
    next.tags = [...tags, "memory-confirmed"];
  } else {
    next.status = "deprecated";
    next.last_modified_by = "Human";
    next.memory_state = "rejected";
    next.tags = [...tags, "memory-rejected"];
  }
  next.last_modified = todayISO();

  try {
    await writeFile(normalized, serializeMarkdown(next, parsed.content));
  } catch {
    return { ok: false, error: "write_failed" };
  }
  const commit = await gitAddAndCommit(
    [normalized],
    `memory: ${action === "confirm" ? "confirm" : "reject"} ${path.basename(normalized)}`,
  );
  if (!commit.ok) return { ok: false, error: "commit_failed", commit };
  return { ok: true, commit };
}
