"""Versioned, evidence-linked project deliverables.

The module deliberately does not call an LLM.  It stores agent-authored drafts,
keeps every version, validates local evidence references, and only writes a
deliverable back to project state after an explicit human confirmation.
"""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from datetime import date
from pathlib import Path

import frontmatter

from context_pack import PROJECT_ID_RE, ProjectDataError


DELIVERABLE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
VERSION_FILE_RE = re.compile(r"^v(\d{3})\.md$")
DELIVERABLE_KINDS = {"research-brief", "project-proposal", "business-one-pager"}
DELIVERABLE_STATUSES = {"draft", "reviewed", "deprecated"}


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def _safe_id(value: str, label: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ProjectDataError(f"非法 {label}（只允许小写字母、数字、-、_，且必须以字母或数字开头）")
    return value


def _project_dir(workspace_root: Path, project_id: str) -> Path:
    _safe_id(project_id, "project_id", PROJECT_ID_RE)
    path = (workspace_root / "projects" / project_id).resolve()
    if path.parent != (workspace_root / "projects").resolve() or not path.is_dir():
        raise ProjectDataError(f"项目不存在: {project_id}")
    return path


def _deliverable_dir(workspace_root: Path, project_id: str, deliverable_id: str) -> Path:
    _project_dir(workspace_root, project_id)
    _safe_id(deliverable_id, "deliverable_id", DELIVERABLE_ID_RE)
    parent = (workspace_root / "exports" / project_id).resolve()
    path = (parent / deliverable_id).resolve()
    if path.parent != parent:
        raise ProjectDataError("deliverable_id 路径越界")
    return path


def _reference_path(reference: str) -> str:
    value = str(reference or "").strip()
    if value.startswith("[[") and value.endswith("]]" ):
        value = value[2:-2].split("|", 1)[0]
    return value.split("#", 1)[0].strip()


def validate_source_refs(workspace_root: Path, source_refs: list[str]) -> list[str]:
    if not source_refs:
        raise ProjectDataError("成果至少需要一个本地 source_ref")
    root = workspace_root.resolve()
    normalized: list[str] = []
    for reference in source_refs:
        value = str(reference or "").strip()
        relative = _reference_path(value)
        if not relative or Path(relative).is_absolute():
            raise ProjectDataError(f"非法 source_ref: {value!r}")
        target = (root / relative).resolve()
        if target != root and root not in target.parents:
            raise ProjectDataError(f"source_ref 路径越界: {value!r}")
        if not target.is_file():
            raise ProjectDataError(f"source_ref 不存在: {value!r}")
        normalized.append(value)
    return list(dict.fromkeys(normalized))


def _context_fingerprint(project_dir: Path) -> str:
    path = project_dir / "context.md"
    if not path.is_file():
        raise ProjectDataError("项目缺少 context.md；请先运行 context-build")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _default_body(title: str, kind: str, source_refs: list[str]) -> str:
    labels = {
        "research-brief": "研究简报",
        "project-proposal": "项目建议书",
        "business-one-pager": "商业材料",
    }
    evidence = "\n".join(f"- `{reference}`" for reference in source_refs)
    return (
        f"# {title}\n\n"
        f"> {labels[kind]}草稿。结论必须能回溯到下列本地证据；未知内容不得补猜。\n\n"
        "## 目标与受众\n\n[待填写]\n\n"
        "## 核心内容\n\n[待填写]\n\n"
        "## 风险、假设与未知\n\n[待填写]\n\n"
        f"## 证据清单\n\n{evidence}\n"
    )


def _version_paths(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("v*.md") if VERSION_FILE_RE.fullmatch(path.name))


def create_deliverable(
    workspace_root: Path,
    project_id: str,
    deliverable_id: str,
    kind: str,
    title: str,
    source_refs: list[str],
    body: str | None = None,
) -> dict:
    if kind not in DELIVERABLE_KINDS:
        raise ProjectDataError(f"非法 deliverable kind: {kind!r}")
    if not str(title or "").strip():
        raise ProjectDataError("成果 title 不能为空")
    project_dir = _project_dir(workspace_root, project_id)
    directory = _deliverable_dir(workspace_root, project_id, deliverable_id)
    sources = validate_source_refs(workspace_root, source_refs)
    context_sha256 = _context_fingerprint(project_dir)
    versions = _version_paths(directory)
    next_version = max((int(VERSION_FILE_RE.fullmatch(path.name).group(1)) for path in versions), default=0) + 1
    if next_version > 999:
        raise ProjectDataError("成果版本已超过 v999")
    path = directory / f"v{next_version:03d}.md"
    today = date.today().isoformat()
    post = frontmatter.Post((body or _default_body(title.strip(), kind, sources)).strip() + "\n")
    post.metadata = {
        "title": title.strip(),
        "type": "deliverable",
        "deliverable_id": deliverable_id,
        "deliverable_kind": kind,
        "project_id": project_id,
        "version": next_version,
        "status": "draft",
        "created_at": today,
        "last_modified_by": "LLM",
        "context_sha256": context_sha256,
        "source_refs": sources,
    }
    _atomic_write(path, frontmatter.dumps(post))
    return {
        "project_id": project_id,
        "deliverable_id": deliverable_id,
        "kind": kind,
        "version": next_version,
        "status": "draft",
        "path": _relative(path, workspace_root),
        "source_refs": sources,
        "written": True,
    }


def _record(path: Path, workspace_root: Path) -> dict:
    try:
        post = frontmatter.load(path)
    except Exception as exc:
        raise ProjectDataError(f"成果无法解析: {_relative(path, workspace_root)} ({exc})") from exc
    fm = post.metadata
    errors: list[str] = []
    for field in (
        "title", "type", "deliverable_id", "deliverable_kind", "project_id",
        "version", "status", "created_at", "last_modified_by", "context_sha256", "source_refs",
    ):
        if field not in fm:
            errors.append(f"缺少字段: {field}")
    if fm.get("type") != "deliverable":
        errors.append("type 必须是 deliverable")
    if fm.get("deliverable_kind") not in DELIVERABLE_KINDS:
        errors.append(f"非法 deliverable_kind: {fm.get('deliverable_kind')!r}")
    if fm.get("status") not in DELIVERABLE_STATUSES:
        errors.append(f"非法 status: {fm.get('status')!r}")
    if fm.get("project_id") != path.parent.parent.name:
        errors.append("project_id 与路径不一致")
    if fm.get("deliverable_id") != path.parent.name:
        errors.append("deliverable_id 与路径不一致")
    match = VERSION_FILE_RE.fullmatch(path.name)
    if not match or fm.get("version") != int(match.group(1)):
        errors.append("version 与文件名不一致")
    refs = fm.get("source_refs")
    if not isinstance(refs, list) or not refs:
        errors.append("source_refs 必须是非空数组")
    else:
        try:
            validate_source_refs(workspace_root, [str(item) for item in refs])
        except ProjectDataError as exc:
            errors.append(str(exc))
    context_path = workspace_root / "projects" / str(fm.get("project_id") or "") / "context.md"
    context_current = (
        context_path.is_file()
        and fm.get("context_sha256") == hashlib.sha256(context_path.read_bytes()).hexdigest()
    )
    return {
        "path": _relative(path, workspace_root),
        "title": str(fm.get("title") or path.stem),
        "deliverable_id": str(fm.get("deliverable_id") or ""),
        "kind": str(fm.get("deliverable_kind") or ""),
        "project_id": str(fm.get("project_id") or ""),
        "version": fm.get("version"),
        "status": str(fm.get("status") or ""),
        "reviewed": fm.get("status") == "reviewed" and fm.get("last_modified_by") == "Human",
        "context_current": context_current,
        "source_refs": refs if isinstance(refs, list) else [],
        "content": post.content,
        "errors": errors,
        "valid": not errors,
    }


def list_deliverables(workspace_root: Path, project_id: str | None = None) -> list[dict]:
    exports_root = workspace_root / "exports"
    if not exports_root.is_dir():
        return []
    if project_id is not None:
        _project_dir(workspace_root, project_id)
        project_dirs = [exports_root / project_id]
    else:
        project_dirs = sorted(path for path in exports_root.iterdir() if path.is_dir())
    records: list[dict] = []
    for project_dir in project_dirs:
        if not project_dir.is_dir():
            continue
        for directory in sorted(path for path in project_dir.iterdir() if path.is_dir()):
            records.extend(_record(path, workspace_root) for path in _version_paths(directory))
    return records


def confirm_deliverable(
    workspace_root: Path,
    project_id: str,
    deliverable_id: str,
    version: int,
    note: str = "",
) -> dict:
    directory = _deliverable_dir(workspace_root, project_id, deliverable_id)
    if not isinstance(version, int) or not 1 <= version <= 999:
        raise ProjectDataError("version 必须在 1 到 999 之间")
    path = directory / f"v{version:03d}.md"
    if not path.is_file():
        raise ProjectDataError(f"成果版本不存在: {project_id}/{deliverable_id}/v{version:03d}")
    record = _record(path, workspace_root)
    if record["errors"]:
        raise ProjectDataError("；".join(record["errors"]))
    if record["project_id"] != project_id or record["deliverable_id"] != deliverable_id:
        raise ProjectDataError("成果元数据与路径不一致")
    validate_source_refs(workspace_root, record["source_refs"])

    today = date.today().isoformat()
    post = frontmatter.load(path)
    post.metadata["status"] = "reviewed"
    post.metadata["last_modified_by"] = "Human"
    post.metadata["reviewed_at"] = today
    if note.strip():
        post.metadata["review_note"] = note.strip()
    _atomic_write(path, frontmatter.dumps(post))

    state_path = workspace_root / "projects" / project_id / "state.md"
    state = frontmatter.load(state_path)
    relative = _relative(path, workspace_root)
    refs = state.metadata.get("deliverable_refs")
    refs = [str(item) for item in refs] if isinstance(refs, list) else []
    if relative not in refs:
        refs.append(relative)
    state.metadata["deliverable_refs"] = refs
    state.metadata["updated_at"] = today
    state.metadata["last_modified_by"] = "Human"
    state.metadata["last_confirmed_at"] = today
    _atomic_write(state_path, frontmatter.dumps(state))

    return {
        "project_id": project_id,
        "deliverable_id": deliverable_id,
        "version": version,
        "status": "reviewed",
        "path": relative,
        "state_path": _relative(state_path, workspace_root),
        "written": True,
    }
