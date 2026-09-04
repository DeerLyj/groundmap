"""Chunk coverage and quality-gate tests for the local audio adapter."""

import pytest

from scripts.transcribe_audio import (
    assess_transcript,
    chunk_ranges,
    parse_retry_ranges,
    refresh_chunk_counts,
    replace_segments_in_range,
    normalize_segment_text,
)


def _segment(segment_id, start, end, text):
    return {"id": segment_id, "start": start, "end": end, "text": text}


def test_chunk_ranges_cover_long_audio_without_gaps():
    ranges = chunk_ranges(6773.551, 600)

    assert len(ranges) == 12
    assert ranges[0] == (0.0, 600.0)
    assert ranges[-1] == pytest.approx((6600.0, 6773.551))
    assert all(left[1] == right[0] for left, right in zip(ranges, ranges[1:]))


def test_quality_gate_accepts_full_chunk_processing():
    chunks = [
        {"id": 0, "start": 0.0, "end": 600.0, "status": "success"},
        {"id": 1, "start": 600.0, "end": 900.0, "status": "success"},
    ]
    segments = [_segment(0, 2.0, 4.0, "正常内容")]

    status, processed, coverage, issues = assess_transcript(900.0, chunks, segments)

    assert status == "success"
    assert processed == 900.0
    assert coverage == 1.0
    assert issues == []


def test_quality_gate_rejects_failed_empty_and_repeated_chunks():
    chunks = [
        {"id": 0, "start": 0.0, "end": 600.0, "status": "success"},
        {"id": 1, "start": 600.0, "end": 1200.0, "status": "no_speech"},
        {"id": 2, "start": 1200.0, "end": 1800.0, "status": "failed"},
    ]
    segments = [_segment(index, index, index + 0.5, "12") for index in range(5)]

    status, processed, coverage, issues = assess_transcript(1800.0, chunks, segments)
    codes = {issue["code"] for issue in issues}

    assert status == "degraded"
    assert processed == 1200.0
    assert coverage == pytest.approx(2 / 3)
    assert codes == {
        "failed_chunks",
        "empty_chunks",
        "incomplete_processing_coverage",
        "repeated_text_review",
    }


def test_quality_gate_accepts_human_confirmed_repetition():
    chunks = [{"id": 0, "start": 0.0, "end": 10.0, "status": "success"}]
    segments = [_segment(index, index, index + 0.5, "Hello") for index in range(5)]
    reviews = [
        {
            "start": 0.0,
            "end": 6.0,
            "text": "Hello",
            "verdict": "confirmed_actual",
        }
    ]

    status, _, _, issues = assess_transcript(10.0, chunks, segments, reviews)

    assert status == "success"
    assert issues == []


def test_simplified_chinese_normalization_updates_segments_and_words():
    class FakeConverter:
        def convert(self, text):
            return text.replace("軟件", "软件")

    segments = [
        {
            "text": "軟件系统",
            "words": [{"text": "軟件"}, {"text": "系统"}],
        }
    ]

    changed = normalize_segment_text(segments, FakeConverter())

    assert changed == 1
    assert segments[0]["text"] == "软件系统"
    assert segments[0]["words"][0]["text"] == "软件"


def test_quality_gate_rejects_timestamp_regression_and_bounds():
    chunks = [{"id": 0, "start": 0.0, "end": 10.0, "status": "success"}]
    segments = [
        _segment(0, 5.0, 6.0, "一"),
        _segment(1, 4.0, 11.0, "二"),
    ]

    status, _, _, issues = assess_transcript(10.0, chunks, segments)

    assert status == "degraded"
    assert [issue["code"] for issue in issues] == ["invalid_timestamps"]


def test_retry_replaces_only_segments_inside_anomaly_range():
    original = [
        _segment(0, 8.0, 9.0, "保留前文"),
        _segment(1, 10.0, 11.0, "12"),
        _segment(2, 11.0, 12.0, "12"),
        _segment(3, 13.0, 14.0, "保留后文"),
    ]
    replacement = [_segment(0, 10.2, 11.8, "修复内容")]

    merged = replace_segments_in_range(original, 10.0, 13.0, replacement)

    assert [item["text"] for item in merged] == ["保留前文", "修复内容", "保留后文"]
    assert [item["id"] for item in merged] == [0, 1, 2]


def test_explicit_retry_ranges_capture_current_text():
    segments = [
        _segment(0, 9.0, 10.5, "前文"),
        _segment(1, 10.5, 11.5, "异常"),
        _segment(2, 12.5, 13.5, "后文"),
    ]

    ranges = parse_retry_ranges("10-12,20-21", segments)

    assert ranges == [
        {"start": 10.0, "end": 12.0, "text": "异常", "count": 1, "trigger": "explicit"},
        {"start": 20.0, "end": 21.0, "text": "", "count": 0, "trigger": "explicit"},
    ]


def test_repair_refreshes_chunk_segment_counts():
    chunks = [
        {"id": 0, "start": 0.0, "end": 10.0, "status": "success", "segment_count": 9},
        {"id": 1, "start": 10.0, "end": 20.0, "status": "success", "segment_count": 9},
    ]
    segments = [_segment(0, 1.0, 2.0, "仅剩一段")]

    refresh_chunk_counts(chunks, segments)

    assert chunks[0]["segment_count"] == 1
    assert chunks[0]["status"] == "success"
    assert chunks[1]["segment_count"] == 0
    assert chunks[1]["status"] == "no_speech"
