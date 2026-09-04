import type { PageFrontmatter } from "./markdown.ts";

export type MemoryState = "candidate" | "confirmed" | "rejected";

export interface MemoryRecord {
  path: string;
  title: string;
  content: string;
  scope: string;
  confidence: string;
  status: string;
  memory_state: MemoryState;
  last_modified: string;
  tags: string[];
}

function asStringArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === "string" && value.trim()) return [value];
  return [];
}

export function isConfirmedMemory(frontmatter: PageFrontmatter): boolean {
  return (
    frontmatter.type === "memory" &&
    frontmatter.status === "reviewed" &&
    frontmatter.last_modified_by === "Human" &&
    asStringArray(frontmatter.tags).includes("memory-confirmed")
  );
}

export function confirmedMemoryText(records: MemoryRecord[], maxChars = 30000): string {
  const confirmed = records.filter((record) => record.memory_state === "confirmed");
  let out = "";
  for (const record of confirmed) {
    const section = `### ${record.title}\n适用范围：${record.scope || "未注明"}\n\n${record.content}\n\n`;
    if (out.length + section.length > maxChars) break;
    out += section;
  }
  return out.trim();
}
