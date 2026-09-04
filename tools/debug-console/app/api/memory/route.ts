/**
 * 控制台到主管理台的记忆写入代理。
 * 控制台是外部客户端，不直接读写 Markdown；实际状态转换仍由 web/ 完成。
 */
import { NextRequest, NextResponse } from "next/server";
import { kbApiBase } from "@/lib/kb-http-client";

const WORKSPACE_RE = /^[A-Za-z0-9_-]+$/;

export async function POST(req: NextRequest) {
  let body: { workspace?: string; action?: string; proposal?: unknown; path?: string; user_confirmed?: boolean };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (body.workspace && WORKSPACE_RE.test(body.workspace)) {
    headers.Cookie = `kb_workspace=${body.workspace}`;
  }
  const { workspace: _workspace, ...forwarded } = body;
  try {
    const response = await fetch(`${kbApiBase()}/api/memory`, {
      method: "POST",
      headers,
      body: JSON.stringify(forwarded),
    });
    const data = await response.json().catch(() => ({ ok: false, error: "non_json_response" }));
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ ok: false, error: "main_web_unavailable" }, { status: 502 });
  }
}
