"""Deterministically export embedded media from DOCX and PPTX packages."""

from __future__ import annotations

import hashlib
import os
import posixpath
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PRESENTATION_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
VML_NS = "urn:schemas-microsoft-com:vml"

RENDERABLE_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".tif",
    ".tiff",
    ".webp",
}


def _atomic_write_bytes(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.replace(temp_name, target)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _relationships(package: zipfile.ZipFile, part_path: str) -> dict[str, str]:
    directory, name = posixpath.split(part_path)
    rels_path = posixpath.join(directory, "_rels", f"{name}.rels")
    try:
        root = ET.fromstring(package.read(rels_path))
    except KeyError:
        return {}
    return {
        relation.attrib["Id"]: posixpath.normpath(
            posixpath.join(directory, relation.attrib["Target"])
        )
        for relation in root.findall(f"{{{PKG_REL_NS}}}Relationship")
        if relation.attrib.get("Id") and relation.attrib.get("Target")
    }


def _relationship_ids(element: ET.Element) -> list[str]:
    ids = []
    for child in element.iter():
        relation_id = child.attrib.get(f"{{{REL_NS}}}embed")
        if child.tag == f"{{{VML_NS}}}imagedata":
            relation_id = relation_id or child.attrib.get(f"{{{REL_NS}}}id")
        if relation_id:
            ids.append(relation_id)
    return ids


def _docx_occurrences(package: zipfile.ZipFile) -> list[dict]:
    occurrences = []
    parts = [
        name
        for name in package.namelist()
        if name.startswith("word/")
        and name.endswith(".xml")
        and "/_rels/" not in name
    ]
    for part_path in sorted(parts):
        relations = _relationships(package, part_path)
        if not relations:
            continue
        try:
            root = ET.fromstring(package.read(part_path))
        except ET.ParseError:
            continue
        paragraphs = root.findall(f".//{{{WORD_NS}}}p")
        for paragraph_number, paragraph in enumerate(paragraphs, start=1):
            for relation_id in _relationship_ids(paragraph):
                package_path = relations.get(relation_id)
                if package_path and package_path.startswith("word/media/"):
                    occurrences.append(
                        {
                            "package_path": package_path,
                            "locator": {
                                "kind": "docx",
                                "part": part_path,
                                "paragraph": paragraph_number,
                                "relationship_id": relation_id,
                            },
                        }
                    )
    return occurrences


def _slide_number(part_path: str) -> int:
    stem = posixpath.basename(part_path).removeprefix("slide").removesuffix(".xml")
    return int(stem) if stem.isdigit() else 0


def _pptx_occurrences(package: zipfile.ZipFile) -> list[dict]:
    occurrences = []
    slide_parts = sorted(
        (
            name
            for name in package.namelist()
            if name.startswith("ppt/slides/slide")
            and name.endswith(".xml")
            and "/_rels/" not in name
        ),
        key=_slide_number,
    )
    for part_path in slide_parts:
        relations = _relationships(package, part_path)
        try:
            root = ET.fromstring(package.read(part_path))
        except ET.ParseError:
            continue
        shape_tree = root.find(f".//{{{PRESENTATION_NS}}}spTree")
        if shape_tree is None:
            continue
        for shape_number, shape in enumerate(list(shape_tree), start=1):
            properties = shape.find(f".//{{{PRESENTATION_NS}}}cNvPr")
            shape_name = properties.attrib.get("name", "") if properties is not None else ""
            for relation_id in _relationship_ids(shape):
                package_path = relations.get(relation_id)
                if package_path and package_path.startswith("ppt/media/"):
                    occurrences.append(
                        {
                            "package_path": package_path,
                            "locator": {
                                "kind": "pptx",
                                "slide": _slide_number(part_path),
                                "shape": shape_number,
                                "shape_name": shape_name,
                                "relationship_id": relation_id,
                            },
                        }
                    )
    return occurrences


def extract_embedded_media(source: Path, assets_dir: Path) -> dict:
    """Export package media and return physical assets plus source occurrences."""
    prefix = "word/media/" if source.suffix.lower() == ".docx" else "ppt/media/"
    with zipfile.ZipFile(source) as package:
        package_paths = sorted(
            name
            for name in package.namelist()
            if name.startswith(prefix) and not name.endswith("/")
        )
        occurrences = (
            _docx_occurrences(package)
            if source.suffix.lower() == ".docx"
            else _pptx_occurrences(package)
        )
        assets = []
        for package_path in package_paths:
            content = package.read(package_path)
            target = assets_dir / posixpath.basename(package_path)
            _atomic_write_bytes(target, content)
            extension = target.suffix.lower()
            assets.append(
                {
                    "package_path": package_path,
                    "asset_path": target,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "media_type": extension.lstrip(".") or "unknown",
                    "status": (
                        "exported"
                        if extension in RENDERABLE_EXTENSIONS
                        else "unsupported_render"
                    ),
                }
            )

    known = {asset["package_path"] for asset in assets}
    mapped = {item["package_path"] for item in occurrences}
    return {
        "assets": assets,
        "occurrences": occurrences,
        "unmapped_assets": sorted(known - mapped),
        "missing_assets": sorted(mapped - known),
    }
