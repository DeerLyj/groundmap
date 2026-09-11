from scripts.ingest_cost import summarize


def test_summarize_filters_batch_and_prices_cached_tokens():
    conversion = {
        "batch_id": "b1",
        "duration_ms": 1000,
        "totals": {
            "converted": 1,
            "quality_success": 1,
            "degraded": 0,
            "failed": 0,
            "input_bytes": 2000,
        },
        "files": [{"characters": 10_000}],
    }
    runs = [
        {
            "batch_id": "b1",
            "provider": "deepseek",
            "model": "pro",
            "input_tokens": 1000,
            "cached_input_tokens": 400,
            "output_tokens": 200,
            "duration_ms": 500,
        },
        {"batch_id": "other", "provider": "deepseek", "model": "pro", "input_tokens": 9999},
    ]
    rates = {
        "currency": "CNY",
        "models": {
            "deepseek/pro": {
                "input_per_million": 10,
                "cached_input_per_million": 2,
                "output_per_million": 20,
            }
        },
    }

    result = summarize(conversion, runs, "b1", rates)

    assert result["llm"]["input_tokens"] == 1000
    assert result["llm"]["cached_input_tokens"] == 400
    assert result["api_cost"]["total"] == 0.0108
    assert result["api_cost"]["per_converted_file"] == 0.0108
    assert result["api_cost"]["per_10k_characters"] == 0.0108
