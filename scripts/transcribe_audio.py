"""Local faster-whisper adapter with chunk coverage and quality checks."""

from __future__ import annotations

import json
import os
import re
import sys
import hashlib
from importlib.metadata import version
from pathlib import Path


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def chunk_ranges(duration: float, chunk_seconds: float) -> list[tuple[float, float]]:
    """Split an audio timeline into contiguous, non-overlapping chunks."""
    if duration <= 0:
        raise ValueError("音频时长必须大于 0")
    if chunk_seconds <= 0:
        raise ValueError("KB_WHISPER_CHUNK_SEC 必须大于 0")
    ranges = []
    start = 0.0
    while start < duration:
        end = min(start + chunk_seconds, duration)
        ranges.append((start, end))
        start = end
    return ranges


def _audio_duration(path: str) -> float:
    """Read container duration through PyAV, already required by faster-whisper."""
    import av

    with av.open(path) as container:
        if container.duration is not None:
            return float(container.duration / av.time_base)
        durations = [
            float(stream.duration * stream.time_base)
            for stream in container.streams.audio
            if stream.duration is not None and stream.time_base is not None
        ]
    if not durations:
        raise ValueError("无法读取音频时长")
    return max(durations)


def _normalized_text(text: str) -> str:
    return re.sub(r"[^\w]+", "", text.casefold(), flags=re.UNICODE)


def normalize_segment_text(segments: list[dict], converter) -> int:
    """Normalize segment and word text in place; return changed segment count."""
    changed = 0
    for segment in segments:
        original = segment.get("text", "")
        normalized = converter.convert(original)
        if normalized != original:
            changed += 1
            segment["text"] = normalized
        for word in segment.get("words") or []:
            word["text"] = converter.convert(word.get("text", ""))
    return changed


def _workspace_review_path(source: Path) -> Path:
    for parent in source.resolve().parents:
        if parent.name.lower() == "raw":
            return parent.parent / "wiki" / "source-reviews.json"
    return source.resolve().parent / "wiki" / "source-reviews.json"


def load_audio_reviews(source: Path) -> tuple[str | None, list[dict]]:
    """Load human-confirmed repetition reviews for one immutable raw source."""
    review_path = _workspace_review_path(source)
    if not review_path.exists():
        return None, []
    review_bytes = review_path.read_bytes()
    payload = json.loads(review_bytes.decode("utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("sources"), dict):
        raise ValueError(f"人工复核文件格式无效: {review_path}")
    with source.open("rb") as stream:
        source_id = f"sha256:{hashlib.file_digest(stream, 'sha256').hexdigest()}"
    source_reviews = payload["sources"].get(source_id, {})
    reviews = source_reviews.get("audio_repetitions", [])
    if not isinstance(reviews, list):
        raise ValueError(f"人工复核记录 audio_repetitions 必须是数组: {review_path}")
    return hashlib.sha256(review_bytes).hexdigest(), reviews


def repetition_is_confirmed(run: dict, reviews: list[dict]) -> bool:
    for review in reviews:
        if review.get("verdict") != "confirmed_actual":
            continue
        if _normalized_text(str(review.get("text", ""))) != _normalized_text(run["text"]):
            continue
        if float(review.get("start", 0)) < run["end"] and float(review.get("end", 0)) > run["start"]:
            return True
    return False


def parse_retry_ranges(value: str, segments: list[dict]) -> list[dict]:
    """Parse comma-separated start-end seconds into retry records."""
    ranges = []
    for item in filter(None, (part.strip() for part in value.split(","))):
        start_text, separator, end_text = item.partition("-")
        if not separator:
            raise ValueError(f"局部重转写区间格式无效: {item}")
        start, end = float(start_text), float(end_text)
        if start < 0 or end <= start:
            raise ValueError(f"局部重转写区间无效: {item}")
        originals = [
            segment["text"]
            for segment in segments
            if start <= (segment["start"] + segment["end"]) / 2 < end
        ]
        ranges.append(
            {
                "start": start,
                "end": end,
                "text": " | ".join(originals),
                "count": len(originals),
                "trigger": "explicit",
            }
        )
    return ranges


def repeated_segment_runs(segments: list[dict], minimum_run: int = 5) -> list[dict]:
    """Find consecutive identical non-empty transcript segments."""
    runs = []
    run_start = 0
    while run_start < len(segments):
        normalized = _normalized_text(segments[run_start].get("text", ""))
        run_end = run_start + 1
        while (
            normalized
            and run_end < len(segments)
            and _normalized_text(segments[run_end].get("text", "")) == normalized
        ):
            run_end += 1
        if normalized and run_end - run_start >= minimum_run:
            runs.append(
                {
                    "text": segments[run_start].get("text", "").strip(),
                    "count": run_end - run_start,
                    "start": segments[run_start]["start"],
                    "end": segments[run_end - 1]["end"],
                }
            )
        run_start = run_end
    return runs


def replace_segments_in_range(
    segments: list[dict], start: float, end: float, replacements: list[dict]
) -> list[dict]:
    """Replace segments whose midpoint lies in one retry range."""
    kept = [
        segment
        for segment in segments
        if not start <= (segment["start"] + segment["end"]) / 2 < end
    ]
    merged = sorted([*kept, *replacements], key=lambda item: (item["start"], item["end"]))
    for segment_id, segment in enumerate(merged):
        segment["id"] = segment_id
    return merged


def refresh_chunk_counts(chunks: list[dict], segments: list[dict]) -> None:
    """Keep chunk statistics aligned with repaired transcript segments."""
    for chunk in chunks:
        if chunk["status"] == "failed":
            continue
        chunk["segment_count"] = sum(
            1
            for segment in segments
            if chunk["start"]
            <= (segment["start"] + segment["end"]) / 2
            < chunk["end"]
        )
        chunk["status"] = "success" if chunk["segment_count"] else "no_speech"


def _segment_payload(segment, chunk_id: int, converter) -> dict:
    return {
        "id": 0,
        "chunk_id": chunk_id,
        "start": segment.start,
        "end": segment.end,
        "text": converter.convert(segment.text.strip()),
        "avg_logprob": segment.avg_logprob,
        "no_speech_prob": segment.no_speech_prob,
        "words": [
            {
                "start": word.start,
                "end": word.end,
                "text": converter.convert(word.word),
                "probability": word.probability,
            }
            for word in (segment.words or [])
        ],
    }


def assess_transcript(
    duration: float,
    chunks: list[dict],
    segments: list[dict],
    confirmed_repetitions: list[dict] | None = None,
) -> tuple[str, float, float, list[dict]]:
    """Return status, processed duration, coverage ratio, and quality issues."""
    completed = [chunk for chunk in chunks if chunk["status"] != "failed"]
    processed_duration = sum(chunk["end"] - chunk["start"] for chunk in completed)
    coverage = min(1.0, processed_duration / duration) if duration else 0.0
    issues = []

    failed = [chunk["id"] for chunk in chunks if chunk["status"] == "failed"]
    empty = [chunk["id"] for chunk in chunks if chunk["status"] == "no_speech"]
    if failed:
        issues.append(
            {
                "code": "failed_chunks",
                "message": f"{len(failed)} 个音频分块转写失败",
                "chunk_ids": failed,
            }
        )
    if empty:
        issues.append(
            {
                "code": "empty_chunks",
                "message": f"{len(empty)} 个音频分块未识别到语音，需复核",
                "chunk_ids": empty,
            }
        )
    if coverage < 0.999999:
        issues.append(
            {
                "code": "incomplete_processing_coverage",
                "message": f"音频处理覆盖不完整：{coverage:.2%}",
                "coverage": coverage,
            }
        )

    previous_start = -1.0
    timestamp_errors = []
    for segment in segments:
        start = float(segment["start"])
        end = float(segment["end"])
        if start < 0 or end < start or end > duration + 0.5 or start < previous_start:
            timestamp_errors.append(segment["id"])
        previous_start = start
    if timestamp_errors:
        issues.append(
            {
                "code": "invalid_timestamps",
                "message": f"{len(timestamp_errors)} 个转写片段时间戳回退或越界",
                "segment_ids": timestamp_errors,
            }
        )

    confirmed_repetitions = confirmed_repetitions or []
    for run in repeated_segment_runs(segments):
        if repetition_is_confirmed(run, confirmed_repetitions):
            continue
        issues.append(
            {
                "code": "repeated_text_review",
                "message": f"检测到连续重复转写“{run['text']}”共 {run['count']} 次，需听录复核",
                **run,
            }
        )

    if not segments and not issues:
        return "no_speech", processed_duration, coverage, issues
    if issues:
        status = "failed" if not completed else "degraded"
        return status, processed_duration, coverage, issues
    return "success", processed_duration, coverage, issues


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: python scripts/transcribe_audio.py <audio>", file=sys.stderr)
        return 2
    try:
        from faster_whisper import WhisperModel
        from opencc import OpenCC
    except ImportError:
        print(
            "音频依赖未安装，请运行: python -m pip install -r requirements-audio.txt",
            file=sys.stderr,
        )
        return 2

    model_name = os.environ.get("KB_WHISPER_MODEL", "small").strip() or "small"
    device = os.environ.get("KB_WHISPER_DEVICE", "cpu").strip() or "cpu"
    compute_type = os.environ.get("KB_WHISPER_COMPUTE_TYPE", "int8").strip() or "int8"
    language = os.environ.get("KB_WHISPER_LANGUAGE", "zh").strip() or None
    chunk_seconds = float(os.environ.get("KB_WHISPER_CHUNK_SEC", "600"))
    retry_context = float(os.environ.get("KB_WHISPER_RETRY_CONTEXT_SEC", "12"))
    base_transcript_path = os.environ.get("KB_WHISPER_BASE_TRANSCRIPT", "").strip()
    explicit_retry_ranges = os.environ.get("KB_WHISPER_RETRY_RANGES", "").strip()
    try:
        text_converter = OpenCC("t2s.json")
        audio_review_sha256, confirmed_repetitions = load_audio_reviews(Path(sys.argv[1]))
        base_transcript = None
        if base_transcript_path:
            base_bytes = Path(base_transcript_path).read_bytes()
            base_transcript = json.loads(base_bytes.decode("utf-8"))
            duration = float(base_transcript["duration"])
            segments = base_transcript["segments"]
            chunks = base_transcript["chunks"]
            base_transcript_sha256 = hashlib.sha256(base_bytes).hexdigest()
            normalize_segment_text(segments, text_converter)
        else:
            duration = _audio_duration(sys.argv[1])
            segments = []
            chunks = []
            base_transcript_sha256 = None
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        info = None
        for chunk_id, (start, end) in enumerate(
            [] if base_transcript is not None else chunk_ranges(duration, chunk_seconds)
        ):
            chunk = {"id": chunk_id, "start": start, "end": end}
            before_count = len(segments)
            try:
                segments_iter, chunk_info = model.transcribe(
                    sys.argv[1],
                    language=language,
                    vad_filter=True,
                    word_timestamps=True,
                    condition_on_previous_text=False,
                    clip_timestamps=f"{start},{end}",
                )
                if info is None:
                    info = chunk_info
                for segment in segments_iter:
                    payload = _segment_payload(segment, chunk_id, text_converter)
                    if not payload["text"]:
                        continue
                    payload["id"] = len(segments)
                    segments.append(payload)
                chunk["segment_count"] = len(segments) - before_count
                chunk["status"] = (
                    "success" if chunk["segment_count"] else "no_speech"
                )
            except Exception as exc:  # noqa: BLE001 - 保留失败分块并继续覆盖后续音频
                chunk.update(
                    status="failed",
                    segment_count=0,
                    error=str(exc)[:500],
                )
            chunks.append(chunk)

        retry_ranges = (
            parse_retry_ranges(explicit_retry_ranges, segments)
            if explicit_retry_ranges
            else [
                run
                for run in repeated_segment_runs(segments)
                if not repetition_is_confirmed(run, confirmed_repetitions)
            ]
        )
        repairs = []
        for repair_id, run in enumerate(retry_ranges):
            clip_start = max(0.0, run["start"] - retry_context)
            clip_end = min(duration, run["end"] + retry_context)
            chunk_id = min(int(run["start"] // chunk_seconds), len(chunks) - 1)
            repair = {
                "id": repair_id,
                "start": run["start"],
                "end": run["end"],
                "clip_start": clip_start,
                "clip_end": clip_end,
                "original_text": run["text"],
                "original_count": run["count"],
                "trigger": run.get("trigger", "quality_gate"),
            }
            try:
                repair_iter, _ = model.transcribe(
                    sys.argv[1],
                    language=language,
                    vad_filter=True,
                    word_timestamps=True,
                    condition_on_previous_text=False,
                    hallucination_silence_threshold=2.0,
                    clip_timestamps=f"{clip_start},{clip_end}",
                )
                replacements = []
                for segment in repair_iter:
                    payload = _segment_payload(segment, chunk_id, text_converter)
                    midpoint = (payload["start"] + payload["end"]) / 2
                    if payload["text"] and run["start"] <= midpoint < run["end"]:
                        replacements.append(payload)
                if replacements:
                    original = [
                        item["text"]
                        for item in segments
                        if run["start"]
                        <= (item["start"] + item["end"]) / 2
                        < run["end"]
                    ]
                    segments = replace_segments_in_range(
                        segments, run["start"], run["end"], replacements
                    )
                    replacement_text = [item["text"] for item in replacements]
                    repair["status"] = (
                        "changed" if replacement_text != original else "unchanged"
                    )
                    repair["replacement_segment_count"] = len(replacements)
                else:
                    repair.update(status="no_speech", replacement_segment_count=0)
            except Exception as exc:  # noqa: BLE001 - 单个复核区间失败不丢弃主转写
                repair.update(
                    status="failed",
                    replacement_segment_count=0,
                    error=str(exc)[:500],
                )
            repairs.append(repair)
    except Exception as exc:  # noqa: BLE001 - 转换入口需要可解释的本地失败
        print(f"faster-whisper 转写失败: {exc}", file=sys.stderr)
        return 1

    refresh_chunk_counts(chunks, segments)
    text = "\n".join(item["text"] for item in segments if item["text"])
    status, processed_duration, coverage, issues = assess_transcript(
        duration, chunks, segments, confirmed_repetitions
    )
    applied_reviews = [
        review
        for review in confirmed_repetitions
        if any(repetition_is_confirmed(run, [review]) for run in repeated_segment_runs(segments))
    ]
    detected_language = (
        info.language
        if info is not None
        else base_transcript.get("language", language)
        if base_transcript is not None
        else language
    )
    language_probability = (
        info.language_probability
        if info is not None
        else base_transcript.get("language_probability")
        if base_transcript is not None
        else None
    )
    payload = {
        "schema_version": 4,
        "status": status,
        "engine": "faster-whisper",
        "engine_version": version("faster-whisper"),
        "model": model_name,
        "device": device,
        "compute_type": compute_type,
        "vad_filter": True,
        "word_timestamps": True,
        "condition_on_previous_text": False,
        "retry_context_seconds": retry_context,
        "repair_mode": "base_transcript" if base_transcript is not None else "full",
        "base_transcript_sha256": base_transcript_sha256,
        "text_normalization": "opencc:t2s",
        "text_normalization_version": version("opencc"),
        "audio_review_sha256": audio_review_sha256,
        "quality_reviews_applied": applied_reviews,
        "language": detected_language,
        "language_probability": language_probability,
        "duration": duration,
        "duration_after_vad": None,
        "chunk_seconds": chunk_seconds,
        "chunk_count": len(chunks),
        "chunks": chunks,
        "repairs": repairs,
        "processed_duration": processed_duration,
        "processing_coverage": coverage,
        "last_segment_end": max((item["end"] for item in segments), default=None),
        "issues": issues,
        "text": text,
        "segments": segments,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
