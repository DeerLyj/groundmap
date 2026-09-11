import { stripMemoryCandidateBlocks } from "./memory-candidate.ts";

export const CHAT_HISTORY_KEY = "groundmap.debug.chat-sessions.v1";
export const MAX_CHAT_SESSIONS = 20;
const MAX_MESSAGES = 50;
const MAX_SESSION_CHARS = 200_000;

export interface StoredChatMessage {
  id: string;
  role: "user" | "assistant" | "error";
  text: string;
  usage?: {
    input_tokens?: number;
    cached_input_tokens?: number;
    output_tokens?: number;
    duration_ms?: number;
    tool_calls?: number;
  };
  refValidation?: { broken: string[]; unread: string[]; downgraded?: string[] };
}

export interface ChatSession {
  schemaVersion: 1;
  id: string;
  contextKey: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  workspace: string | null;
  projectId: string | null;
  provider: string;
  model: string;
  mode: string;
  networkMode: string;
  messages: StoredChatMessage[];
}

interface MessageLike {
  id: string;
  role: string;
  parts: Array<{ kind: string; text?: string }>;
  usage?: StoredChatMessage["usage"];
  refValidation?: StoredChatMessage["refValidation"];
}

export function chatContextKey(workspace: string | null, projectId: string | null): string {
  return `${workspace || "__default__"}:${projectId || "__none__"}`;
}

export function newChatSessionId(): string {
  return globalThis.crypto?.randomUUID?.() || `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function toStoredMessages(
  messages: MessageLike[],
  maxMessages: number | null = MAX_MESSAGES,
): StoredChatMessage[] {
  const stored = messages
    .filter((message) => ["user", "assistant", "error"].includes(message.role))
    .map((message) => ({
      id: message.id,
      role: message.role as StoredChatMessage["role"],
      text: stripMemoryCandidateBlocks(
        message.parts
          .filter((part) => part.kind === "text")
          .map((part) => part.text || "")
          .join("\n"),
      ),
      usage: message.usage,
      refValidation: message.refValidation,
    }))
    .filter((message) => message.text);
  return maxMessages === null ? stored : stored.slice(-maxMessages);
}

function trimSession(session: ChatSession): ChatSession {
  let remaining = MAX_SESSION_CHARS;
  const messages: StoredChatMessage[] = [];
  for (let index = session.messages.length - 1; index >= 0 && remaining > 0; index--) {
    const message = session.messages[index];
    const text = message.text.length <= remaining
      ? message.text
      : message.text.slice(message.text.length - remaining);
    messages.unshift({ ...message, text });
    remaining -= text.length;
  }
  return { ...session, messages };
}

function isSession(value: unknown): value is ChatSession {
  if (!value || typeof value !== "object") return false;
  const session = value as Partial<ChatSession>;
  return session.schemaVersion === 1 &&
    typeof session.id === "string" &&
    typeof session.contextKey === "string" &&
    typeof session.title === "string" &&
    typeof session.createdAt === "string" &&
    typeof session.updatedAt === "string" &&
    (typeof session.workspace === "string" || session.workspace === null) &&
    (typeof session.projectId === "string" || session.projectId === null) &&
    typeof session.provider === "string" &&
    typeof session.model === "string" &&
    typeof session.mode === "string" &&
    typeof session.networkMode === "string" &&
    Array.isArray(session.messages) &&
    session.messages.every((message) => {
      if (!message || typeof message !== "object") return false;
      const item = message as Partial<StoredChatMessage>;
      return typeof item.id === "string" &&
        (item.role === "user" || item.role === "assistant" || item.role === "error") &&
        typeof item.text === "string";
    });
}

export function loadChatSessions(storage: Pick<Storage, "getItem">): ChatSession[] {
  try {
    const parsed = JSON.parse(storage.getItem(CHAT_HISTORY_KEY) || "[]") as unknown;
    return Array.isArray(parsed) ? parsed.filter(isSession) : [];
  } catch {
    return [];
  }
}

export function saveChatSession(
  storage: Pick<Storage, "getItem" | "setItem">,
  session: ChatSession,
): ChatSession[] {
  const next = [
    trimSession(session),
    ...loadChatSessions(storage).filter((item) => item.id !== session.id),
  ]
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .slice(0, MAX_CHAT_SESSIONS);
  storage.setItem(CHAT_HISTORY_KEY, JSON.stringify(next));
  return next;
}

export function removeChatSession(
  storage: Pick<Storage, "getItem" | "setItem">,
  sessionId: string,
): ChatSession[] {
  const next = loadChatSessions(storage).filter((item) => item.id !== sessionId);
  storage.setItem(CHAT_HISTORY_KEY, JSON.stringify(next));
  return next;
}

function quoted(value: string): string {
  return JSON.stringify(value);
}

export function conversationMarkdown(session: ChatSession, exportedAt = new Date().toISOString()): string {
  const lines = [
    "---",
    `title: ${quoted(session.title)}`,
    `created_at: ${quoted(session.createdAt)}`,
    `exported_at: ${quoted(exportedAt)}`,
    `workspace: ${quoted(session.workspace || "")}`,
    `project_id: ${quoted(session.projectId || "")}`,
    `provider: ${quoted(session.provider)}`,
    `model: ${quoted(session.model)}`,
    `mode: ${quoted(session.mode)}`,
    `network_mode: ${quoted(session.networkMode)}`,
    "---",
    "",
    `# ${session.title}`,
  ];
  let userIndex = 0;
  let assistantIndex = 0;
  for (const message of session.messages) {
    if (message.role === "user") userIndex++;
    if (message.role === "assistant") assistantIndex++;
    const label = message.role === "user"
      ? `User ${userIndex}`
      : message.role === "assistant" ? `Assistant ${assistantIndex}` : "Error";
    lines.push("", `## ${label}`, "", message.text);
  }
  return `${lines.join("\n").trim()}\n`;
}

export function downloadMarkdown(filename: string, content: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: "text/markdown;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
