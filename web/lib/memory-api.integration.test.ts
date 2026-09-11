import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { confirmedMemoryText, type MemoryRecord } from "./memory-model.ts";

const WEB_ROOT = path.resolve(import.meta.dirname, "..");
const NEXT_BIN = path.join(WEB_ROOT, "node_modules", "next", "dist", "bin", "next");

function git(cwd: string, ...args: string[]): void {
  const result = spawnSync("git", args, { cwd, encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr || result.stdout);
}

async function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      assert(address && typeof address === "object");
      server.close(() => resolve(address.port));
    });
  });
}

async function startWeb(dataRoot: string): Promise<{ child: ChildProcess; base: string }> {
  const port = await freePort();
  const base = `http://127.0.0.1:${port}`;
  const child = spawn(process.execPath, [NEXT_BIN, "dev", "-H", "127.0.0.1", "-p", String(port)], {
    cwd: WEB_ROOT,
    env: {
      ...process.env,
      KB_ROOT: dataRoot,
      KB_WORKSPACE: "alpha",
      NEXT_TELEMETRY_DISABLED: "1",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let output = "";
  child.stdout?.on("data", (chunk) => (output += chunk.toString()));
  child.stderr?.on("data", (chunk) => (output += chunk.toString()));

  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`Next exited early (${child.exitCode})\n${output}`);
    try {
      const response = await fetch(`${base}/api/memory`);
      if (response.ok) return { child, base };
    } catch {
      // Server is still compiling.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  child.kill();
  throw new Error(`Next did not become ready\n${output}`);
}

async function stopWeb(child: ChildProcess): Promise<void> {
  if (child.exitCode !== null) return;
  child.kill();
  await Promise.race([
    new Promise<void>((resolve) => child.once("exit", () => resolve())),
    new Promise<void>((resolve) => setTimeout(resolve, 5_000)),
  ]);
}

async function records(base: string, workspace = "alpha"): Promise<MemoryRecord[]> {
  const response = await fetch(`${base}/api/memory`, {
    headers: { Cookie: `kb_workspace=${workspace}` },
  });
  assert.equal(response.status, 200);
  const body = (await response.json()) as { ok: boolean; records: MemoryRecord[] };
  assert.equal(body.ok, true);
  return body.records;
}

async function post(base: string, body: object, workspace = "alpha") {
  const response = await fetch(`${base}/api/memory`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Cookie: `kb_workspace=${workspace}`,
    },
    body: JSON.stringify(body),
  });
  return { status: response.status, body: (await response.json()) as Record<string, unknown> };
}

test("memory API persists only confirmed memory and isolates workspaces", { timeout: 120_000 }, async (t) => {
  const dataRoot = await mkdtemp(path.join(path.resolve(WEB_ROOT, ".."), ".groundmap-memory-"));
  for (const workspace of ["alpha", "beta"]) {
    await mkdir(path.join(dataRoot, "workspaces", workspace, "wiki", "memory", "candidates"), {
      recursive: true,
    });
  }
  await writeFile(path.join(dataRoot, "README.md"), "temporary memory integration fixture\n");
  git(dataRoot, "init", "-q");
  git(dataRoot, "config", "user.name", "GroundMap Test");
  git(dataRoot, "config", "user.email", "groundmap-test@example.invalid");
  git(dataRoot, "add", "README.md");
  git(dataRoot, "commit", "-q", "-m", "test fixture");

  let server = await startWeb(dataRoot);
  t.after(async () => {
    await stopWeb(server.child);
    await rm(dataRoot, { recursive: true, force: true });
  });

  const refused = await post(server.base, {
    action: "save_candidate",
    proposal: { title: "未确认", content: "不得落盘", scope: "测试", confidence: "low" },
  });
  assert.equal(refused.status, 400);
  assert.equal(refused.body.error, "explicit_confirmation_required");
  assert.deepEqual(await records(server.base), []);

  const saved = await post(server.base, {
    action: "save_candidate",
    user_confirmed: true,
    proposal: { title: "确认记忆", content: "先给证据。", scope: "回答", confidence: "high" },
  });
  assert.equal(saved.status, 200, JSON.stringify(saved.body));
  const confirmedPath = String(saved.body.path);
  assert.equal((await records(server.base))[0].memory_state, "candidate");
  assert.equal(confirmedMemoryText(await records(server.base)), "");

  const confirmed = await post(server.base, {
    action: "confirm",
    path: confirmedPath,
    user_confirmed: true,
  });
  assert.equal(confirmed.status, 200);

  const rejectedSaved = await post(server.base, {
    action: "save_candidate",
    user_confirmed: true,
    proposal: { title: "拒绝记忆", content: "不得注入。", scope: "回答", confidence: "medium" },
  });
  assert.equal(rejectedSaved.status, 200);
  const rejected = await post(server.base, {
    action: "reject",
    path: String(rejectedSaved.body.path),
    user_confirmed: true,
  });
  assert.equal(rejected.status, 200);

  const betaSaved = await post(server.base, {
    action: "save_candidate",
    user_confirmed: true,
    proposal: { title: "另一工作区", content: "只属于 beta。", scope: "回答", confidence: "high" },
  }, "beta");
  assert.equal(betaSaved.status, 200);
  assert.equal((await post(server.base, {
    action: "confirm",
    path: String(betaSaved.body.path),
    user_confirmed: true,
  }, "beta")).status, 200);

  await stopWeb(server.child);
  server = await startWeb(dataRoot);

  const alphaText = confirmedMemoryText(await records(server.base, "alpha"));
  assert.match(alphaText, /先给证据/);
  assert.doesNotMatch(alphaText, /不得注入|只属于 beta/);

  const betaText = confirmedMemoryText(await records(server.base, "beta"));
  assert.match(betaText, /只属于 beta/);
  assert.doesNotMatch(betaText, /先给证据|不得注入/);
});
