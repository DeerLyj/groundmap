export type EvidenceLocator = Record<string, string | number | unknown[]>;

function normalizeEvidenceText(value: string): string {
  return value
    .replace(/!\[[^\]]*\]\((?:<[^>]+>|[^)]+)\)/g, "")
    .replace(/\^[hpcft]-[a-z0-9-]+/gi, "")
    .toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "");
}

function timecodeSeconds(value: string): number {
  const [hours, minutes, seconds] = value.split(":");
  return Number(hours) * 3600 + Number(minutes) * 60 + Number(seconds);
}

export function inferEvidenceTimestamp(content: string, beforeIndex: number): EvidenceLocator | null {
  const prefix = content.slice(0, beforeIndex);
  const pattern = /^###\s+(\d{2}:\d{2}:\d{2}\.\d{3})[–-](\d{2}:\d{2}:\d{2}\.\d{3})/gm;
  let match: RegExpExecArray | null;
  let latest: RegExpExecArray | null = null;
  while ((match = pattern.exec(prefix)) !== null) latest = match;
  return latest
    ? { kind: "audio", start: timecodeSeconds(latest[1]), end: timecodeSeconds(latest[2]) }
    : null;
}

export function bestEvidenceLocator(payload: Record<string, unknown> | null, sourceText: string): {
  locator: EvidenceLocator;
  assetPath?: string;
} | null {
  const needle = normalizeEvidenceText(sourceText);
  if (!payload || !needle) return null;
  const tokens = [...new Set(
    sourceText
      .replace(/\^[hpcft]-[a-z0-9-]+/gi, "")
      .split(/[^\p{L}\p{N}]+/u)
      .map(normalizeEvidenceText)
      .filter((token) => token.length >= 2),
  )];
  const candidates: Array<{ text: string; locator: EvidenceLocator; assetPath?: string }> = [];
  const items = Array.isArray(payload.items) ? payload.items : [];
  for (const item of items) {
    if (!item || typeof item !== "object") continue;
    const value = item as Record<string, unknown>;
    if (value.locator && typeof value.locator === "object") {
      candidates.push({ text: String(value.text || ""), locator: value.locator as EvidenceLocator });
    }
  }
  const segments = Array.isArray(payload.segments) ? payload.segments : [];
  for (const item of segments) {
    if (!item || typeof item !== "object") continue;
    const value = item as Record<string, unknown>;
    if (value.locator && typeof value.locator === "object") {
      candidates.push({ text: String(value.text || ""), locator: value.locator as EvidenceLocator });
    }
  }
  const assets = Array.isArray(payload.assets) ? payload.assets : [];
  for (const item of assets) {
    if (!item || typeof item !== "object") continue;
    const value = item as Record<string, unknown>;
    const ocr = value.ocr && typeof value.ocr === "object" ? value.ocr as Record<string, unknown> : null;
    const locators = Array.isArray(value.locators) ? value.locators : [];
    const locator = locators[0] && typeof locators[0] === "object"
      ? locators[0] as EvidenceLocator
      : { kind: "image" };
    candidates.push({
      text: String(ocr?.text || ""),
      locator,
      assetPath: typeof value.asset_path === "string" ? value.asset_path : undefined,
    });
  }

  let best: typeof candidates[number] | null = null;
  let bestScore = 0;
  for (const candidate of candidates) {
    const haystack = normalizeEvidenceText(candidate.text);
    const exactScore = haystack.includes(needle)
      ? needle.length
      : needle.includes(haystack) ? haystack.length : 0;
    const matchingTokens = exactScore ? [] : tokens.filter((token) => haystack.includes(token));
    const tokenScore = matchingTokens.length >= 2
      ? matchingTokens.reduce((sum, token) => sum + token.length, 0)
      : 0;
    const score = Math.max(exactScore, tokenScore);
    if (score > bestScore) {
      best = candidate;
      bestScore = score;
    }
  }
  if (!best) return null;
  return best.assetPath
    ? { locator: best.locator, assetPath: best.assetPath }
    : { locator: best.locator };
}
