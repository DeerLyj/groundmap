/**
 * 从回答中提取“候选记忆”标记。
 * 只有模型明确输出 memory-candidate 代码块时才识别，普通文本不会被自动持久化。
 */
export interface MemoryCandidate {
  title: string;
  content: string;
  scope: string;
  confidence: "high" | "medium" | "low";
  state: "new" | "saved" | "ignored";
  path?: string;
  error?: string;
}

const BLOCK_RE = /```memory-candidate\s*\n([\s\S]*?)\n```/gi;

function validConfidence(value: unknown): value is MemoryCandidate["confidence"] {
  return value === "high" || value === "medium" || value === "low";
}

function parsePayload(raw: string): Omit<MemoryCandidate, "state"> | null {
  try {
    const value = JSON.parse(raw) as Record<string, unknown>;
    if (
      typeof value.title === "string" &&
      typeof value.content === "string" &&
      typeof value.scope === "string" &&
      validConfidence(value.confidence)
    ) {
      return {
        title: value.title.trim(),
        content: value.content.trim(),
        scope: value.scope.trim(),
        confidence: value.confidence,
      };
    }
  } catch {
    // Ignore malformed blocks; the answer itself remains visible.
  }
  return null;
}

export function extractMemoryCandidates(text: string): MemoryCandidate[] {
  const candidates: MemoryCandidate[] = [];
  for (const match of text.matchAll(BLOCK_RE)) {
    const parsed = parsePayload(match[1].trim());
    if (!parsed || !parsed.title || !parsed.content || !parsed.scope) continue;
    candidates.push({ ...parsed, state: "new" });
  }
  return candidates;
}

export function stripMemoryCandidateBlocks(text: string): string {
  return text.replace(BLOCK_RE, "").replace(/\n{3,}/g, "\n\n").trim();
}
