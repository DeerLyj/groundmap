/** Read-only, range-aware access to renderable raw/derived evidence assets. */
import { NextRequest, NextResponse } from "next/server";
import { fileExists, fileSize, isReadableDir, readFileBytes } from "@/lib/kb";
import { assetMimeType, isWorkspaceAssetPath } from "@/lib/evidence-path";

export const dynamic = "force-dynamic";

function parseRange(value: string | null, size: number): [number, number] | null {
  if (!value) return null;
  const match = /^bytes=(\d*)-(\d*)$/.exec(value.trim());
  if (!match || (!match[1] && !match[2])) return null;
  if (!match[1]) {
    const length = Number(match[2]);
    if (!Number.isSafeInteger(length) || length <= 0) return null;
    return [Math.max(0, size - length), size - 1];
  }
  const start = Number(match[1]);
  const end = match[2] ? Number(match[2]) : size - 1;
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 0 || start >= size) {
    return null;
  }
  return [start, Math.min(end, size - 1)];
}

export async function GET(req: NextRequest, { params }: { params: { path: string[] } }) {
  let relPath: string;
  try {
    relPath = params.path.map((part) => decodeURIComponent(part)).join("/");
  } catch {
    return NextResponse.json({ error: "invalid_path" }, { status: 400 });
  }
  const mime = assetMimeType(relPath);
  if (!mime || !isReadableDir(relPath) || !isWorkspaceAssetPath(relPath)) {
    return NextResponse.json({ error: "invalid_asset" }, { status: 400 });
  }
  if (!(await fileExists(relPath))) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  try {
    const size = await fileSize(relPath);
    const range = parseRange(req.headers.get("range"), size);
    const result = range
      ? await readFileBytes(relPath, range[0], range[1])
      : await readFileBytes(relPath);
    const headers = new Headers({
      "Accept-Ranges": "bytes",
      "Cache-Control": "private, no-store",
      "Content-Type": mime,
      "Content-Length": String(result.bytes.byteLength),
      "X-Content-Type-Options": "nosniff",
    });
    if (range) headers.set("Content-Range", `bytes ${range[0]}-${range[1]}/${size}`);
    return new NextResponse(result.bytes.buffer as ArrayBuffer, {
      status: range ? 206 : 200,
      headers,
    });
  } catch (error) {
    return NextResponse.json({ error: "read_failed", message: String(error) }, { status: 500 });
  }
}
