import { fileExists, isReadableDir, readFile } from "./kb";
import { parseMarkdown } from "./markdown";
import {
  assetMimeType,
  derivedMarkdownForRaw,
  resolveMarkdownAssetPath,
} from "./evidence-path";
import {
  bestEvidenceLocator,
  inferEvidenceTimestamp,
  type EvidenceLocator,
} from "./evidence-locator";

export type { EvidenceLocator } from "./evidence-locator";

export interface EvidenceView {
  requestedPath: string;
  originalPath: string | null;
  markdownPath: string | null;
  content: string;
  mime: string | null;
  locator: EvidenceLocator | null;
}

async function readJson(path: string): Promise<Record<string, unknown> | null> {
  if (!(await fileExists(path))) return null;
  try {
    return JSON.parse(await readFile(path)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function sidecar(markdownPath: string, suffix: string): string {
  return markdownPath.replace(/\.md$/i, suffix);
}

function cleanAnchor(anchor?: string | null): string {
  return (anchor || "").replace(/^\^/, "");
}

function anchoredLine(content: string, anchor?: string | null): { line: string; index: number } | null {
  const clean = cleanAnchor(anchor);
  if (!clean) return null;
  const pattern = new RegExp(`^.*\\^${clean.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*$`, "m");
  const match = pattern.exec(content);
  return match ? { line: match[0], index: match.index } : null;
}

async function sourceFromManifest(markdownPath: string): Promise<string | null> {
  const manifest = await readJson(sidecar(markdownPath, ".source.json"));
  const source = manifest?.source_path;
  return typeof source === "string" && isReadableDir(source) && await fileExists(source)
    ? source
    : null;
}

export async function buildEvidenceView(
  requestedPath: string,
  anchor?: string | null,
  explicitLocator?: EvidenceLocator | null,
): Promise<EvidenceView | null> {
  if (!isReadableDir(requestedPath)) return null;

  let markdownPath: string | null = null;
  let originalPath: string | null = null;
  if (requestedPath.toLowerCase().endsWith(".md")) {
    if (await fileExists(requestedPath)) markdownPath = requestedPath;
    if (requestedPath.startsWith("raw/")) {
      const companion = derivedMarkdownForRaw(requestedPath);
      if (!markdownPath && companion && await fileExists(companion)) markdownPath = companion;
    }
  } else if (await fileExists(requestedPath)) {
    originalPath = requestedPath;
    const companion = derivedMarkdownForRaw(requestedPath);
    if (companion && await fileExists(companion)) markdownPath = companion;
  }

  if (markdownPath?.startsWith("derived/")) {
    originalPath = await sourceFromManifest(markdownPath) || originalPath;
  }
  if (!markdownPath && !originalPath) return null;

  let content = "";
  if (markdownPath) content = parseMarkdown(await readFile(markdownPath)).content;
  const anchorMatch = anchoredLine(content, anchor);
  let locator = explicitLocator || null;

  if (anchorMatch && markdownPath) {
    const imageMatch = /!\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))/.exec(anchorMatch.line);
    const imagePath = resolveMarkdownAssetPath(markdownPath, imageMatch?.[1] || imageMatch?.[2]);
    if (imagePath) {
      originalPath = imagePath;
      locator ||= { kind: "image" };
    }
    locator ||= inferEvidenceTimestamp(content, anchorMatch.index);

    if (!locator) {
      for (const suffix of [".evidence.json", ".transcript.json", ".visual.json"]) {
        const found = bestEvidenceLocator(await readJson(sidecar(markdownPath, suffix)), anchorMatch.line);
        if (found) {
          locator = found.locator;
          if (found.assetPath && isReadableDir(found.assetPath) && await fileExists(found.assetPath)) {
            originalPath = found.assetPath;
          }
          break;
        }
      }
    }
  }

  return {
    requestedPath,
    originalPath,
    markdownPath,
    content,
    mime: originalPath ? assetMimeType(originalPath) : null,
    locator,
  };
}
