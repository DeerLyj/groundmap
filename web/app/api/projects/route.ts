/**
 * Project State / Decision Record / Context Pack API.
 *
 * GET /api/projects                 list projects
 * GET /api/projects?id=<project_id> show one project and its decisions
 * POST { action: "context-build", project_id, max_chars? }
 * POST { action: "confirm", project_id, target, decision_id?, decision_status?, note? }
 */
import { NextRequest, NextResponse } from "next/server";
import { runKCli } from "@/lib/k-cli";
import { isSameOrigin } from "@/lib/permissions";

export const dynamic = "force-dynamic";

const PROJECT_ID_RE = /^[a-z0-9][a-z0-9_-]*$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function validProjectId(value: string | null): value is string {
  return !!value && PROJECT_ID_RE.test(value);
}

function parseDate(value: string | null): string | undefined {
  return value && DATE_RE.test(value) ? value : undefined;
}

export async function GET(req: NextRequest) {
  const params = req.nextUrl.searchParams;
  const id = params.get("id");
  const args = id
    ? ["project-show", id]
    : ["project-list"];

  if (id && !validProjectId(id)) {
    return NextResponse.json({ ok: false, error: "invalid_project_id" }, { status: 400 });
  }
  for (const key of ["date_from", "date_to"]) {
    const value = params.get(key);
    if (value && !DATE_RE.test(value)) {
      return NextResponse.json({ ok: false, error: `invalid_${key}` }, { status: 400 });
    }
  }
  if (!id && params.get("status")) args.push("--status", params.get("status")!);
  if (id && params.get("decision_status")) args.push("--decision-status", params.get("decision_status")!);
  if (id && parseDate(params.get("date_from"))) args.push("--date-from", parseDate(params.get("date_from"))!);
  if (id && parseDate(params.get("date_to"))) args.push("--date-to", parseDate(params.get("date_to"))!);

  const result = await runKCli(args);
  if (!result.ok) {
    return NextResponse.json({ ok: false, error: result.error || "project_query_failed" }, { status: 400 });
  }
  return NextResponse.json({ ok: true, data: result.data });
}

export async function POST(req: NextRequest) {
  if (!isSameOrigin(req)) {
    return NextResponse.json({ ok: false, error: "csrf_blocked" }, { status: 403 });
  }

  let body: {
    action?: string;
    project_id?: string;
    max_chars?: number;
    target?: string;
    decision_id?: string;
    decision_status?: string;
    note?: string;
  };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }
  const projectId = body.project_id;
  if (typeof projectId !== "string" || !PROJECT_ID_RE.test(projectId)) {
    return NextResponse.json({ ok: false, error: "invalid_action" }, { status: 400 });
  }

  if (body.action === "confirm") {
    if (body.target !== "state" && body.target !== "decision") {
      return NextResponse.json({ ok: false, error: "invalid_target" }, { status: 400 });
    }
    if (body.decision_id && !/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(body.decision_id)) {
      return NextResponse.json({ ok: false, error: "invalid_decision_id" }, { status: 400 });
    }
    if (body.decision_status && !["reviewed", "executed"].includes(body.decision_status)) {
      return NextResponse.json({ ok: false, error: "invalid_decision_status" }, { status: 400 });
    }
    const result = await runKCli([
      "project-confirm",
      projectId,
      body.target,
      ...(body.decision_id ? [body.decision_id] : []),
      ...(body.decision_status ? ["--decision-status", body.decision_status] : []),
      ...(typeof body.note === "string" && body.note.trim()
        ? ["--note", body.note.trim().slice(0, 500)]
        : []),
    ]);
    if (!result.ok) {
      return NextResponse.json({ ok: false, error: result.error || "project_confirm_failed" }, { status: 400 });
    }
    return NextResponse.json({ ok: true, data: result.data });
  }

  if (body.action !== "context-build") {
    return NextResponse.json({ ok: false, error: "invalid_action" }, { status: 400 });
  }

  const maxChars = typeof body.max_chars === "number" && Number.isFinite(body.max_chars)
    ? Math.max(1000, Math.min(100000, Math.floor(body.max_chars)))
    : 30000;
  const result = await runKCli([
    "context-build",
    projectId,
    "--max-chars",
    String(maxChars),
  ]);
  if (!result.ok) {
    return NextResponse.json({ ok: false, error: result.error || "context_build_failed" }, { status: 400 });
  }
  return NextResponse.json({ ok: true, data: result.data });
}
