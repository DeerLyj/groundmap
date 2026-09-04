"""RapidOCR CLI adapter with optional structured JSON output."""

from __future__ import annotations

import json
import sys
from importlib.metadata import version


def _payload(result, image_path: str) -> dict:
    raw_blocks = (result.to_json() if hasattr(result, "to_json") else []) or []
    blocks = [
        {
            "text": str(item.get("txt", "")).strip(),
            "bbox": item.get("box"),
            "confidence": item.get("score"),
        }
        for item in raw_blocks
        if str(item.get("txt", "")).strip()
    ]
    return {
        "input": image_path,
        "status": "ocr_success" if blocks else "no_text",
        "engine": "rapidocr",
        "engine_version": version("rapidocr"),
        "text": "\n".join(block["text"] for block in blocks),
        "blocks": blocks,
    }


def main() -> int:
    json_mode = "--json" in sys.argv[1:]
    image_paths = [arg for arg in sys.argv[1:] if arg != "--json"]
    if not image_paths:
        print("用法: python scripts/ocr_rapid.py [--json] <image> [...]", file=sys.stderr)
        return 2
    try:
        from rapidocr import RapidOCR
    except ImportError:
        print(
            "RapidOCR 未安装，请运行: python -m pip install -r requirements-ocr.txt",
            file=sys.stderr,
        )
        return 2
    try:
        engine = RapidOCR()
        results = []
        for image_path in image_paths:
            try:
                results.append(_payload(engine(image_path), image_path))
            except Exception as exc:  # noqa: BLE001 - 单图失败不丢掉同批结果
                results.append(
                    {
                        "input": image_path,
                        "status": "failed",
                        "engine": "rapidocr",
                        "engine_version": version("rapidocr"),
                        "text": "",
                        "blocks": [],
                        "error": str(exc),
                    }
                )
    except Exception as exc:  # noqa: BLE001 - CLI 要把后端错误传回 convert.py
        print(f"RapidOCR 初始化失败: {exc}", file=sys.stderr)
        return 1

    if json_mode:
        output = results[0] if len(results) == 1 else {"results": results}
        print(json.dumps(output, ensure_ascii=False))
        return 0

    texts = [item["text"] for item in results if item["text"]]
    if not texts:
        print("RapidOCR 未识别到文字", file=sys.stderr)
        return 1
    print("\n".join(texts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
