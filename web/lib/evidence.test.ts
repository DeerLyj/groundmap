import { test } from "node:test";
import assert from "node:assert/strict";
import { bestEvidenceLocator, inferEvidenceTimestamp } from "./evidence-locator.ts";

test("infers the nearest preceding audio time range", () => {
  const content = [
    "### 00:00:00.000–00:00:03.600",
    "第一段内容。",
    "",
    "### 00:00:03.600–00:00:08.100",
    "第二段内容。 ^p-2-test",
  ].join("\n");
  assert.deepEqual(
    inferEvidenceTimestamp(content, content.indexOf("第二段")),
    { kind: "audio", start: 3.6, end: 8.1 },
  );
});

test("matches sidecar locators using meaningful token overlap", () => {
  const payload = {
    items: [
      { text: "无关说明", locator: { kind: "xlsx", sheet: "Sheet1", range: "A1:B1" } },
      {
        text: "卫星 名称 轨道 类型 数据 状态",
        locator: { kind: "xlsx", sheet: "Sheet1", range: "A20:N20" },
      },
    ],
  };
  assert.deepEqual(
    bestEvidenceLocator(payload, "| 卫星名称 | 轨道类型 | 数据状态 | ^t-1-test"),
    { locator: { kind: "xlsx", sheet: "Sheet1", range: "A20:N20" } },
  );
});

test("returns an extracted image path with its locator", () => {
  const payload = {
    assets: [{
      asset_path: "derived/report.assets/image1.png",
      ocr: { text: "系统总体架构图" },
      locators: [{ kind: "image", page: 4, bbox: [1, 2, 3, 4] }],
    }],
  };
  assert.deepEqual(
    bestEvidenceLocator(payload, "系统总体架构图 ^p-4-test"),
    {
      locator: { kind: "image", page: 4, bbox: [1, 2, 3, 4] },
      assetPath: "derived/report.assets/image1.png",
    },
  );
});
