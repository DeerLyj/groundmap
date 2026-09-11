"""Combine one conversion report and an LLM JSONL ledger into batch cost metrics."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def _read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_jsonl(path: str | None) -> list[dict]:
    if not path:
        return []
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def summarize(
    conversion: dict,
    runs: list[dict],
    batch_id: str,
    rate_card: dict | None = None,
) -> dict:
    if conversion.get("batch_id") not in {None, batch_id}:
        raise ValueError("转换报告的 batch_id 与请求不一致")
    selected = [run for run in runs if run.get("batch_id") == batch_id]
    grouped = defaultdict(lambda: {"runs": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "duration_ms": 0})
    for run in selected:
        key = f"{run.get('provider', 'unknown')}/{run.get('model', 'unknown')}"
        item = grouped[key]
        item["runs"] += 1
        for field in ("input_tokens", "cached_input_tokens", "output_tokens", "duration_ms"):
            item[field] += int(run.get(field) or 0)

    currency = (rate_card or {}).get("currency")
    prices = (rate_card or {}).get("models", {})
    total_cost = 0.0
    unpriced = []
    model_rows = []
    for key, item in sorted(grouped.items()):
        price = prices.get(key)
        row = {"model": key, **item, "cost": None}
        if price:
            uncached = max(0, item["input_tokens"] - item["cached_input_tokens"])
            row["cost"] = round(
                (
                    uncached * float(price["input_per_million"])
                    + item["cached_input_tokens"]
                    * float(price.get("cached_input_per_million", price["input_per_million"]))
                    + item["output_tokens"] * float(price["output_per_million"])
                )
                / 1_000_000,
                6,
            )
            total_cost += row["cost"]
        else:
            unpriced.append(key)
        model_rows.append(row)

    files = conversion.get("files", [])
    totals = conversion.get("totals", {})
    characters = sum(int(item.get("characters") or 0) for item in files)
    converted = int(totals.get("converted") or 0)
    return {
        "schema_version": 1,
        "kind": "ingest_batch_cost",
        "batch_id": batch_id,
        "conversion": {
            "duration_ms": int(conversion.get("duration_ms") or 0),
            "input_bytes": int(totals.get("input_bytes") or 0),
            "characters": characters,
            "converted": converted,
            "quality_success": int(totals.get("quality_success") or 0),
            "degraded": int(totals.get("degraded") or 0),
            "failed": int(totals.get("failed") or 0),
        },
        "llm": {
            "runs": len(selected),
            "input_tokens": sum(row["input_tokens"] for row in model_rows),
            "cached_input_tokens": sum(row["cached_input_tokens"] for row in model_rows),
            "output_tokens": sum(row["output_tokens"] for row in model_rows),
            "duration_ms": sum(row["duration_ms"] for row in model_rows),
            "models": model_rows,
        },
        "api_cost": {
            "currency": currency,
            "total": round(total_cost, 6) if currency else None,
            "per_converted_file": round(total_cost / converted, 6)
            if currency and converted
            else None,
            "per_10k_characters": round(total_cost * 10_000 / characters, 6)
            if currency and characters
            else None,
            "unpriced_models": unpriced,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="汇总单个批量摄入任务的时间、token 与 API 成本")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--conversion-report", required=True)
    parser.add_argument("--llm-ledger")
    parser.add_argument("--rate-card", help="可选模型价目 JSON；不提供时只统计 token")
    parser.add_argument("--out", help="可选输出 JSON；默认打印到终端")
    args = parser.parse_args()

    result = summarize(
        _read_json(args.conversion_report),
        _read_jsonl(args.llm_ledger),
        args.batch_id,
        _read_json(args.rate_card) if args.rate_card else None,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
