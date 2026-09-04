/**
 * 个人工作记忆 API。
 *
 * 保存候选和确认/拒绝都是显式用户动作；普通聊天不会通过此路由自动落盘。
 */
import { NextRequest, NextResponse } from "next/server";
import { isSameOrigin } from "@/lib/permissions";
import {
  listMemoryRecords,
  saveMemoryCandidate,
  transitionMemory,
  type MemoryProposal,
} from "@/lib/memory";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    return NextResponse.json({ ok: true, records: await listMemoryRecords() });
  } catch {
    return NextResponse.json({ ok: false, error: "read_failed" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  if (!isSameOrigin(req)) {
    return NextResponse.json({ ok: false, error: "csrf_blocked" }, { status: 403 });
  }

  let body: {
    action?: "save_candidate" | "confirm" | "reject";
    proposal?: MemoryProposal;
    path?: string;
    user_confirmed?: boolean;
  };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  if (body.action === "save_candidate") {
    if (body.user_confirmed !== true) {
      return NextResponse.json({ ok: false, error: "explicit_confirmation_required" }, { status: 400 });
    }
    const result = await saveMemoryCandidate(body.proposal as MemoryProposal);
    return NextResponse.json(result, { status: result.ok ? 200 : 400 });
  }

  if ((body.action === "confirm" || body.action === "reject") && body.user_confirmed === true && body.path) {
    const result = await transitionMemory(body.path, body.action);
    return NextResponse.json(result, { status: result.ok ? 200 : 400 });
  }

  return NextResponse.json({ ok: false, error: "invalid_action" }, { status: 400 });
}
