import assert from "node:assert/strict";
import test from "node:test";
import {
  CHAT_HISTORY_KEY,
  chatContextKey,
  conversationMarkdown,
  loadChatSessions,
  saveChatSession,
  toStoredMessages,
  type ChatSession,
} from "./chat-history.ts";

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    value: (key: string) => values.get(key),
  };
}

function session(id: string, updatedAt: string): ChatSession {
  return {
    schemaVersion: 1,
    id,
    contextKey: chatContextKey("alpha", "project-a"),
    title: "第一条问题",
    createdAt: "2026-09-10T00:00:00.000Z",
    updatedAt,
    workspace: "alpha",
    projectId: "project-a",
    provider: "codex",
    model: "default",
    mode: "quick",
    networkMode: "local",
    messages: [
      { id: "u-1", role: "user", text: "第一条问题" },
      { id: "a-1", role: "assistant", text: "第一条回答" },
    ],
  };
}

test("stores one updated record per session and restores valid history", () => {
  const storage = memoryStorage();
  saveChatSession(storage, session("one", "2026-09-10T00:00:00.000Z"));
  const changed = session("one", "2026-09-10T01:00:00.000Z");
  changed.messages[1].text = "更新后的回答";
  saveChatSession(storage, changed);
  assert.equal(loadChatSessions(storage).length, 1);
  assert.equal(loadChatSessions(storage)[0].messages[1].text, "更新后的回答");
  assert.ok(storage.value(CHAT_HISTORY_KEY));
});

test("persists text only and removes hidden memory candidate blocks", () => {
  const messages = toStoredMessages([{
    id: "a-1",
    role: "assistant",
    parts: [
      { kind: "reasoning", text: "private reasoning" },
      { kind: "tool-call" },
      { kind: "text", text: "可见回答\n```memory-candidate\n{\"title\":\"x\",\"content\":\"y\",\"scope\":\"z\",\"confidence\":\"high\"}\n```" },
    ],
  }]);
  assert.deepEqual(messages.map((message) => message.text), ["可见回答"]);
});

test("can keep every visible message for a complete conversation export", () => {
  const messages = Array.from({ length: 60 }, (_, index) => ({
    id: `m-${index}`,
    role: index % 2 ? "assistant" : "user",
    parts: [{ kind: "text", text: `message ${index}` }],
  }));
  assert.equal(toStoredMessages(messages).length, 50);
  assert.equal(toStoredMessages(messages, null).length, 60);
});

test("exports a complete conversation as Markdown", () => {
  const markdown = conversationMarkdown(session("one", "2026-09-10T00:00:00.000Z"), "2026-09-10T02:00:00.000Z");
  assert.match(markdown, /provider: "codex"/);
  assert.match(markdown, /## User 1\n\n第一条问题/);
  assert.match(markdown, /## Assistant 1\n\n第一条回答/);
});
