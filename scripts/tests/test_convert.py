"""convert.py 的 OCR、OOXML 媒体与音频安全回归测试。"""

import json
import sys
import zipfile
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

pytest.importorskip("markitdown")

from scripts import convert as converter
from scripts import ocr_rapid


class EmptyConverter:
    def convert(self, _source):
        return SimpleNamespace(markdown="")


class StaticConverter:
    def __init__(self, markdown="# Converted\n"):
        self.markdown = markdown
        self.called = False

    def convert(self, _source):
        self.called = True
        return SimpleNamespace(markdown=self.markdown)


def _write_package(path, files):
    with zipfile.ZipFile(path, "w") as package:
        for name, content in files.items():
            package.writestr(name, content)


def _fake_ocr(paths):
    return {
        path: (
            True,
            {
                "status": "ocr_success",
                "recognition_status": "ocr_success",
                "engine": "rapidocr",
                "engine_version": "test",
                "text": "detected text",
                "blocks": [
                    {
                        "text": "detected text",
                        "bbox": [[1, 2], [3, 2], [3, 4], [1, 4]],
                        "confidence": 0.99,
                    }
                ],
                "average_confidence": 0.99,
                "low_confidence_blocks": 0,
                "review_threshold": 0.8,
                "needs_review": False,
            },
        )
        for path in paths
    }


def test_rapidocr_none_result_is_no_text_not_failure():
    result = SimpleNamespace(to_json=lambda: None)

    payload = ocr_rapid._payload(result, "blank.png")

    assert payload["status"] == "no_text"
    assert payload["blocks"] == []


@pytest.fixture(autouse=True)
def derived_layout(tmp_path, monkeypatch):
    monkeypatch.setattr(converter, "_BASE_ROOT", tmp_path)
    monkeypatch.setattr(converter, "_SOURCE_ROOT", tmp_path)
    monkeypatch.setattr(converter, "_DERIVED_ROOT", tmp_path / "derived")


def test_image_uses_external_ocr_command(tmp_path, monkeypatch):
    source = tmp_path / "figure.png"
    source.write_bytes(b"not-a-real-image")
    monkeypatch.setenv(
        "KB_OCR_COMMAND",
        f'"{sys.executable}" -c "print(\\\"OCR result\\\")" {{input}}',
    )
    ok, message = converter.convert_file(EmptyConverter(), source)

    assert ok is True
    assert "figure.md" in message
    output = tmp_path / "derived" / "figure.md"
    manifest = tmp_path / "derived" / "figure.source.json"
    assert "OCR result" in output.read_text(encoding="utf-8")
    assert (tmp_path / "derived" / "figure.outline.json").exists()
    assert json.loads(manifest.read_text(encoding="utf-8"))["source_path"] == "figure.png"
    assert source.read_bytes() == b"not-a-real-image"


def test_main_writes_conversion_run_report(tmp_path, monkeypatch):
    workspace = tmp_path / "workspaces" / "main"
    raw = workspace / "raw"
    raw.mkdir(parents=True)
    (raw / "note.md").write_text("# Note\n\nMeasured content.\n", encoding="utf-8")
    report = workspace / "projects" / "acceptance" / "convert-run.json"
    monkeypatch.setenv("KB_ROOT", str(tmp_path))
    monkeypatch.setattr(
        sys,
        "argv",
        ["convert.py", "--workspace", "main", "--report", str(report)],
    )

    converter.main()

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["kind"] == "conversion"
    assert payload["totals"]["attempted"] == 1
    assert payload["totals"]["converted"] == 1
    assert payload["totals"]["quality_success"] == 1
    assert payload["files"][0]["path"] == "note.md"
    assert payload["files"][0]["duration_ms"] >= 0
    assert payload["cloud_llm_calls"] == 0


def test_image_without_ocr_backend_fails_explicitly(tmp_path, monkeypatch):
    source = tmp_path / "figure.png"
    source.write_bytes(b"not-a-real-image")
    monkeypatch.delenv("KB_OCR_COMMAND", raising=False)
    monkeypatch.setenv("KB_OCR_ENGINE", "rapidocr")
    monkeypatch.setattr(
        converter,
        "_default_ocr_command",
        lambda _engine: (None, "RapidOCR 未安装"),
    )

    ok, message = converter.convert_file(EmptyConverter(), source)

    assert ok is False
    assert "RapidOCR 未安装" in message


def test_builtin_engine_can_be_overridden_by_command(tmp_path, monkeypatch):
    source = tmp_path / "figure.png"
    source.write_bytes(b"not-a-real-image")
    monkeypatch.setenv("KB_OCR_ENGINE", "tesseract")
    monkeypatch.setenv(
        "KB_OCR_COMMAND",
        f'"{sys.executable}" -c "print(\\"custom OCR\\")" {{input}}',
    )

    ok, _ = converter.convert_file(EmptyConverter(), source)

    assert ok is True
    output = (tmp_path / "derived" / "figure.md").read_text(encoding="utf-8")
    assert "custom OCR" in output
    assert "OCR_ENGINE: custom-command" in output


def test_ocr_fallback_command_is_used_after_primary_failure(tmp_path, monkeypatch):
    source = tmp_path / "figure.png"
    source.write_bytes(b"not-a-real-image")
    monkeypatch.setenv(
        "KB_OCR_COMMAND",
        f'"{sys.executable}" -c "import sys; sys.exit(1)" {{input}}',
    )
    monkeypatch.setenv(
        "KB_OCR_FALLBACK_COMMAND",
        f'"{sys.executable}" -c "print(\\"fallback OCR\\")" {{input}}',
    )

    ok, _ = converter.convert_file(EmptyConverter(), source)

    assert ok is True
    assert "fallback OCR" in (tmp_path / "derived" / "figure.md").read_text(encoding="utf-8")


def test_markdown_source_is_copied_to_derived_and_incremental(tmp_path):
    source = tmp_path / "notes" / "source.md"
    source.parent.mkdir()
    source.write_text("# Source\n\nOriginal fact.\n", encoding="utf-8")
    converter._SOURCE_ROOT = tmp_path

    ok, _ = converter.convert_file(EmptyConverter(), source)

    assert ok is True
    assert source.read_text(encoding="utf-8") == "# Source\n\nOriginal fact.\n"
    assert (tmp_path / "derived" / "notes" / "source.md").exists()
    assert converter.should_convert(source, force=False) is False

    source.write_text("# Source\n\nChanged fact.\n", encoding="utf-8")
    assert converter.should_convert(source, force=False) is True


def test_audio_review_change_invalidates_incremental_conversion(tmp_path, monkeypatch):
    source = tmp_path / "raw" / "test" / "meeting.mp3"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"audio")
    monkeypatch.setattr(converter, "_SOURCE_ROOT", tmp_path / "raw")
    monkeypatch.setattr(converter, "_DERIVED_ROOT", tmp_path / "derived")
    monkeypatch.setattr(
        converter,
        "_transcribe_audio",
        lambda _source: (
            True,
            {
                "status": "success",
                "duration": 1.0,
                "duration_after_vad": None,
                "language": "zh",
                "segments": [],
                "issues": [],
            },
        ),
    )

    ok, _ = converter.convert_file(StaticConverter(), source)
    assert ok is True
    assert converter.should_convert(source, force=False) is False

    review = tmp_path / "wiki" / "source-reviews.json"
    review.parent.mkdir(parents=True)
    review.write_text('{"schema_version":1,"sources":{}}', encoding="utf-8")

    assert converter.should_convert(source, force=False) is True


def test_target_paths_preserve_subdirectories_below_raw(tmp_path, monkeypatch):
    source = tmp_path / "raw" / "papers" / "paper.pdf"
    monkeypatch.setattr(converter, "_SOURCE_ROOT", tmp_path / "raw")
    monkeypatch.setattr(converter, "_DERIVED_ROOT", tmp_path / "derived")

    markdown, outline, manifest = converter._target_paths(source)

    assert markdown == tmp_path / "derived" / "papers" / "paper.md"
    assert outline == tmp_path / "derived" / "papers" / "paper.outline.json"
    assert manifest == tmp_path / "derived" / "papers" / "paper.source.json"


def test_markdown_and_binary_twins_never_share_a_manifest(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    markdown = raw / "paper.md"
    pdf = raw / "paper.pdf"
    markdown.write_text("source mirror", encoding="utf-8")
    pdf.write_bytes(b"pdf")
    monkeypatch.setattr(converter, "_SOURCE_ROOT", raw)
    monkeypatch.setattr(converter, "_DERIVED_ROOT", tmp_path / "derived")

    markdown_paths = converter._target_paths(markdown)
    pdf_paths = converter._target_paths(pdf)

    assert markdown_paths[0] == tmp_path / "derived" / "paper.raw.md"
    assert markdown_paths[2] == tmp_path / "derived" / "paper.raw.source.json"
    assert pdf_paths[0] == tmp_path / "derived" / "paper.md"
    assert pdf_paths[2] == tmp_path / "derived" / "paper.source.json"
    assert set(markdown_paths).isdisjoint(pdf_paths)


def test_xlsx_writes_formula_value_evidence_and_removes_nan(tmp_path):
    source = tmp_path / "orders.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "Orders"
    sheet.append(["id", "amount", "total"])
    sheet.append(["ORD-004", None, "=B2*2"])
    book.save(source)

    ok, _ = converter.convert_file(
        StaticConverter(
            "## Orders\n| id | amount | total |\n| --- | --- | --- |\n"
            "| ORD-004 | NaN | NaN |\n"
        ),
        source,
    )

    assert ok is True
    markdown = (tmp_path / "derived" / "orders.md").read_text(encoding="utf-8")
    assert "NaN" not in markdown
    assert "=B2*2" in markdown
    evidence = json.loads(
        (tmp_path / "derived" / "orders.evidence.json").read_text(encoding="utf-8")
    )
    assert evidence["sheets"][0]["rows"][1]["values"][1] is None
    assert evidence["sheets"][0]["formula_cells"][0]["formula"] == "=B2*2"
    manifest = json.loads(
        (tmp_path / "derived" / "orders.source.json").read_text(encoding="utf-8")
    )
    assert any(artifact["type"] == "evidence" for artifact in manifest["artifacts"])


def test_docx_exports_media_and_records_paragraph_locator(tmp_path, monkeypatch):
    source = tmp_path / "sample.docx"
    original = b"png-content"
    _write_package(
        source,
        {
            "word/media/image1.png": original,
            "word/media/image2.emf": b"emf-content",
            "word/document.xml": """<w:document
                xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <w:body>
                <w:p><w:r><a:blip r:embed="rId1"/></w:r></w:p>
                <w:p><w:r><a:blip r:embed="rId2"/></w:r></w:p>
              </w:body>
            </w:document>""",
            "word/_rels/document.xml.rels": """<Relationships
                xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId1" Target="media/image1.png"/>
              <Relationship Id="rId2" Target="media/image2.emf"/>
            </Relationships>""",
        },
    )
    before = source.read_bytes()
    backend = StaticConverter("# Converted\n\n![broken](data:image/png;base64,AAA)\n")
    monkeypatch.setattr(converter, "ocr_images", _fake_ocr)

    ok, _ = converter.convert_file(backend, source)

    assert ok is True
    assert source.read_bytes() == before
    assets = tmp_path / "derived" / "sample.assets"
    assert (assets / "image1.png").read_bytes() == original
    assert (assets / "image2.emf").read_bytes() == b"emf-content"
    markdown = (tmp_path / "derived" / "sample.md").read_text(encoding="utf-8")
    assert "data:image" not in markdown
    assert "sample.assets/image1.png" in markdown
    assert "当前不支持直接渲染" in markdown
    visual = json.loads(
        (tmp_path / "derived" / "sample.visual.json").read_text(encoding="utf-8")
    )
    assert visual["occurrence_count"] == 2
    assert visual["assets"][0]["locators"][0]["paragraph"] == 1
    assert visual["assets"][0]["ocr"]["blocks"][0]["confidence"] == 0.99
    assert (assets / "image1.png.ocr.md").exists()
    assert visual["assets"][1]["status"] == "unsupported_render"
    quality = json.loads(
        (tmp_path / "derived" / "sample.quality.json").read_text(encoding="utf-8")
    )
    assert quality["embedded_media"]["discovered_assets"] == 2
    assert quality["embedded_media"]["unsupported_render_assets"] == 1
    manifest = json.loads(
        (tmp_path / "derived" / "sample.source.json").read_text(encoding="utf-8")
    )
    assert {artifact["type"] for artifact in manifest["artifacts"]} >= {
        "markdown",
        "outline",
        "visual",
        "quality",
        "embedded_media",
        "embedded_ocr_markdown",
    }
    assert converter.should_convert(source, force=False) is False


def test_pptx_exports_media_and_records_slide_shape_locator(tmp_path, monkeypatch):
    source = tmp_path / "slides.pptx"
    _write_package(
        source,
        {
            "ppt/media/image1.jpeg": b"jpeg-content",
            "ppt/slides/slide2.xml": """<p:sld
                xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <p:cSld><p:spTree><p:pic><p:nvPicPr><p:cNvPr id="7" name="Chart"/></p:nvPicPr>
              <p:blipFill><a:blip r:embed="rId5"/></p:blipFill></p:pic></p:spTree></p:cSld>
            </p:sld>""",
            "ppt/slides/_rels/slide2.xml.rels": """<Relationships
                xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId5" Target="../media/image1.jpeg"/>
            </Relationships>""",
        },
    )
    monkeypatch.setattr(converter, "ocr_images", _fake_ocr)

    ok, _ = converter.convert_file(
        StaticConverter("# Slides\n\n![dangling](Picture.jpg)\n"), source
    )

    assert ok is True
    assert (tmp_path / "derived" / "slides.assets" / "image1.jpeg").exists()
    markdown = (tmp_path / "derived" / "slides.md").read_text(encoding="utf-8")
    assert "Picture.jpg" not in markdown
    assert "slides.assets/image1.jpeg" in markdown
    visual = json.loads(
        (tmp_path / "derived" / "slides.visual.json").read_text(encoding="utf-8")
    )
    locator = visual["assets"][0]["locators"][0]
    assert locator["slide"] == 2
    assert locator["shape_name"] == "Chart"
    assert locator["relationship_id"] == "rId5"


@pytest.mark.parametrize("extension", [".mp3", ".wav", ".m4a"])
def test_audio_uses_local_transcriber_and_writes_timestamps(
    extension, tmp_path, monkeypatch
):
    source = tmp_path / f"narration{extension}"
    source.write_bytes(b"audio")
    backend = StaticConverter()
    monkeypatch.setattr(
        converter,
        "_transcribe_audio",
        lambda _source: (
            True,
            {
                "schema_version": 1,
                "status": "success",
                "engine": "faster-whisper",
                "engine_version": "1.2.1",
                "model": "small",
                "device": "cpu",
                "compute_type": "int8",
                "vad_filter": True,
                "word_timestamps": True,
                "language": "zh",
                "language_probability": 0.99,
                "duration": 2.0,
                "duration_after_vad": 1.5,
                "chunk_seconds": 600,
                "chunk_count": 1,
                "processed_duration": 2.0,
                "processing_coverage": 1.0,
                "last_segment_end": 1.75,
                "issues": [],
                "text": "测试口播",
                "segments": [
                    {
                        "id": 0,
                        "start": 0.25,
                        "end": 1.75,
                        "text": "测试口播",
                        "avg_logprob": -0.1,
                        "no_speech_prob": 0.01,
                        "words": [],
                    }
                ],
            },
        ),
    )

    ok, message = converter.convert_file(backend, source)

    assert ok is True
    assert backend.called is False
    assert "narration.md" in message
    transcript = json.loads(
        (tmp_path / "derived" / "narration.transcript.json").read_text(
            encoding="utf-8"
        )
    )
    assert transcript["segments"][0]["locator"] == {
        "kind": "audio",
        "start": 0.25,
        "end": 1.75,
    }
    markdown = (tmp_path / "derived" / "narration.md").read_text(encoding="utf-8")
    assert "00:00:00.250–00:00:01.750" in markdown
    assert converter.should_convert(source, force=False) is False


def test_audio_quality_gate_is_propagated_to_conversion_artifacts(tmp_path, monkeypatch):
    source = tmp_path / "degraded.mp3"
    source.write_bytes(b"audio")
    monkeypatch.setattr(
        converter,
        "_transcribe_audio",
        lambda _source: (
            True,
            {
                "schema_version": 2,
                "status": "degraded",
                "engine": "faster-whisper",
                "engine_version": "1.2.1",
                "model": "small",
                "device": "cpu",
                "compute_type": "int8",
                "vad_filter": True,
                "word_timestamps": True,
                "condition_on_previous_text": False,
                "language": "zh",
                "language_probability": 0.99,
                "duration": 1200.0,
                "duration_after_vad": None,
                "chunk_seconds": 600,
                "chunk_count": 2,
                "chunks": [
                    {"id": 0, "start": 0.0, "end": 600.0, "status": "success", "segment_count": 1},
                    {"id": 1, "start": 600.0, "end": 1200.0, "status": "failed", "segment_count": 0},
                ],
                "processed_duration": 600.0,
                "processing_coverage": 0.5,
                "last_segment_end": 1.75,
                "issues": [
                    {"code": "failed_chunks", "message": "1 个音频分块转写失败"}
                ],
                "text": "部分转写",
                "segments": [
                    {
                        "id": 0,
                        "chunk_id": 0,
                        "start": 0.25,
                        "end": 1.75,
                        "text": "部分转写",
                        "avg_logprob": -0.1,
                        "no_speech_prob": 0.01,
                        "words": [],
                    }
                ],
            },
        ),
    )

    ok, _ = converter.convert_file(StaticConverter(), source)

    assert ok is True
    quality = json.loads(
        (tmp_path / "derived" / "degraded.quality.json").read_text(encoding="utf-8")
    )
    assert quality["status"] == "degraded"
    assert quality["audio"]["processing_coverage"] == 0.5
    assert "1 个音频分块转写失败" in quality["issues"]
    manifest = json.loads(
        (tmp_path / "derived" / "degraded.source.json").read_text(encoding="utf-8")
    )
    transcript = next(
        artifact for artifact in manifest["artifacts"] if artifact["type"] == "transcript"
    )
    assert transcript["status"] == "degraded"


def test_audio_failure_is_explicit_and_never_calls_markitdown(tmp_path, monkeypatch):
    source = tmp_path / "broken.mp3"
    source.write_bytes(b"broken")
    backend = StaticConverter()
    monkeypatch.setattr(
        converter,
        "_transcribe_audio",
        lambda _source: (False, "faster-whisper 转写失败: invalid data"),
    )

    ok, message = converter.convert_file(backend, source)

    assert ok is False
    assert backend.called is False
    assert "invalid data" in message
