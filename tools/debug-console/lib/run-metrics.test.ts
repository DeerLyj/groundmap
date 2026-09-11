import assert from "node:assert/strict";
import test from "node:test";
import { createRunMetrics } from "./run-metrics.ts";

test("run metrics accumulate provider turns", () => {
  let now = 1000;
  const metrics = createRunMetrics(() => now);
  metrics.recordToolCall();
  metrics.recordUsage({
    kind: "turn-end",
    reason: "stop",
    usage: { input_tokens: 10, cached_input_tokens: 4, output_tokens: 3 },
  });
  metrics.recordUsage({
    kind: "turn-end",
    reason: "stop",
    usage: { input_tokens: 20, cached_input_tokens: 6, output_tokens: 4 },
  });
  now = 2500;

  const end = metrics.withMetrics({ kind: "turn-end", reason: "stop" });
  assert.deepEqual(end.usage, {
    input_tokens: 30,
    cached_input_tokens: 10,
    output_tokens: 7,
    duration_ms: 1500,
    tool_calls: 1,
  });
});
