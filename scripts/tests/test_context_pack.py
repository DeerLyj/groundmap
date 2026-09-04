"""Project State / Decision Record / Context Pack acceptance checks."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from context_pack import (
    build_context_pack,
    confirm_project_record,
    list_projects,
    load_project,
)


def write_project_file(path: Path, fm: dict, body: str) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    header = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    path.write_text(f"---\n{header}\n---\n\n{body}\n", encoding="utf-8")


def make_project(root: Path) -> Path:
    project = root / "projects" / "demo-project"
    write_project_file(
        project / "brief.md",
        {"title": "Demo project", "project_id": "demo-project"},
        "## 目标\n\n完成一个可验证的阶段成果。\n\n## 非目标\n\n不建设完整任务管理器。",
    )
    write_project_file(
        project / "state.md",
        {
            "project_id": "demo-project",
            "status": "active",
            "updated_at": "2026-09-02",
            "owner": "Human",
            "current_outcome": "阶段成果可复核",
            "next_action": "完成一次交接测试",
            "blocked_by": [],
            "decision_refs": ["[[projects/demo-project/decisions/DEC-001]]"],
            "knowledge_refs": ["[[wiki/concepts/example]]"],
        },
        "## 当前进展\n\n已完成基础实现。\n\n## 风险\n\n真实样本尚未验证。",
    )
    write_project_file(
        project / "decisions" / "DEC-001.md",
        {
            "title": "采用最小闭环",
            "project_id": "demo-project",
            "decision_id": "DEC-001",
            "decision_status": "reviewed",
            "decision_date": "2026-09-01",
        },
        "## 当前判断\n\n先完成状态、决策和交接。\n\n## 关键假设\n\n现有文件契约足够支撑第一版。",
    )
    write_project_file(
        project / "decisions" / "DEC-002.md",
        {
            "title": "等待样本验收",
            "project_id": "demo-project",
            "decision_id": "DEC-002",
            "decision_status": "pending_validation",
            "decision_date": "2026-09-02",
        },
        "## 行动\n\n准备真实样本。",
    )
    return root / "projects"


def test_list_and_show_project_records(tmp_path):
    projects_root = make_project(tmp_path)
    items = list_projects(projects_root)
    assert len(items) == 1
    assert items[0]["valid"] is True
    assert items[0]["decision_count"] == 2

    project = load_project(projects_root, "demo-project", decision_status="reviewed")
    assert project["state"]["frontmatter"]["next_action"] == "完成一次交接测试"
    assert [d["decision_id"] for d in project["decisions"]] == ["DEC-001"]
    assert project["decisions"][0]["sections"]["关键假设"].startswith("现有文件")


def test_context_is_project_scoped_and_deterministic(tmp_path):
    projects_root = make_project(tmp_path)
    project = load_project(projects_root, "demo-project")
    first = build_context_pack(project)
    second = build_context_pack(load_project(projects_root, "demo-project"))
    assert first == second
    assert "Demo project" in first
    assert "完成一次交接测试" in first
    assert "采用最小闭环" in first
    assert "memory" not in first
    assert "wiki/concepts/example" in first
    assert first.count("wiki/concepts/example") == 1


def test_context_respects_budget(tmp_path):
    projects_root = make_project(tmp_path)
    context = build_context_pack(load_project(projects_root, "demo-project"), max_chars=1200)
    assert len(context) <= 1200
    assert "项目目标与范围" in context


def test_cli_context_build_can_be_read_only(tmp_path):
    projects_root = make_project(tmp_path)
    data_root = tmp_path / "data"
    (data_root / "workspaces" / "demo").mkdir(parents=True)
    # The CLI reads DATA_ROOT/workspaces/<workspace>; move the fixture there.
    workspace = data_root / "workspaces" / "demo"
    source_project = projects_root
    (workspace / "projects").mkdir()
    for path in source_project.rglob("*"):
        if path.is_file():
            target = workspace / "projects" / path.relative_to(source_project)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())

    env = dict(os.environ)
    env["KB_ROOT"] = str(data_root)
    command = [
        sys.executable,
        str(Path(__file__).resolve().parents[1] / "k.py"),
        "--workspace",
        "demo",
        "context-build",
        "demo-project",
        "--no-write",
        "--json",
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=env)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["written"] is False
    assert payload["context_path"].endswith("projects/demo-project/context.md")
    assert not (workspace / "projects" / "demo-project" / "context.md").exists()


def test_explicit_confirmation_updates_only_selected_frontmatter(tmp_path):
    projects_root = make_project(tmp_path)

    state_result = confirm_project_record(projects_root, "demo-project", "state")
    assert state_result["confirmed_by"] == "Human"
    state = load_project(projects_root, "demo-project")["state"]
    assert state["frontmatter"]["last_modified_by"] == "Human"
    assert "已完成基础实现" in state["content"]

    decision_result = confirm_project_record(
        projects_root,
        "demo-project",
        "decision",
        "DEC-002",
        "reviewed",
    )
    assert decision_result["decision_status"] == "reviewed"
    decision = next(
        d for d in load_project(projects_root, "demo-project")["decisions"]
        if d["decision_id"] == "DEC-002"
    )
    assert decision["frontmatter"]["last_modified_by"] == "Human"
    assert decision["frontmatter"]["decision_status"] == "reviewed"
    context = build_context_pack(load_project(projects_root, "demo-project"))
    assert "等待样本验收" in context.split("## 决策记录", 1)[1].split("## 证据与知识入口", 1)[0]
