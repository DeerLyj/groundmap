import { test } from "node:test";
import assert from "node:assert/strict";
import {
  assetMimeType,
  assetUrl,
  derivedMarkdownForRaw,
  evidenceHref,
  isWorkspaceAssetPath,
  resolveMarkdownAssetPath,
} from "./evidence-path.ts";
import { normalizeLinkTarget } from "./markdown.ts";

test("resolves exported and raw images relative to derived Markdown", () => {
  assert.equal(
    resolveMarkdownAssetPath("derived/test/report.md", "report.assets/image1.png"),
    "derived/test/report.assets/image1.png",
  );
  assert.equal(
    resolveMarkdownAssetPath("derived/test/photo.md", "../../raw/test/photo.jpg"),
    "raw/test/photo.jpg",
  );
  assert.equal(
    resolveMarkdownAssetPath("derived/test/报告.md", "%E6%8A%A5%E5%91%8A.assets/%E5%9B%BE1.png"),
    "derived/test/报告.assets/图1.png",
  );
});

test("rejects traversal and unsupported assets", () => {
  assert.equal(resolveMarkdownAssetPath("derived/a.md", "../../secret.png"), null);
  assert.equal(resolveMarkdownAssetPath("derived/a.md", "a.exe"), null);
  assert.equal(isWorkspaceAssetPath("raw/../my_thoughts/a.png"), false);
});

test("builds encoded asset and evidence URLs", () => {
  assert.equal(assetUrl("raw/test/原图 1.jpg"), "/api/assets/raw/test/%E5%8E%9F%E5%9B%BE%201.jpg");
  assert.equal(
    evidenceHref("derived/test/报告.md", "^p-1-abc123"),
    "/evidence/derived/test/%E6%8A%A5%E5%91%8A.md?anchor=p-1-abc123#p-1-abc123",
  );
});

test("maps source files to their derived Markdown and MIME type", () => {
  assert.equal(derivedMarkdownForRaw("raw/papers/a.pdf"), "derived/papers/a.md");
  assert.equal(assetMimeType("raw/a.xlsx"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
});

test("keeps explicit source extensions while normalizing wiki targets", () => {
  assert.equal(normalizeLinkTarget("raw/papers/a.pdf"), "raw/papers/a.pdf");
  assert.equal(normalizeLinkTarget("wiki/concepts/a"), "wiki/concepts/a.md");
});
