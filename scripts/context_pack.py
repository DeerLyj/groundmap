"""Project state, decision records, and portable context packs.

Project files live outside wiki/ so project state is not mistaken for durable
knowledge. The module is deliberately filesystem-based and deterministic.
"""
from __future__ import annotations

import os
import re
import tempfile
from datetime import date, datetime
from pathlib import Path

import frontmatter


PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")

STATE_REQUIRED_FIELDS = (
    "project_id",
    "status",
    "updated_at",
    "owner",
    "current_outcome",
    "next_action",
    "blocked_by",
    "decision_refs",
    "knowledge_refs",
)
STATE_STATUSES = {"active", "paused", "blocked", "completed", "archived"}
DECISION_STATUSES = {"open", "pending_validation", "executed", "reviewed", "deprecated"}
CONFIRMABLE_DECISION_STATUSES = {"executed", "reviewed"}
DECISION_REQUIRED_FIELDS = ("decision_id", "project_id", "decision_status", "decision_date")


class ProjectDataError(ValueError):
    """A project file is missing, malformed, or inconsistent."""


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(value)]


def _iso(value) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value or "")


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_doc(path: Path, root: Path, label: str) -> dict:
    try:
        post = frontmatter.load(path)
    except Exception as exc:
        raise ProjectDataError(f"{label} 无法解析: {_relative(path, root)} ({exc})") from exc
    return {
        "path": _relative(path, root),
        "frontmatter": post.metadata,
        "content": post.content.strip(),
        "sections": _sections(post.content),
    }


def _sections(content: str) -> dict[str, str]:
    matches = list(HEADING_RE.finditer(content))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        title = match.group(1).strip()
        body = content[match.end():end].strip()
        sections[title] = body
    return sections


def _validate_state(doc: dict, project_id: str) -> list[str]:
    fm = doc["frontmatter"]
    errors = [f"state.md 缺少必填字段: {field}" for field in STATE_REQUIRED_FIELDS if field not in fm]
    if fm.get("project_id") != project_id:
        errors.append(f"project_id 与目录不一致: {fm.get('project_id')!r} != {project_id!r}")
    if fm.get("status") not in STATE_STATUSES:
        errors.append(f"非法项目 status: {fm.get('status')!r}")
    if not _iso(fm.get("updated_at")):
        errors.append("updated_at 不能为空")
    return errors


def _validate_decision(doc: dict, project_id: str) -> list[str]:
    fm = doc["frontmatter"]
    errors = [f"决策记录缺少必填字段: {field}" for field in DECISION_REQUIRED_FIELDS if field not in fm]
    if fm.get("project_id") != project_id:
        errors.append(f"决策 project_id 与项目不一致: {fm.get('project_id')!r} != {project_id!r}")
    if fm.get("decision_status") not in DECISION_STATUSES:
        errors.append(f"非法 decision_status: {fm.get('decision_status')!r}")
    return errors


def _project_dir(projects_root: Path, project_id: str) -> Path:
    if not isinstance(project_id, str) or not PROJECT_ID_RE.fullmatch(project_id):
        raise ProjectDataError("非法 project_id（只允许小写字母、数字、-、_，且必须以字母或数字开头）")
    path = (projects_root / project_id).resolve()
    if path.parent != projects_root.resolve():
        raise ProjectDataError("project_id 路径越界")
    return path


def _decision_paths(project_dir: Path) -> list[Path]:
    paths: list[Path] = []
    single = project_dir / "decisions.md"
    if single.is_file():
        paths.append(single)
    directory = project_dir / "decisions"
    if directory.is_dir():
        paths.extend(sorted(p for p in directory.glob("*.md") if p.is_file()))
    return paths


def _decision_record(path: Path, root: Path, project_id: str) -> dict:
    doc = _read_doc(path, root, "决策记录")
    errors = _validate_decision(doc, project_id)
    fm = doc["frontmatter"]
    return {
        "path": doc["path"],
        "title": str(fm.get("title") or fm.get("decision_id") or path.stem),
        "decision_id": str(fm.get("decision_id") or ""),
        "project_id": str(fm.get("project_id") or ""),
        "decision_status": str(fm.get("decision_status") or ""),
        "decision_date": _iso(fm.get("decision_date")),
        "review_date": _iso(fm.get("review_date")),
        "frontmatter": fm,
        "content": doc["content"],
        "sections": doc["sections"],
        "errors": errors,
    }


def list_projects(projects_root: Path, status: str | None = None) -> list[dict]:
    if not projects_root.is_dir():
        return []
    out: list[dict] = []
    for directory in sorted(p for p in projects_root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        state_path = directory / "state.md"
        item = {
            "project_id": directory.name,
            "path": directory.relative_to(projects_root.parent).as_posix(),
            "state_path": state_path.relative_to(projects_root.parent).as_posix(),
            "brief_path": (directory / "brief.md").relative_to(projects_root.parent).as_posix(),
            "context_path": (directory / "context.md").relative_to(projects_root.parent).as_posix(),
            "status": "",
            "updated_at": "",
            "current_outcome": "",
            "next_action": "",
            "decision_count": len(_decision_paths(directory)),
            "state_confirmed": False,
            "valid": False,
            "errors": [],
        }
        if not state_path.is_file():
            item["errors"] = ["缺少 projects/<project_id>/state.md"]
        else:
            try:
                state = _read_doc(state_path, projects_root.parent, "state.md")
                errors = _validate_state(state, directory.name)
                fm = state["frontmatter"]
                item.update(
                    status=str(fm.get("status") or ""),
                    updated_at=_iso(fm.get("updated_at")),
                    current_outcome=str(fm.get("current_outcome") or ""),
                    next_action=str(fm.get("next_action") or ""),
                    state_confirmed=fm.get("last_modified_by") == "Human",
                    valid=not errors,
                    errors=errors,
                )
            except ProjectDataError as exc:
                item["errors"] = [str(exc)]
        if status is None or item["status"] == status:
            out.append(item)
    return out


def load_project(projects_root: Path, project_id: str, decision_status: str | None = None,
                 date_from: str | None = None, date_to: str | None = None) -> dict:
    directory = _project_dir(projects_root, project_id)
    if not directory.is_dir():
        raise ProjectDataError(f"项目不存在: {project_id}")
    state_path = directory / "state.md"
    if not state_path.is_file():
        raise ProjectDataError(f"项目缺少 state.md: projects/{project_id}/state.md")
    state = _read_doc(state_path, projects_root.parent, "state.md")
    state_errors = _validate_state(state, project_id)
    if state_errors:
        raise ProjectDataError("；".join(state_errors))

    decisions = []
    for path in _decision_paths(directory):
        decision = _decision_record(path, projects_root.parent, project_id)
        if decision["errors"]:
            raise ProjectDataError("；".join(decision["errors"]))
        decision_date = decision["decision_date"]
        if decision_status and decision["decision_status"] != decision_status:
            continue
        if date_from and decision_date < date_from:
            continue
        if date_to and decision_date > date_to:
            continue
        decisions.append(decision)

    brief_path = directory / "brief.md"
    brief = _read_doc(brief_path, projects_root.parent, "brief.md") if brief_path.is_file() else None
    return {
        "project": {
            "project_id": project_id,
            "path": directory.relative_to(projects_root.parent).as_posix(),
            "state_path": state["path"],
            "brief_path": brief["path"] if brief else None,
            "context_path": (directory / "context.md").relative_to(projects_root.parent).as_posix(),
        },
        "brief": brief,
        "state": {
            "path": state["path"],
            "frontmatter": state["frontmatter"],
            "content": state["content"],
            "sections": state["sections"],
            "confirmed": state["frontmatter"].get("last_modified_by") == "Human",
        },
        "decisions": decisions,
    }


def _links(*docs: dict | None) -> list[str]:
    found: set[str] = set()
    for doc in docs:
        if not doc:
            continue
        for value in doc["frontmatter"].values():
            for link in _as_list(value):
                match = WIKILINK_RE.search(link)
                if match:
                    found.add(match.group(1).strip())
        found.update(match.group(1).strip() for match in WIKILINK_RE.finditer(doc["content"]))
    return sorted(found)


def _section(doc: dict | None, *names: str) -> str:
    if not doc:
        return ""
    for name in names:
        if doc["sections"].get(name):
            return doc["sections"][name]
    return ""


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:max(0, limit - 24)].rstrip() + "\n\n[内容因预算被裁剪]"


def build_context_pack(project: dict, max_chars: int = 30000) -> str:
    if max_chars < 1000:
        raise ProjectDataError("max_chars 至少为 1000")
    state = project["state"]
    brief = project["brief"]
    fm = state["frontmatter"]
    title = str((brief or {}).get("frontmatter", {}).get("title") or project["project"]["project_id"])

    blocks = [
        f"# Context Pack: {title}\n\n"
        f"- project_id: `{project['project']['project_id']}`\n"
        f"- state source: `{state['path']}`\n"
        f"- this file is generated; edit state.md / brief.md / decisions instead.\n",
        "## 项目目标与范围\n\n" + _clip(brief["content"] if brief else str(fm.get("current_outcome") or "未提供项目 brief。"), 7000),
        "## 当前状态\n\n"
        f"- 状态：{fm.get('status', '未知')}\n"
        f"- 状态确认：{'已由 Human 确认' if fm.get('last_modified_by') == 'Human' else '待 Human 确认'}\n"
        f"- 更新时间：{_iso(fm.get('updated_at'))}\n"
        f"- 负责人：{fm.get('owner', '未注明')}\n"
        f"- 当前结果：{fm.get('current_outcome', '未注明')}\n"
        f"- 下一行动：{fm.get('next_action', '未注明')}\n"
        f"- 阻塞：{', '.join(_as_list(fm.get('blocked_by'))) or '未记录'}\n\n"
        + _clip(state["content"], 7000),
    ]

    confirmed = [
        d for d in project["decisions"]
        if d["decision_status"] in {"reviewed", "executed"}
        and d["frontmatter"].get("last_modified_by") == "Human"
    ]
    open_decisions = [
        d for d in project["decisions"]
        if d["decision_status"] != "deprecated" and d not in confirmed
    ]
    decision_lines = []
    for heading, records in (("已确认/已执行决策", confirmed), ("未决策或待验证", open_decisions)):
        if records:
            decision_lines.append(f"### {heading}\n")
            for decision in records:
                decision_lines.append(
                    f"#### {decision['title']}（{decision['decision_status']}）\n"
                    f"来源文件：`{decision['path']}`\n\n{_clip(decision['content'], 5000)}\n"
                )
    blocks.append("## 决策记录\n\n" + ("\n".join(decision_lines).strip() or "暂无决策记录。"))

    links = _links(brief, state, *project["decisions"])
    refs = []
    for value in _as_list(fm.get("knowledge_refs")) + _as_list(fm.get("decision_refs")):
        match = WIKILINK_RE.search(value)
        refs.append(match.group(1).strip() if match else value.strip())
    knowledge = sorted(set(refs + links))
    blocks.append("## 证据与知识入口\n\n" + ("\n".join(f"- {item}" for item in knowledge) or "未提供本地知识入口；不得自行推断来源。"))

    assumptions = []
    for decision in project["decisions"]:
        text = _section(decision, "关键假设", "什么证据会让我改变判断", "判断依据")
        if text:
            assumptions.append(f"### {decision['title']}\n\n{_clip(text, 3500)}")
    risks = _section(state, "当前阻塞", "风险", "待用户决策", "未知信息")
    blocks.append(
        "## 风险、假设与未知\n\n"
        + ("\n\n".join(assumptions) if assumptions else "暂无已登记的决策假设。")
        + (f"\n\n### 状态页登记\n\n{_clip(risks, 4500)}" if risks else "\n\n状态页未登记风险或未知信息；不得补猜。")
        + "\n\n- 未经用户确认的事实、记忆和决策不得视为已生效。"
    )

    output = "\n\n".join(blocks).strip() + "\n"
    return _clip(output, max_chars)


def write_context(path: Path, content: str) -> None:
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


def build_and_write(projects_root: Path, project_id: str, max_chars: int = 30000,
                    write: bool = True) -> dict:
    project = load_project(projects_root, project_id)
    content = build_context_pack(project, max_chars)
    path = projects_root / project_id / "context.md"
    if write:
        write_context(path, content)
    return {
        "project_id": project_id,
        "context_path": path.relative_to(projects_root.parent).as_posix(),
        "context": content,
        "written": write,
    }


def confirm_project_record(
    projects_root: Path,
    project_id: str,
    target: str,
    decision_id: str | None = None,
    decision_status: str | None = None,
    note: str = "",
) -> dict:
    """Mark one explicitly selected state or decision as human-confirmed."""
    if target not in {"state", "decision"}:
        raise ProjectDataError("target 必须是 state 或 decision")
    project = load_project(projects_root, project_id)
    now = date.today().isoformat()

    if target == "state":
        if decision_id or decision_status:
            raise ProjectDataError("确认 state 时不能指定 decision_id 或 decision_status")
        path = projects_root / project_id / "state.md"
        post = frontmatter.load(path)
        post.metadata["last_modified_by"] = "Human"
        post.metadata["last_confirmed_at"] = now
        post.metadata["updated_at"] = now
        result = {
            "project_id": project_id,
            "target": "state",
            "path": path.relative_to(projects_root.parent).as_posix(),
            "confirmed_by": "Human",
            "confirmed_at": now,
        }
    else:
        if not decision_id:
            raise ProjectDataError("确认 decision 时必须指定 decision_id")
        matches = [d for d in project["decisions"] if d["decision_id"] == decision_id]
        if len(matches) != 1:
            raise ProjectDataError(f"未找到唯一决策记录: {decision_id}")
        decision = matches[0]
        new_status = decision_status or decision["decision_status"]
        if new_status not in CONFIRMABLE_DECISION_STATUSES:
            raise ProjectDataError("确认决策时 status 必须是 reviewed 或 executed")
        path = projects_root.parent / decision["path"]
        post = frontmatter.load(path)
        post.metadata["decision_status"] = new_status
        post.metadata["last_modified_by"] = "Human"
        post.metadata["review_date"] = now
        post.metadata["last_confirmed_at"] = now
        result = {
            "project_id": project_id,
            "target": "decision",
            "decision_id": decision_id,
            "decision_status": new_status,
            "path": decision["path"],
            "confirmed_by": "Human",
            "confirmed_at": now,
        }

    write_context(path, frontmatter.dumps(post))
    log_path = projects_root.parent / "log.md"
    log_entry = (
        f"\n## [{now}] confirm | {project_id}\n"
        f"- 确认对象：{target}"
        + (f" {decision_id}" if decision_id else "")
        + f"（{result.get('path')}）。\n"
        "- 操作者：Human；仅更新 frontmatter 的确认标记，正文与证据入口未改。\n"
        + (f"- 备注：{note.strip()}\n" if note.strip() else "")
    )
    if log_path.is_file():
        write_context(log_path, log_path.read_text(encoding="utf-8") + log_entry)
    result["written"] = True
    result["note"] = note.strip()
    return result
