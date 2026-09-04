import { test } from "node:test";
import assert from "node:assert/strict";
import { confirmedMemoryText, isConfirmedMemory, type MemoryRecord } from "./memory-model.ts";

test("只接受 Human reviewed + memory-confirmed 的长期记忆", () => {
  assert.equal(
    isConfirmedMemory({
      type: "memory",
      status: "reviewed",
      last_modified_by: "Human",
      tags: ["memory-confirmed"],
    }),
    true,
  );
  assert.equal(
    isConfirmedMemory({
      type: "memory",
      status: "reviewed",
      last_modified_by: "LLM",
      tags: ["memory-confirmed"],
    }),
    false,
  );
  assert.equal(
    isConfirmedMemory({
      type: "memory",
      status: "draft",
      last_modified_by: "LLM",
      tags: ["memory-candidate"],
    }),
    false,
  );
});

test("confirmedMemoryText 只汇总已确认记录并限制总长度", () => {
  const records: MemoryRecord[] = [
    {
      path: "wiki/memory/candidates/a.md",
      title: "工作偏好",
      content: "先给结论。",
      scope: "回答结构",
      confidence: "high",
      status: "reviewed",
      memory_state: "confirmed",
      last_modified: "2026-08-30",
      tags: ["memory-confirmed"],
    },
    {
      path: "wiki/memory/candidates/b.md",
      title: "候选",
      content: "不应注入。",
      scope: "回答结构",
      confidence: "low",
      status: "draft",
      memory_state: "candidate",
      last_modified: "2026-08-30",
      tags: ["memory-candidate"],
    },
  ];
  const out = confirmedMemoryText(records, 100);
  assert.match(out, /工作偏好/);
  assert.doesNotMatch(out, /不应注入/);
});
