"""PaddleOCR 的命令行适配器：接收图片路径，把识别文本写到 stdout。"""

from __future__ import annotations

import sys
from typing import Any


def _texts(result: Any) -> list[str]:
    values = getattr(result, "rec_texts", None)
    if values is None and isinstance(result, dict):
        values = result.get("rec_texts") or result.get("txts")
    if values is None:
        payload = getattr(result, "json", None)
        if callable(payload):
            payload = payload()
        if isinstance(payload, str):
            import json

            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = None
        if isinstance(payload, dict):
            values = payload.get("rec_texts") or payload.get("txts")
    if values is None:
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: python scripts/ocr_paddle.py <image>", file=sys.stderr)
        return 2
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        print(
            "PaddleOCR 未安装，请按官方文档安装 PaddlePaddle 与 PaddleOCR。",
            file=sys.stderr,
        )
        return 2
    options: dict[str, Any] = {
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
    }
    try:
        ocr = PaddleOCR(**options)
        texts: list[str] = []
        for result in ocr.predict(sys.argv[1]):
            texts.extend(_texts(result))
    except Exception as exc:  # noqa: BLE001 - CLI 要把后端错误传回 convert.py
        print(f"PaddleOCR 执行失败: {exc}", file=sys.stderr)
        return 1
    if not texts:
        print("PaddleOCR 未识别到文字", file=sys.stderr)
        return 1
    print("\n".join(texts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
