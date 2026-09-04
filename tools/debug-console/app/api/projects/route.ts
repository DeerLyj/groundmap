/** GET /api/projects — 代理主 web 的项目列表接口。 */
import { NextRequest, NextResponse } from "next/server";
import { kbApiBase } from "@/lib/kb-http-client";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const WORKSPACE_RE = /^[A-Za-z0-9_-]+$/;

export async function GET(req: NextRequest) {
  const workspace = req.nextUrl.searchParams.get("ws");
  const headers: HeadersInit = {};
  if (workspace && WORKSPACE_RE.test(workspace)) {
    headers.Cookie = `kb_workspace=${encodeURIComponent(workspace)}`;
  }
  try {
    const res = await fetch(`${kbApiBase()}/api/projects`, {
      headers,
      cache: "no-store",
    });
    if (!res.ok) return NextResponse.json({ ok: false, data: [] });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ ok: false, data: [] });
  }
}
