"""
markitdown 文档转换脚本

将 raw/ 目录中的各种文档（PDF、DOCX、PPTX、XLSX 等）转换为 Markdown 格式。
原件保持只读；Markdown、outline 和 Source Manifest 写入同 workspace 的 derived/。

说明：图片会被扫描到，但 MarkItDown 本身不负责 OCR。默认使用本地 RapidOCR；
也可以通过 KB_OCR_ENGINE 切换到 PaddleOCR 或 Tesseract，或用
KB_OCR_COMMAND 覆盖为任意外部 OCR 命令。OCR 失败时不会生成空 Markdown 页面冒充成功。

用法:
    python scripts/convert.py                  # 增量转换 raw/ 下所有支持的文件
    python scripts/convert.py --force          # 强制重新转换所有文件
    python scripts/convert.py --dry-run        # 只列出待转换文件，不执行
    python scripts/convert.py --ext .pdf,.docx # 只处理指定格式
    python scripts/convert.py --dir path/to/   # 指定扫描目录

依赖:
    pip install 'markitdown[all]'

图片 OCR:
    默认（推荐的轻量本地方案）：
    KB_OCR_ENGINE=rapidocr
    python -m pip install -r requirements-ocr.txt

    中文复杂版面升级：
    KB_OCR_ENGINE=paddleocr
    （按 PaddleOCR 官方文档安装 PaddlePaddle 与 PaddleOCR）

    简单基线：
    KB_OCR_ENGINE=tesseract
    （Windows 需安装 Tesseract，并准备 chi_sim / eng 语言数据）

    任意外部命令仍可覆盖默认引擎，命令中用 {input} 表示图片路径：
    KB_OCR_COMMAND="tesseract {input} stdout -l chi_sim+eng"
    可选 KB_OCR_FALLBACK_COMMAND 作为主引擎失败后的复核入口。
    OCR 命令由外部进程执行，convert.py 不内嵌 LLM 或视觉模型。

本地语音转写:
    python -m pip install -r requirements-audio.txt
    默认使用 faster-whisper small / CPU INT8 / VAD / word timestamps。
    可通过 KB_WHISPER_MODEL、KB_WHISPER_DEVICE、KB_WHISPER_COMPUTE_TYPE
    和 KB_WHISPER_LANGUAGE 调整；原始音频不会发送到云端服务。
"""

import argparse
import hashlib
import json
import math
import os
import re
import shlex
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _atomic_write_text(target: Path, content: str, encoding: str = "utf-8") -> None:
    """write-then-rename 原子写：先写到同目录的临时文件再 os.replace 重命名。
    保证别的进程读 target 时只能看到完整旧内容或完整新内容，不会读到半截。

    Windows 兼容：目标文件被另一进程持 read handle 时 os.replace 抛 PermissionError，
    重试 3 次（50ms 间隔）；最终失败保留 tmp 文件供手动收拾。
    """
    import time as _time

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=str(target.parent),
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding=encoding, newline="") as f:
            f.write(content)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    last_exc: Exception | None = None
    for _ in range(3):
        try:
            os.replace(tmp_path, str(target))
            return
        except PermissionError as e:
            last_exc = e
            _time.sleep(0.05)
    # 3 次都失败：清理 tmp 避免污染 git status；给 stderr 提示重试
    try:
        os.unlink(tmp_path)
    except OSError:
        print(
            f"[_atomic_write_text] 警告：临时文件无法清理：{tmp_path}",
            file=sys.stderr,
        )
    print(
        f"[_atomic_write_text] os.replace 失败 3 次（目标 {target} 可能被另一进程持锁）；"
        f"请稍后重试",
        file=sys.stderr,
    )
    if last_exc is not None:
        raise last_exc

try:
    from markitdown import MarkItDown
except ImportError:
    print("错误: 未安装 markitdown，请运行: pip install 'markitdown[all]'")
    sys.exit(1)

# 让 postprocess 模块可被 import（与 convert.py 同目录）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from postprocess import process as postprocess_text
from extract_embedded_media import extract_embedded_media

SUPPORTED_EXTENSIONS = {
    # 已是 markdown：仅做 postprocess（加锚点 + 生成 outline）
    ".md",
    # 文档
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls",
    # 网页与数据
    ".html", ".htm", ".csv", ".json", ".xml",
    # 电子书
    ".epub",
    # 图片
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp",
    # 音频
    ".mp3", ".wav", ".m4a",
    # 邮件
    ".msg",
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp"
}

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
OOXML_MEDIA_EXTENSIONS = {".docx", ".pptx"}

PIPELINE_VERSION = 3
AUDIO_PIPELINE_VERSION = 4

def _ocr_engine() -> str:
    """返回配置的 OCR 引擎；显式命令优先被标记为 custom-command。"""
    if os.environ.get("KB_OCR_COMMAND", "").strip():
        return "custom-command"
    return os.environ.get("KB_OCR_ENGINE", "rapidocr").strip().lower() or "rapidocr"


def _default_ocr_command(engine: str) -> tuple[str | None, str | None]:
    """为内置引擎生成外部命令，不在知识库核心内导入 OCR SDK。"""
    if engine == "tesseract":
        return "tesseract {input} stdout -l chi_sim+eng", None
    if engine not in {"rapidocr", "paddleocr"}:
        return None, (
            f"OCR 引擎无效: {engine}；可选 rapidocr、paddleocr、tesseract，"
            "或设置 KB_OCR_COMMAND"
        )
    wrapper_name = "ocr_rapid.py" if engine == "rapidocr" else "ocr_paddle.py"
    wrapper = Path(__file__).with_name(wrapper_name)
    if not wrapper.exists():
        return None, f"OCR 适配脚本不存在: {wrapper}"
    # shlex.split() 会在后续把带空格的 Python 路径解析为单个参数。
    json_flag = " --json" if engine == "rapidocr" else ""
    return (
        f"{shlex.quote(sys.executable)} {shlex.quote(str(wrapper))}"
        f"{json_flag} {{input}}",
        None,
    )


def _run_ocr_command(command: str, source: Path) -> tuple[bool, str]:
    """执行一个 OCR 命令；命令必须把文本写到 stdout。"""
    try:
        args = shlex.split(command)
    except ValueError as e:
        return False, f"OCR 命令解析失败: {e}"
    if not args or not any("{input}" in arg for arg in args):
        return False, "OCR 命令无效：必须使用 {input} 占位符指定图片路径"
    input_path = str(source.resolve())
    args = [arg.replace("{input}", input_path) for arg in args]
    try:
        command_env = os.environ.copy()
        # 内置 Python 适配器在 Windows 管道中也统一输出 UTF-8，避免中文错误信息乱码。
        command_env.setdefault("PYTHONIOENCODING", "utf-8")
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=command_env,
            timeout=int(os.environ.get("KB_OCR_TIMEOUT_SEC", "120")),
            check=False,
        )
    except FileNotFoundError:
        return False, f"OCR 命令不存在: {args[0]}"
    except subprocess.TimeoutExpired:
        return False, "OCR 超时：可通过 KB_OCR_TIMEOUT_SEC 调整超时时间"
    except (OSError, ValueError) as e:
        return False, f"OCR 执行失败: {e}"
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        suffix = f": {detail[:300]}" if detail else ""
        return False, f"OCR 返回错误码 {result.returncode}{suffix}"
    text = result.stdout.strip()
    if not text:
        return False, "OCR 未识别到文字"
    return True, text


def _normalize_ocr_payload(payload: dict | str, engine: str) -> dict:
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = {
                "status": "ocr_success",
                "engine": engine,
                "engine_version": "unknown",
                "text": payload,
                "blocks": [
                    {"text": line, "bbox": None, "confidence": None}
                    for line in payload.splitlines()
                    if line.strip()
                ],
            }
        payload = parsed
    confidences = [
        block["confidence"]
        for block in payload.get("blocks", [])
        if isinstance(block.get("confidence"), (int, float))
    ]
    threshold = float(os.environ.get("KB_OCR_REVIEW_THRESHOLD", "0.8"))
    average = sum(confidences) / len(confidences) if confidences else None
    low_count = sum(score < threshold for score in confidences)
    status = payload.get("status", "failed")
    payload["average_confidence"] = average
    payload["low_confidence_blocks"] = low_count
    payload["review_threshold"] = threshold
    payload["recognition_status"] = (
        "needs_visual_review"
        if status == "ocr_success" and low_count
        else status
    )
    payload["needs_review"] = status != "ocr_success" or bool(low_count)
    return payload


def ocr_image(source: Path) -> tuple[bool, dict | str]:
    """调用配置的外部 OCR 命令，返回 (成功与否, 文本或错误信息)。

    使用 shell=False，且只把 source 作为独立参数/占位符替换，避免图片路径
    被 shell 二次解释。命令必须显式包含 {input}，防止误把图片路径传给错误参数。
    """
    command = os.environ.get("KB_OCR_COMMAND", "").strip()
    if not command:
        command, config_error = _default_ocr_command(_ocr_engine())
        if config_error:
            return False, config_error
    ok, result = _run_ocr_command(command, source)
    if ok:
        return True, _normalize_ocr_payload(result, _ocr_engine())

    fallback = os.environ.get("KB_OCR_FALLBACK_COMMAND", "").strip()
    if fallback:
        fallback_ok, fallback_result = _run_ocr_command(fallback, source)
        if fallback_ok:
            return True, _normalize_ocr_payload(fallback_result, "fallback-command")
        return False, f"主 OCR 失败: {result}；复核 OCR 失败: {fallback_result}"
    return False, result


def ocr_images(sources: list[Path]) -> dict[Path, tuple[bool, dict | str]]:
    """OCR a batch with one RapidOCR process; other engines keep the existing path."""
    if not sources:
        return {}
    if os.environ.get("KB_OCR_COMMAND", "").strip() or _ocr_engine() != "rapidocr":
        return {source: ocr_image(source) for source in sources}

    wrapper = Path(__file__).with_name("ocr_rapid.py")
    args = [sys.executable, str(wrapper), "--json", *(str(path.resolve()) for path in sources)]
    command_env = os.environ.copy()
    command_env.setdefault("PYTHONIOENCODING", "utf-8")
    timeout = int(os.environ.get("KB_OCR_TIMEOUT_SEC", "120")) * max(
        1, math.ceil(len(sources) / 10)
    )
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=command_env,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {source: (False, f"RapidOCR 批处理失败: {exc}") for source in sources}
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return {source: (False, detail or "RapidOCR 批处理失败") for source in sources}
    try:
        payload = json.loads(result.stdout)
        items = payload.get("results", [payload])
    except (AttributeError, json.JSONDecodeError) as exc:
        return {source: (False, f"RapidOCR JSON 无效: {exc}") for source in sources}
    outputs = {}
    for index, source in enumerate(sources):
        if index >= len(items):
            outputs[source] = (False, "RapidOCR 批处理结果数量不完整")
        else:
            outputs[source] = (
                True,
                _normalize_ocr_payload(items[index], "rapidocr"),
            )
    return outputs


def get_project_root() -> Path:
    """获取项目根目录（scripts/ 的父目录）"""
    return Path(__file__).resolve().parent.parent


_BASE_ROOT: Path | None = None
_SOURCE_ROOT: Path | None = None
_DERIVED_ROOT: Path | None = None


def _target_paths(source: Path) -> tuple[Path, Path, Path]:
    """Return derived markdown, outline, and manifest paths for a raw source."""
    source_root = _SOURCE_ROOT or source.parent
    derived_root = _DERIVED_ROOT or source.parent / "derived"
    rel = source.resolve().relative_to(source_root.resolve())
    target_md = (derived_root / rel).with_suffix(".md")
    return target_md, target_md.with_suffix(".outline.json"), target_md.with_suffix(".source.json")


def _artifact_paths(target_md: Path) -> tuple[Path, Path, Path]:
    """Return quality, visual, and embedded-media directory paths."""
    return (
        target_md.with_suffix(".quality.json"),
        target_md.with_suffix(".visual.json"),
        target_md.parent / f"{target_md.stem}.assets",
    )


def _transcript_path(target_md: Path) -> Path:
    return target_md.with_suffix(".transcript.json")


def _file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _audio_review_path(source: Path) -> Path:
    for parent in source.resolve().parents:
        if parent.name.lower() == "raw":
            return parent.parent / "wiki" / "source-reviews.json"
    return (_BASE_ROOT or get_project_root()) / "wiki" / "source-reviews.json"


def _audio_review_sha256(source: Path) -> str | None:
    review_path = _audio_review_path(source)
    return _file_sha256(review_path) if review_path.is_file() else None


def should_convert(source: Path, force: bool) -> bool:
    """判断文件是否需要（重新）处理。
    三个派生产物必须齐全；源文件指纹或转换管线版本变化时重建。
    """
    if force:
        return True
    target_md, target_outline, target_manifest = _target_paths(source)
    target_quality, _, _ = _artifact_paths(target_md)
    if (
        not target_md.exists()
        or not target_outline.exists()
        or not target_manifest.exists()
        or not target_quality.exists()
    ):
        return True
    try:
        manifest = json.loads(target_manifest.read_text(encoding="utf-8"))
        stat = source.stat()
        with target_md.open("rb") as derived_file:
            derived_hash = hashlib.file_digest(derived_file, "sha256").hexdigest()
        changed = (
            manifest.get("pipeline_version") != PIPELINE_VERSION
            or (
                source.suffix.lower() in AUDIO_EXTENSIONS
                and manifest.get("audio_pipeline_version") != AUDIO_PIPELINE_VERSION
            )
            or (
                source.suffix.lower() in AUDIO_EXTENSIONS
                and manifest.get("audio_review_sha256") != _audio_review_sha256(source)
            )
            or manifest.get("source_size") != stat.st_size
            or manifest.get("source_mtime_ns") != stat.st_mtime_ns
            or manifest.get("derived_sha256") != derived_hash
        )
        if changed:
            return True
        base = (_BASE_ROOT or get_project_root()).resolve()
        artifacts = manifest.get("artifacts")
        if not isinstance(artifacts, list):
            return True
        for artifact in artifacts:
            artifact_path = (base / artifact["path"]).resolve()
            artifact_path.relative_to(base)
            if not artifact_path.is_file():
                return True
            expected_hash = artifact.get("sha256")
            if expected_hash and _file_sha256(artifact_path) != expected_hash:
                return True
        return False
    except (KeyError, OSError, TypeError, ValueError):
        return True


def collect_files(scan_dir: Path, extensions: set[str] | None) -> list[Path]:
    """收集目录下所有待处理的文件，跳过派生产物（*.outline.json / *.outline.md）。"""
    allowed = extensions if extensions else SUPPORTED_EXTENSIONS
    files = []
    for file_path in sorted(scan_dir.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in allowed:
            continue
        if file_path.name == ".gitkeep":
            continue
        # 跳过 convert.py 自己的派生产物（避免被再次处理）
        if file_path.stem.lower().endswith(".outline"):
            continue
        files.append(file_path)
    return files


def _project_relative_posix(path: Path) -> str:
    """把绝对路径转换成相对 base root（workspace 根 / 项目根）的 POSIX 路径，
    供 outline.json 的 doc_path 字段使用。"""
    base = _BASE_ROOT or get_project_root()
    try:
        rel = path.resolve().relative_to(base)
    except ValueError:
        return path.name
    return str(rel).replace("\\", "/")


def _docling_pdf_markdown(source: Path) -> tuple[bool, str, str]:
    """用 Docling + OCR 处理没有文本层的 PDF；依赖按需导入。"""
    try:
        # Windows 非开发者模式下禁用 HF cache symlink，避免模型下载失败。
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
    except ImportError as exc:
        return False, "", f"Docling 未安装: {exc}"

    try:
        pipeline_options = PdfPipelineOptions(do_ocr=True)
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        result = converter.convert(str(source))
        markdown = result.document.export_to_markdown()
    except Exception as exc:  # noqa: BLE001 - 将可解释错误写入验收输出
        return False, "", f"Docling + OCR 执行失败: {exc}"

    if not markdown.strip():
        return False, "", "Docling + OCR 输出为空"
    return True, markdown, "docling+ocr"


def _transcribe_audio(source: Path) -> tuple[bool, dict | str]:
    """Run the local faster-whisper adapter; no shell or network API is used."""
    wrapper = Path(__file__).with_name("transcribe_audio.py")
    if not wrapper.exists():
        return False, f"本地音频转写适配器不存在: {wrapper}"
    command_env = os.environ.copy()
    command_env.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        result = subprocess.run(
            [sys.executable, str(wrapper), str(source.resolve())],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=command_env,
            timeout=int(os.environ.get("KB_WHISPER_TIMEOUT_SEC", "3600")),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"本地音频转写失败: {exc}"
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return False, detail or f"音频转写返回错误码 {result.returncode}"
    try:
        return True, json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return False, f"音频转写 JSON 无效: {exc}"


def _timecode(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"


def _transcript_markdown(source: Path, transcript: dict) -> str:
    lines = [f"# {source.stem}", "", "## 语音转写", ""]
    if transcript["status"] == "no_speech":
        return "\n".join(lines + ["（VAD 未检测到语音。）", ""])
    if transcript["status"] in {"degraded", "failed"}:
        lines.extend(["（转写质量闸门未通过，请结合 quality.json 复核。）", ""])
    for segment in transcript["segments"]:
        lines.extend(
            [
                f"### {_timecode(segment['start'])}–{_timecode(segment['end'])}",
                "",
                segment["text"],
                "",
            ]
        )
    return "\n".join(lines)


def _without_markdown_images(markdown: str) -> str:
    """Remove MarkItDown image placeholders before adding exported local assets."""
    return re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)


def _locator_text(locator: dict) -> str:
    if locator["kind"] == "pptx":
        shape = locator.get("shape_name") or f"shape {locator['shape']}"
        return (
            f"slide {locator['slide']}, {shape}, "
            f"relationship {locator['relationship_id']}"
        )
    return (
        f"{locator['part']}, paragraph {locator['paragraph']}, "
        f"relationship {locator['relationship_id']}"
    )


def _prepare_embedded_media(source: Path, target_md: Path, markdown: str) -> tuple[str, dict]:
    """Export OOXML media and replace broken converter image references."""
    _, _, assets_dir = _artifact_paths(target_md)
    extracted = extract_embedded_media(source, assets_dir)
    occurrences_by_package: dict[str, list[dict]] = {}
    for occurrence in extracted["occurrences"]:
        occurrences_by_package.setdefault(occurrence["package_path"], []).append(
            occurrence["locator"]
        )
    renderable_paths = [
        asset["asset_path"]
        for asset in extracted["assets"]
        if asset["status"] == "exported"
    ]
    ocr_results = ocr_images(renderable_paths)

    asset_records = []
    markdown_lines = [
        "",
        "<!-- groundmap:embedded-media:start -->",
        "## 导出媒体",
        "",
    ]
    for asset in extracted["assets"]:
        asset_path = asset["asset_path"]
        relative_link = os.path.relpath(asset_path, target_md.parent).replace("\\", "/")
        locators = occurrences_by_package.get(asset["package_path"], [])
        record = {
            key: value
            for key, value in asset.items()
            if key != "asset_path"
        }
        record["asset_path"] = _project_relative_posix(asset_path)
        record["locators"] = locators
        ocr_markdown = asset_path.with_suffix(asset_path.suffix + ".ocr.md")
        if asset["status"] == "exported":
            ocr_ok, ocr_result = ocr_results[asset_path]
            if ocr_ok:
                record["ocr"] = dict(ocr_result)
                record["ocr"].pop("input", None)
            else:
                record["ocr"] = {
                    "status": "failed",
                    "recognition_status": "failed",
                    "engine": _ocr_engine(),
                    "text": "",
                    "blocks": [],
                    "error": str(ocr_result),
                    "needs_review": True,
                }
            record["recognition_status"] = record["ocr"]["recognition_status"]
            if record["ocr"]["text"]:
                _atomic_write_text(
                    ocr_markdown,
                    f"# OCR evidence\n\n{record['ocr']['text']}\n",
                )
                record["ocr_markdown_path"] = _project_relative_posix(ocr_markdown)
            else:
                ocr_markdown.unlink(missing_ok=True)
                record["ocr_markdown_path"] = None
        else:
            ocr_markdown.unlink(missing_ok=True)
            record["ocr"] = None
            record["recognition_status"] = "unsupported_render"
            record["ocr_markdown_path"] = None
        asset_records.append(record)

        markdown_lines.append(f"### {asset_path.name}")
        markdown_lines.append("")
        if asset["status"] == "exported":
            markdown_lines.append(f"![{asset_path.name}](<{relative_link}>)")
        else:
            markdown_lines.append(
                f"[{asset_path.name}](<{relative_link}>)（当前不支持直接渲染）"
            )
        markdown_lines.append("")
        if locators:
            markdown_lines.extend(
                f"- 来源位置：{_locator_text(locator)}" for locator in locators
            )
        else:
            markdown_lines.append("- 来源位置：未能从 OOXML 关系中定位")
        markdown_lines.append("")

    markdown_lines.append("<!-- groundmap:embedded-media:end -->")
    ocr_lines = [
        "",
        "<!-- groundmap:embedded-ocr:start -->",
        "## 图片 OCR 文本",
        "",
    ]
    for record in asset_records:
        if not record["ocr"]:
            continue
        ocr_lines.extend(["### 图片 OCR", ""])
        if record["ocr"]["text"]:
            ocr_lines.extend([record["ocr"]["text"], ""])
        else:
            ocr_lines.extend(["（未识别到文字，需视觉复核）", ""])
    ocr_lines.append("<!-- groundmap:embedded-ocr:end -->")
    return (
        _without_markdown_images(markdown).rstrip()
        + "\n"
        + "\n".join(markdown_lines + ocr_lines),
        {
            "schema_version": 1,
            "generator": "groundmap-ooxml-stdlib",
            "modality": "embedded_media",
            "assets": asset_records,
            "occurrence_count": len(extracted["occurrences"]),
            "unmapped_assets": extracted["unmapped_assets"],
            "missing_assets": extracted["missing_assets"],
            "needs_review": True,
        },
    )


def convert_file(md: MarkItDown, source: Path) -> tuple[bool, str]:
    """
    转换/处理单个文件。返回 (成功与否, 消息)。

    Pipeline:
      1. 非 .md：markitdown 转为 markdown 文本；.md：直接读原文
      2. postprocess.process 加锚点 + 生成 outline 数据
      3. 写 Markdown、outline、manifest 及对应模态的结构化派生物
    """
    suffix = source.suffix.lower()
    is_md = suffix == ".md"
    converter_used = "markdown" if is_md else ""
    visual_data = None
    transcript_data = None

    if is_md:
        try:
            markdown = source.read_text(encoding="utf-8")
        except Exception as e:
            return False, f"读取失败: {e}"
        target_md, target_outline, target_manifest = _target_paths(source)
    else:
        target_md, target_outline, target_manifest = _target_paths(source)
        if suffix in IMAGE_EXTENSIONS:
            # 图片必须经过显式 OCR；即便未来 MarkItDown 返回了 alt text 或元数据，
            # 也不能把它误当成图片文字识别结果。
            ok, ocr_result = ocr_image(source)
            if not ok:
                return False, str(ocr_result)
            ocr_result.pop("input", None)
            image_ref = os.path.relpath(source, target_md.parent).replace("\\", "/")
            ocr_text = ocr_result["text"] or "（未识别到文字，需视觉复核）"
            markdown = (
                f"# {source.stem}\n\n"
                f"![{source.name}]({image_ref})\n\n"
                f"<!-- OCR_ENGINE: {_ocr_engine()} -->\n"
                f"<!-- OCR_FALLBACK: {'configured' if os.environ.get('KB_OCR_FALLBACK_COMMAND', '').strip() else 'disabled'} -->\n\n"
                "## OCR 文本\n\n"
                f"{ocr_text}\n"
            )
            visual_data = {
                "schema_version": 1,
                "generator": "groundmap-image-ocr",
                "modality": "standalone_image",
                "assets": [
                    {
                        "package_path": None,
                        "asset_path": _project_relative_posix(source),
                        "sha256": _file_sha256(source),
                        "media_type": suffix.lstrip("."),
                        "status": "source",
                        "locators": [{"kind": "image"}],
                        "ocr": ocr_result,
                        "recognition_status": ocr_result["recognition_status"],
                    }
                ],
                "occurrence_count": 1,
                "unmapped_assets": [],
                "missing_assets": [],
                "needs_review": ocr_result["needs_review"],
            }
        elif suffix in AUDIO_EXTENSIONS:
            ok, transcript_result = _transcribe_audio(source)
            if not ok:
                return False, str(transcript_result)
            transcript_data = transcript_result
            markdown = _transcript_markdown(source, transcript_data)
            converter_used = "faster-whisper"
        else:
            markitdown_error = ""
            try:
                result = md.convert(str(source))
                markdown = result.markdown if result.markdown else ""
            except Exception as exc:  # noqa: BLE001 - 允许 PDF 进入升级路由
                markdown = ""
                markitdown_error = str(exc)
            converter_used = "markitdown"
            if not markdown.strip() and suffix == ".pdf":
                ok, docling_markdown, fallback_message = _docling_pdf_markdown(source)
                if ok:
                    markdown = docling_markdown
                    converter_used = fallback_message
                else:
                    detail = markitdown_error or "转换结果为空"
                    return False, f"{detail}；{fallback_message}"
            if not markdown.strip():
                return False, "转换结果为空"

        if suffix in OOXML_MEDIA_EXTENSIONS:
            try:
                markdown, visual_data = _prepare_embedded_media(
                    source, target_md, markdown
                )
            except (OSError, ValueError, zipfile.BadZipFile) as exc:
                return False, f"内嵌媒体导出失败: {exc}"

    doc_path = _project_relative_posix(target_md)

    # 读旧 outline（如果存在），让 process 保留 agent_summary
    previous_outline = None
    if target_outline.exists():
        try:
            previous_outline = json.loads(target_outline.read_text(encoding="utf-8"))
        except Exception:
            previous_outline = None

    text_with_anchors, outline_data = postprocess_text(
        markdown, doc_path, previous_outline=previous_outline
    )

    # 仅当内容变化时写 .md（保护 git 工作树）
    md_changed = (
        not target_md.exists()
        or target_md.read_text(encoding="utf-8") != text_with_anchors
    )
    if md_changed:
        _atomic_write_text(target_md, text_with_anchors)

    _atomic_write_text(
        target_outline,
        json.dumps(outline_data, ensure_ascii=False, indent=2),
    )

    stat = source.stat()
    source_hash = _file_sha256(source)
    source_id = f"sha256:{source_hash}"
    derived_hash = hashlib.sha256(text_with_anchors.encode("utf-8")).hexdigest()
    converter = (
        converter_used
        if converter_used
        else f"ocr:{_ocr_engine()}"
        if suffix in IMAGE_EXTENSIONS
        else "markitdown"
    )
    target_quality, target_visual, _ = _artifact_paths(target_md)
    artifacts = [
        {
            "type": "markdown",
            "path": doc_path,
            "sha256": derived_hash,
            "status": "success",
        },
        {
            "type": "outline",
            "path": _project_relative_posix(target_outline),
            "sha256": _file_sha256(target_outline),
            "status": "success",
        },
    ]
    quality_issues = []
    media_stats = None
    if visual_data is not None:
        visual_data["source_id"] = source_id
        visual_data["source_path"] = _project_relative_posix(source)
        _atomic_write_text(
            target_visual,
            json.dumps(visual_data, ensure_ascii=False, indent=2),
        )
        artifacts.append(
            {
                "type": "visual",
                "path": _project_relative_posix(target_visual),
                "sha256": _file_sha256(target_visual),
                "status": (
                    "needs_review" if visual_data["needs_review"] else "success"
                ),
            }
        )
        unsupported = sum(
            asset["status"] == "unsupported_render"
            for asset in visual_data["assets"]
        )
        media_stats = {
            "discovered_assets": len(visual_data["assets"]),
            "exported_assets": sum(
                asset["status"] in {"exported", "source"}
                for asset in visual_data["assets"]
            ),
            "renderable_assets": len(visual_data["assets"]) - unsupported,
            "unsupported_render_assets": unsupported,
            "occurrences": visual_data["occurrence_count"],
            "unmapped_assets": len(visual_data["unmapped_assets"]),
            "missing_assets": len(visual_data["missing_assets"]),
            "recognition": {
                status: sum(
                    asset["recognition_status"] == status
                    for asset in visual_data["assets"]
                )
                for status in (
                    "ocr_success",
                    "no_text",
                    "failed",
                    "needs_visual_review",
                    "unsupported_render",
                )
            },
        }
        if unsupported:
            quality_issues.append(f"{unsupported} 个媒体文件当前不支持直接渲染")
        if visual_data["unmapped_assets"]:
            quality_issues.append("存在未能定位来源关系的媒体文件")
        if visual_data["missing_assets"]:
            quality_issues.append("存在引用但未在包内发现的媒体文件")
        review_count = media_stats["recognition"]["needs_visual_review"]
        no_text_count = media_stats["recognition"]["no_text"]
        failed_count = media_stats["recognition"]["failed"]
        if review_count:
            quality_issues.append(f"{review_count} 张图片 OCR 置信度偏低，需视觉复核")
        if no_text_count:
            quality_issues.append(f"{no_text_count} 张图片未识别到文字，需视觉复核")
        if failed_count:
            quality_issues.append(f"{failed_count} 张图片 OCR 失败")
        if visual_data["modality"] == "embedded_media":
            artifacts.extend(
                {
                    "type": "embedded_media",
                    "path": asset["asset_path"],
                    "sha256": asset["sha256"],
                    "status": asset["status"],
                }
                for asset in visual_data["assets"]
            )
            artifacts.extend(
                {
                    "type": "embedded_ocr_markdown",
                    "path": asset["ocr_markdown_path"],
                    "sha256": _file_sha256(
                        (_BASE_ROOT or get_project_root())
                        / asset["ocr_markdown_path"]
                    ),
                    "status": asset["recognition_status"],
                }
                for asset in visual_data["assets"]
                if asset["ocr_markdown_path"]
            )

    audio_stats = None
    if transcript_data is not None:
        transcript_data["source_id"] = source_id
        transcript_data["source_path"] = _project_relative_posix(source)
        for segment in transcript_data["segments"]:
            segment["locator"] = {
                "kind": "audio",
                "start": segment["start"],
                "end": segment["end"],
            }
        target_transcript = _transcript_path(target_md)
        _atomic_write_text(
            target_transcript,
            json.dumps(transcript_data, ensure_ascii=False, indent=2),
        )
        artifacts.append(
            {
                "type": "transcript",
                "path": _project_relative_posix(target_transcript),
                "sha256": _file_sha256(target_transcript),
                "status": transcript_data["status"],
            }
        )
        audio_stats = {
            "status": transcript_data["status"],
            "duration": transcript_data["duration"],
            "duration_after_vad": transcript_data["duration_after_vad"],
            "segments": len(transcript_data["segments"]),
            "language": transcript_data["language"],
            "chunk_seconds": transcript_data.get("chunk_seconds"),
            "chunk_count": transcript_data.get("chunk_count"),
            "processed_duration": transcript_data.get("processed_duration"),
            "processing_coverage": transcript_data.get("processing_coverage"),
            "last_segment_end": transcript_data.get("last_segment_end"),
            "text_normalization": transcript_data.get("text_normalization"),
            "text_normalization_version": transcript_data.get("text_normalization_version"),
            "quality_reviews_applied": len(transcript_data.get("quality_reviews_applied", [])),
        }
        if transcript_data["status"] == "no_speech":
            quality_issues.append("VAD 未检测到语音")
        for issue in transcript_data.get("issues", []):
            message = issue.get("message") if isinstance(issue, dict) else str(issue)
            if message and message not in quality_issues:
                quality_issues.append(message)
        if transcript_data["status"] in {"degraded", "failed"} and not transcript_data.get("issues"):
            quality_issues.append(f"音频转写状态为 {transcript_data['status']}，需人工复核")

    quality = {
        "schema_version": 1,
        "pipeline_version": PIPELINE_VERSION,
        "source_id": source_id,
        "source_path": _project_relative_posix(source),
        "status": "degraded" if quality_issues else "success",
        "character_count": len(text_with_anchors),
        "section_count": sum(_count_sections(s) for s in outline_data["sections"]),
        "paragraph_count": outline_data["doc_paragraphs"],
        "embedded_media": media_stats,
        "audio": audio_stats,
        "issues": quality_issues,
    }
    _atomic_write_text(
        target_quality,
        json.dumps(quality, ensure_ascii=False, indent=2),
    )
    artifacts.append(
        {
            "type": "quality",
            "path": _project_relative_posix(target_quality),
            "sha256": _file_sha256(target_quality),
            "status": quality["status"],
        }
    )
    manifest = {
        "schema_version": 1,
        "pipeline_version": PIPELINE_VERSION,
        "audio_pipeline_version": (
            AUDIO_PIPELINE_VERSION if suffix in AUDIO_EXTENSIONS else None
        ),
        "audio_review_sha256": (
            _audio_review_sha256(source) if suffix in AUDIO_EXTENSIONS else None
        ),
        "source_id": source_id,
        "source_path": _project_relative_posix(source),
        "source_size": stat.st_size,
        "source_mtime_ns": stat.st_mtime_ns,
        "derived_markdown": doc_path,
        "derived_sha256": derived_hash,
        "outline_path": _project_relative_posix(target_outline),
        "converter": converter,
        "converted_at": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "artifacts": artifacts,
    }
    _atomic_write_text(
        target_manifest,
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )

    sec_count = sum(_count_sections(s) for s in outline_data["sections"])
    md_msg = "新增" if md_changed else "未变"
    return True, (
        f"-> {target_md.name} ({md_msg}, {len(text_with_anchors)} 字符, "
        f"{sec_count} 章节, {outline_data['doc_paragraphs']} 段)"
    )


def _count_sections(section: dict) -> int:
    return 1 + sum(_count_sections(c) for c in section.get("children", []))


def parse_extensions(ext_str: str) -> set[str]:
    """解析用户指定的扩展名列表"""
    exts = set()
    for e in ext_str.split(","):
        e = e.strip().lower()
        if e and not e.startswith("."):
            e = "." + e
        if e:
            exts.add(e)
    return exts


def main():
    parser = argparse.ArgumentParser(
        description="将 raw/ 目录中的文档批量转换为 Markdown（基于 markitdown）"
    )
    parser.add_argument(
        "--dir",
        type=str,
        default=None,
        help="显式扫描目录路径（覆盖 --workspace）；默认按 --workspace 取 workspaces/<name>/raw/",
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default=os.environ.get("KB_WORKSPACE", "smb-ecommerce"),
        help=(
            "工作区名称（在 workspaces/ 下查找），默认 smb-ecommerce；"
            "可用环境变量 KB_WORKSPACE 覆盖。--dir 显式给出时本项被忽略"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新转换所有文件（忽略增量检查）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只列出待转换的文件，不执行转换",
    )
    parser.add_argument(
        "--ext",
        type=str,
        default=None,
        help="只处理指定格式，逗号分隔（如 --ext .pdf,.docx）",
    )
    args = parser.parse_args()

    # 确定扫描目录 + doc_path 基准
    global _BASE_ROOT, _SOURCE_ROOT, _DERIVED_ROOT
    # 数据根：默认 = 引擎根；设 KB_ROOT 指向独立项目的数据目录（含 workspaces/），
    # 与 k.py、web/lib/kb.ts 的 KB_ROOT 同义，让一份引擎服务多个独立项目。
    _kb_root_env = os.environ.get("KB_ROOT")
    data_root = Path(_kb_root_env).expanduser().resolve() if _kb_root_env else get_project_root()
    if args.dir:
        # 显式 --dir：若目录位于 raw/ 子树，仍保持 workspace 的 raw → derived
        # 相对映射；任意普通目录则把输出放到其同级 derived/。
        scan_dir = Path(args.dir).resolve()
        _BASE_ROOT = data_root
        raw_root = next(
            (parent for parent in (scan_dir, *scan_dir.parents) if parent.name == "raw"),
            None,
        )
        if raw_root is not None:
            _SOURCE_ROOT = raw_root
            _DERIVED_ROOT = raw_root.parent / "derived"
            _BASE_ROOT = raw_root.parent
        else:
            _SOURCE_ROOT = scan_dir
            _DERIVED_ROOT = scan_dir.parent / "derived"
    else:
        # 解析 workspace（对齐 k.py：workspaces/<name>，挡 ../ 穿越与不存在的名字）
        workspaces_root = (data_root / "workspaces").resolve()
        ws_root = (workspaces_root / args.workspace).resolve()
        valid = [
            d.name for d in sorted(workspaces_root.iterdir())
            if d.is_dir() and not d.name.startswith(".")
        ] if workspaces_root.is_dir() else []
        if not ws_root.is_dir() or ws_root.parent != workspaces_root:
            print(
                f"错误: 非法 --workspace {args.workspace!r}（必须是 workspaces/ 下的目录）。"
                f"有效工作区: {valid}"
            )
            sys.exit(2)
        scan_dir = ws_root / "raw"
        _BASE_ROOT = ws_root
        _SOURCE_ROOT = scan_dir
        _DERIVED_ROOT = ws_root / "derived"

    if not scan_dir.is_dir():
        print(f"错误: 目录不存在: {scan_dir}")
        sys.exit(1)

    # 沙盒：输入和派生输出都必须位于数据根内。
    for path in (scan_dir, _DERIVED_ROOT):
        try:
            path.resolve().relative_to(data_root)
        except ValueError:
            print(f"错误: 输入与输出目录必须在数据根 ({data_root}) 内: {path}")
            sys.exit(1)

    # 解析扩展名过滤
    extensions = parse_extensions(args.ext) if args.ext else None
    if extensions:
        unknown = extensions - SUPPORTED_EXTENSIONS
        if unknown:
            print(f"警告: 以下格式不在已知支持列表中: {', '.join(unknown)}")

    # 收集文件
    files = collect_files(scan_dir, extensions)
    if not files:
        print(f"未找到待转换的文件（目录: {scan_dir}）")
        return

    # 筛选需要转换的文件
    to_convert = []
    skipped_uptodate = 0
    for f in files:
        if should_convert(f, args.force):
            to_convert.append(f)
        else:
            skipped_uptodate += 1

    # Dry run 模式
    if args.dry_run:
        print(f"扫描目录: {scan_dir}")
        print(f"找到 {len(files)} 个支持的文件，其中 {len(to_convert)} 个待转换，{skipped_uptodate} 个已是最新\n")
        if to_convert:
            print("待转换文件:")
            for f in to_convert:
                rel = f.relative_to(scan_dir)
                print(f"  {rel}")
        return

    # 执行转换
    print(f"扫描目录: {scan_dir}")
    print(f"待转换: {len(to_convert)} | 已是最新: {skipped_uptodate}\n")

    if not to_convert:
        print("所有文件均已是最新，无需转换。")
        return

    md = MarkItDown()
    success_count = 0
    fail_count = 0
    empty_count = 0

    for f in to_convert:
        rel = f.relative_to(scan_dir)
        print(f"  转换: {rel} ... ", end="", flush=True)
        try:
            ok, msg = convert_file(md, f)
            if ok:
                print(f"完成 {msg}")
                success_count += 1
            else:
                print(f"跳过 ({msg})")
                empty_count += 1
        except Exception as e:
            print(f"失败 ({e})")
            fail_count += 1

    # 汇总报告
    print(f"\n{'='*40}")
    print(f"转换完成:")
    print(f"  成功: {success_count}")
    if empty_count:
        print(f"  空输出: {empty_count}")
    if fail_count:
        print(f"  失败: {fail_count}")
    if skipped_uptodate:
        print(f"  已是最新: {skipped_uptodate}")

    # 推荐下一步：ingest 流程的章节阅读 + 回填摘要
    if success_count > 0:
        print()
        print("下一步（ingest 流程）:")
        print("  1. 看大纲: python scripts/k.py outline <derived_path>")
        print("  2. 按 anchor 读章节: python scripts/k.py read-section <derived_path> <anchor>")
        print('  3. 读完每个 H2/H3 立即回填摘要:')
        print('     python scripts/k.py annotate-section <derived_path> <anchor> "<一两句概括>"')
        print("     ↑ ②③ 档（分段阅读）的必经步骤；① 档短文不强制（详见 CLAUDE.md Ingest 操作流程 / docs/raw-to-wiki-流程.md §3.6）")


if __name__ == "__main__":
    main()
