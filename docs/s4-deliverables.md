# S4 可追溯成果

GroundMap 的成果层只负责本地证据、版本和确认状态，不在核心引擎内调用模型。Agent 可以依据项目 Context Pack 编写正文，但新成果一律先保存为 `draft / LLM`。

## 创建草稿

```powershell
$env:KB_ROOT = "<data-root>"
python scripts/k.py --workspace <workspace> deliverable-create <project-id> <deliverable-id> `
  --kind project-proposal `
  --title "项目建议书" `
  --source-ref "projects/<project-id>/context.md" `
  --source-ref "wiki/concepts/example.md"
```

支持三种最小成果类型：`research-brief`、`project-proposal` 和 `business-one-pager`。每次创建都会新增 `exports/<project-id>/<deliverable-id>/vNNN.md`，不会覆盖旧版本。每个版本记录 Context Pack 哈希和非空本地 `source_refs`；不存在或越界的来源会被拒绝。

## 查看与确认

```powershell
python scripts/k.py --workspace <workspace> deliverable-list --project-id <project-id>
python scripts/k.py --workspace <workspace> deliverable-confirm <project-id> <deliverable-id> 1
```

也可以在 Web 的“项目总控”页面展开成果、审阅正文并点击“确认此版本”。确认动作会二次询问，只将选中版本改为 `reviewed / Human`，然后把该版本的路径加入项目 `state.md` 的 `deliverable_refs`。正文和旧版本不会被覆盖。

## 安全边界

- Web 来源不能直接成为成果的本地证据，也不会自动写入 Wiki。
- 规划、宣传和推断必须与已确认的项目事实区分。
- Context Pack 更新后，旧成果仍保留；列表中的 `context_current` 会提示它是否基于当前版本。
- 未经 Human 确认的成果不能视为已验收交付物。
