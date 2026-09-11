"""S4 deliverable versioning, evidence, and confirmation checks."""
from __future__ import annotations

from pathlib import Path

import frontmatter
import pytest
import yaml

from context_pack import ProjectDataError
from deliverables import confirm_deliverable, create_deliverable, list_deliverables


def write_markdown(path: Path, metadata: dict, body: str = "# Fixture\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    path.write_text(f"---\n{header}\n---\n\n{body}", encoding="utf-8")


def make_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    project = workspace / "projects" / "demo-project"
    write_markdown(
        project / "state.md",
        {
            "project_id": "demo-project",
            "status": "active",
            "updated_at": "2026-09-07",
            "owner": "Human",
            "current_outcome": "Context Pack ready",
            "next_action": "Create reviewed deliverables",
            "blocked_by": [],
            "decision_refs": [],
            "knowledge_refs": ["[[wiki/example]]"],
            "last_modified_by": "Human",
        },
        "# State\n",
    )
    (project / "context.md").write_text("# Context Pack\n", encoding="utf-8")
    write_markdown(workspace / "wiki" / "example.md", {"title": "Evidence"})
    return workspace


def test_create_keeps_versions_and_local_evidence(tmp_path):
    workspace = make_workspace(tmp_path)
    first = create_deliverable(
        workspace,
        "demo-project",
        "proposal",
        "project-proposal",
        "Demo proposal",
        ["projects/demo-project/context.md", "wiki/example.md#Evidence"],
    )
    second = create_deliverable(
        workspace,
        "demo-project",
        "proposal",
        "project-proposal",
        "Demo proposal revision",
        ["projects/demo-project/context.md"],
    )

    assert first["path"].endswith("proposal/v001.md")
    assert second["path"].endswith("proposal/v002.md")
    records = list_deliverables(workspace, "demo-project")
    assert [item["version"] for item in records] == [1, 2]
    assert all(item["status"] == "draft" for item in records)
    assert all(item["valid"] for item in records)
    assert all(item["context_current"] for item in records)


def test_missing_or_escaping_evidence_is_rejected(tmp_path):
    workspace = make_workspace(tmp_path)
    with pytest.raises(ProjectDataError, match="source_ref 不存在"):
        create_deliverable(
            workspace, "demo-project", "brief", "research-brief", "Brief", ["wiki/missing.md"]
        )
    with pytest.raises(ProjectDataError, match="路径越界"):
        create_deliverable(
            workspace, "demo-project", "brief", "research-brief", "Brief", ["../secret.md"]
        )


def test_confirmation_preserves_body_and_writes_state_reference(tmp_path):
    workspace = make_workspace(tmp_path)
    body = "# Proposal\n\nA reviewed human-facing body.\n"
    created = create_deliverable(
        workspace,
        "demo-project",
        "proposal",
        "project-proposal",
        "Demo proposal",
        ["projects/demo-project/context.md"],
        body=body,
    )
    result = confirm_deliverable(workspace, "demo-project", "proposal", 1, "Approved")

    artifact = frontmatter.load(workspace / created["path"])
    state = frontmatter.load(workspace / "projects" / "demo-project" / "state.md")
    assert result["status"] == "reviewed"
    assert artifact.metadata["last_modified_by"] == "Human"
    assert artifact.metadata["review_note"] == "Approved"
    assert artifact.content.strip() == body.strip()
    assert created["path"] in state.metadata["deliverable_refs"]
    assert state.metadata["last_modified_by"] == "Human"


def test_confirmation_rejects_tampered_metadata(tmp_path):
    workspace = make_workspace(tmp_path)
    created = create_deliverable(
        workspace,
        "demo-project",
        "brief",
        "research-brief",
        "Brief",
        ["projects/demo-project/context.md"],
    )
    path = workspace / created["path"]
    post = frontmatter.load(path)
    post.metadata["version"] = 9
    path.write_text(frontmatter.dumps(post), encoding="utf-8")

    with pytest.raises(ProjectDataError, match="version 与文件名不一致"):
        confirm_deliverable(workspace, "demo-project", "brief", 1)
