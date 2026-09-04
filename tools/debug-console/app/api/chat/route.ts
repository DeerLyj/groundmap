/**
 * POST /api/chat — SSE 流式对话端点
 *
 * 请求体：
 *   {
 *     provider: 'deepseek' | 'claude-code' | 'codex',
 *     model: string,
 *     system?: string,
 *     messages: ChatMessage[],   // 完整历史，包括最新的 user 消息
 *     tool_budget?: number,
 *     project_id?: string,        // 可选：预加载当前项目 Context Pack
 *   }
 *
 * 响应：text/event-stream，每行 `data: <AgentEvent json>\n\n`
 */
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { getProvider } from "@/lib/providers";
import type { ProviderId } from "@/lib/providers/types";
import { runAgent } from "@/lib/agent-loop";
import { sseLine } from "@/lib/sse";
import { DEFAULT_SYSTEM_PROMPT } from "@/lib/default-system-prompt";
import { executeTool, workspaceContext } from "@/lib/kb-http-client";

/**
 * 预热：root_index 内存缓存（5 分钟 TTL）。
 * 每次 chat 都拉 KB HTTP 太费，但 5 分钟内反复问问题就能复用。
 * 用户改了 root_index 后最迟 5 分钟生效——可接受（root_index 改动很少）。
 */
const ROOT_INDEX_TTL_MS = 5 * 60 * 1000;
// 按 workspace 分桶缓存——否则切库后会把上一个库的 root_index 串给新库。
const rootIndexCache = new Map<string, { content: string; expiresAt: number }>();
const CONFIRMED_MEMORY_TTL_MS = 5 * 60 * 1000;
const confirmedMemoryCache = new Map<string, { content: string; expiresAt: number }>();

async function getRootIndexContent(workspace: string | undefined): Promise<string> {
  const key = workspace ?? "__default__";
  const now = Date.now();
  const cached = rootIndexCache.get(key);
  if (cached && cached.expiresAt > now) return cached.content;
  try {
    // executeTool 从 workspaceContext 读 ws（本函数在 run(ws) 作用域内被调）
    const r = await executeTool("read_page", { path: "wiki/root_index.md" });
    if (!r.ok || !r.data) return "";
    const d = r.data as { content?: string };
    const content = d.content || "";
    rootIndexCache.set(key, { content, expiresAt: now + ROOT_INDEX_TTL_MS });
    return content;
  } catch {
    return "";
  }
}

/** 预热用户已确认的个人记忆；候选记忆和 draft 页面永远不自动注入。 */
async function getConfirmedMemoryContent(workspace: string | undefined): Promise<string> {
  const key = workspace ?? "__default__";
  const now = Date.now();
  const cached = confirmedMemoryCache.get(key);
  if (cached && cached.expiresAt > now) return cached.content;
  try {
    const listed = await executeTool("list_pages", { type: "memory", status: "reviewed" });
    if (!listed.ok || !Array.isArray(listed.data)) return "";
    const pages = listed.data as Array<{ path?: string }>;
    const sections: string[] = [];
    for (const page of pages.slice(0, 50)) {
      if (!page.path || !page.path.startsWith("wiki/memory/")) continue;
      const r = await executeTool("read_page", { path: page.path });
      if (!r.ok || !r.data) continue;
      const d = r.data as { path?: string; content?: string; frontmatter?: Record<string, unknown> };
      const tags = Array.isArray(d.frontmatter?.tags) ? d.frontmatter.tags.map(String) : [];
      if (
        d.frontmatter?.type !== "memory" ||
        d.frontmatter?.status !== "reviewed" ||
        d.frontmatter?.last_modified_by !== "Human" ||
        !tags.includes("memory-confirmed")
      ) continue;
      const content = String(d.content || "").trim();
      if (content) sections.push(`### ${String(d.frontmatter?.title || d.path)}\n${content}`);
    }
    const content = sections.join("\n\n").slice(0, 30_000);
    confirmedMemoryCache.set(key, { content, expiresAt: now + CONFIRMED_MEMORY_TTL_MS });
    return content;
  } catch {
    return "";
  }
}

/** 在 system prompt 末尾 append root_index 全文，让 AI 不需要花一轮调 read_page 读它 */
function appendPrewarmedIndex(baseSystem: string, indexContent: string): string {
  if (!indexContent) return baseSystem;
  return (
    baseSystem +
    "\n\n---\n\n## 📚 已预加载：wiki/root_index.md 全文\n\n" +
    "下面是知识库一级领域索引的完整内容。**不要再调 `read_page` 读它**——直接基于这份索引决定下一步钻取哪个子 MOC / 具体页面。\n\n" +
    "```markdown\n" +
    indexContent +
    "\n```\n"
  );
}

function appendConfirmedMemory(baseSystem: string, memoryContent: string): string {
  if (!memoryContent) return baseSystem;
  return (
    baseSystem +
    "\n\n---\n\n## 🧠 已预加载：用户已确认的个人工作偏好\n\n" +
    "以下内容是用户明确确认过的长期工作记忆。只能用于调整回答方式、输出格式和任务协作方式；不要把它扩展为未写明的个人事实，也不要把候选记忆当作已确认偏好。\n\n" +
    "```markdown\n" +
    memoryContent +
    "\n```\n"
  );
}

function appendProjectContext(baseSystem: string, projectId: string, context: string): string {
  if (!context) return baseSystem;
  return (
    baseSystem +
    "\n\n---\n\n## 📦 已预加载：当前项目 Context Pack（" + projectId + "）\n\n" +
    "以下内容来自项目目录生成的 Context Pack。项目状态、事实和决策必须遵守其中的确认标记：未被 Human 确认的内容不是有效记忆或已确认事实。回答知识库事实时，优先引用其中列出的 wiki/ 与证据入口；不要把 projects/ 路径编造成可点击的 Wiki 引用。若问题属于该项目，可直接使用这份上下文，不必重复调用 context_pack。\n\n" +
    "```markdown\n" +
    context +
    "\n```\n"
  );
}

async function getProjectContext(projectId: string | undefined): Promise<string> {
  if (!projectId) return "";
  try {
    const result = await executeTool("context_pack", {
      project_id: projectId,
      max_chars: 30_000,
    });
    if (!result.ok || !result.data || typeof result.data !== "object") return "";
    const data = result.data as { context?: unknown };
    return typeof data.context === "string" ? data.context : "";
  } catch {
    return "";
  }
}

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ChatMessageSchema = z.object({
  role: z.enum(["user", "assistant"]),
  text: z.string().optional(),
  tool_calls: z
    .array(
      z.object({
        id: z.string(),
        name: z.string(),
        args: z.record(z.unknown()),
      }),
    )
    .optional(),
  tool_results: z
    .array(
      z.object({
        id: z.string(),
        ok: z.boolean(),
        data: z.unknown().optional(),
        error: z.string().optional(),
      }),
    )
    .optional(),
});

const RequestSchema = z.object({
  provider: z.enum(["deepseek", "claude-code", "codex"]),
  model: z.string().min(1),
  system: z.string().optional(),
  messages: z.array(ChatMessageSchema).min(1).max(50),
  tool_budget: z.number().int().min(1).max(50).optional(),
  mode: z.enum(["quick", "audit", "explore", "devil"]).optional(),
  // 「自动识别」用：要查的 workspace；空则 web 回退默认。合法性由 web 的 resolveWorkspace 兜底校验。
  workspace: z.string().regex(/^[A-Za-z0-9_-]+$/).optional(),
  project_id: z.string().regex(/^[a-z0-9][a-z0-9_-]*$/).optional(),
  memory_opt_out: z.boolean().optional(),
});

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const parsed = RequestSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: "invalid_request", details: parsed.error.flatten() },
      { status: 400 },
    );
  }

  const {
    provider: providerId,
    model,
    system,
    messages,
    tool_budget,
    mode,
    workspace,
    project_id,
    memory_opt_out,
  } = parsed.data;
  const provider = getProvider(providerId as ProviderId);
  if (!provider) {
    return NextResponse.json({ error: "unknown_provider" }, { status: 400 });
  }
  if (!provider.isAvailable()) {
    return NextResponse.json(
      { error: "provider_unavailable", reason: provider.unavailableReason() },
      { status: 400 },
    );
  }

  // 客户端断开（关浏览器 / abort()）→ 触发 AbortController，
  // agent-loop / providers 监听后 kill subprocess、停止 fetch 流
  const abortController = new AbortController();
  // Next.js Route Handler 的 req.signal 在客户端断连时 fire abort
  req.signal.addEventListener("abort", () => abortController.abort(), { once: true });

  const stream = new ReadableStream({
    async start(controller) {
      let closed = false;
      const safeEnqueue = (chunk: Uint8Array) => {
        if (closed) return;
        try {
          controller.enqueue(chunk);
        } catch {
          // controller 已关闭——忽略
          closed = true;
        }
      };
      // 整段逻辑跑在 workspaceContext 作用域内：root_index 预热 + runAgent 深处的所有
      // executeTool 都会读到 workspace，并在调 web 时带上 kb_workspace cookie。
      await workspaceContext.run(workspace, async () => {
        try {
          const baseSystem = memory_opt_out
            ? `${system || DEFAULT_SYSTEM_PROMPT}\n\n本轮用户明确要求不记录记忆（#no-memory）。不要提出、保存或暗示任何候选记忆。`
            : system || DEFAULT_SYSTEM_PROMPT;
          const indexContent = await getRootIndexContent(workspace);
          const memoryContent = await getConfirmedMemoryContent(workspace);
          const projectContext = await getProjectContext(project_id);
          const augmentedSystem = appendProjectContext(
            appendConfirmedMemory(
              appendPrewarmedIndex(baseSystem, indexContent),
              memoryContent,
            ),
            project_id || "",
            projectContext,
          );

          for await (const evt of runAgent({
            provider,
            model,
            system: augmentedSystem,
            messages,
            toolBudget: tool_budget,
            mode,
            preloadedSources: [
              ...(indexContent ? ["wiki/root_index.md"] : []),
              ...(memoryContent ? ["wiki/memory/confirmed.md"] : []),
            ],
            signal: abortController.signal,
          })) {
            if (abortController.signal.aborted) break;
            safeEnqueue(sseLine(evt));
          }
          safeEnqueue(sseLine({ kind: "stream-end" }));
        } catch (e) {
          safeEnqueue(
            sseLine({
              kind: "turn-end",
              reason: "error",
              error_message: e instanceof Error ? e.message : String(e),
            }),
          );
        } finally {
          closed = true;
          try {
            controller.close();
          } catch {
            /* 已关闭 */
          }
        }
      });
    },
    cancel() {
      // 客户端拉断 stream（fetch abort）→ 转发到 agent-loop
      abortController.abort();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
