import type { AgentEvent } from "./providers/types.ts";

type TurnEnd = Extract<AgentEvent, { kind: "turn-end" }>;

export function createRunMetrics(now: () => number = Date.now) {
  const startedAt = now();
  let inputTokens = 0;
  let cachedInputTokens = 0;
  let outputTokens = 0;
  let toolCalls = 0;

  return {
    recordUsage(evt: TurnEnd) {
      inputTokens += evt.usage?.input_tokens ?? 0;
      cachedInputTokens += evt.usage?.cached_input_tokens ?? 0;
      outputTokens += evt.usage?.output_tokens ?? 0;
    },
    recordToolCall() {
      toolCalls += 1;
    },
    withMetrics(evt: TurnEnd): TurnEnd {
      return {
        ...evt,
        usage: {
          input_tokens: inputTokens || undefined,
          cached_input_tokens: cachedInputTokens || undefined,
          output_tokens: outputTokens || undefined,
          duration_ms: now() - startedAt,
          tool_calls: toolCalls,
        },
      };
    },
  };
}
