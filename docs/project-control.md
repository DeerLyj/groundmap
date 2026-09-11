# 项目总控与执行闭环

GroundMap 把项目状态放在 `projects/`，避免与 `wiki/` 中的长期知识混淆。一个项目的最小目录如下：

```text
projects/<project_id>/
├── brief.md
├── state.md
├── decisions/
│   ├── DEC-001.md
│   └── DEC-002.md
├── progress/
│   └── EXEC-001.md
└── context.md              # 由 context-build 生成
```

旧项目不需要迁移：没有 `progress/` 时仍可读取，只会被标记为“P2 业务闭环待补”。

## 执行记录契约

每次现实行动单独保存为 `progress/*.md`。以下字段和三个非空章节是必需的：

```markdown
---
title: "完成一次真实交付"
project_id: demo-project
execution_id: EXEC-001
recorded_at: 2026-09-06
last_modified_by: Human
---

## 行动

实际做了什么，以及使用了哪些输入。

## 结果

现实世界中观察到的结果；失败和不确定性也应原样记录。

## 修正

根据结果改变了什么判断、计划或下一行动。
```

章节也可使用英文标题 `Action`、`Result`、`Revision`。LLM 可以起草记录，但只有 `last_modified_by: Human` 的记录才计入已确认闭环。

## P2 闭环判定

`project-list --json` 和 `project-show --json` 都返回 `control_loop`。只有以下五项同时满足，`control_loop.complete` 才为 `true`：

1. 存在 `brief.md`；
2. `state.md` 已由 Human 确认；
3. 至少两条决策为 `reviewed` 或 `executed`，且已由 Human 确认；
4. 至少一条完整执行记录已由 Human 确认；
5. 已写入 `context.md`。

```powershell
$env:KB_ROOT = "<data-root>"
python scripts/k.py --workspace <workspace> project-list --json
python scripts/k.py --workspace <workspace> project-show <project_id> --json
python scripts/k.py --workspace <workspace> project-confirm <project_id> execution EXEC-001 --json
python scripts/k.py --workspace <workspace> context-build <project_id> --json
```

生成的 Context Pack 会包含当前状态、执行记录、决策、证据入口以及风险和未知项。项目 Web 页面展示相同的闭环状态；它不会替用户编造、自动确认或自动写入现实结果。
