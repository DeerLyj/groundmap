# Obsidian 与 GroundMap 集成

## 目标

Obsidian 作为个人 AI OS 的本地工作界面，GroundMap 作为知识治理和 Agent 执行引擎。两者直接使用同一套 Markdown 文件，不建立第二份需要同步的知识库。

```text
GroundMap 引擎目录
└── scripts/、web/、tools/

个人数据根目录
└── workspaces/
    └── personal-ai-os/     ← 作为 Obsidian Vault 打开
        ├── wiki/
        ├── raw/
        ├── derived/
        ├── my_thoughts/
        ├── exports/
        ├── .cache/
        └── log.md
```

## 建议的打开方式

Obsidian 应打开具体 workspace 目录：

```text
<DATA_ROOT>/workspaces/<workspace>
```

不要直接打开 `<DATA_ROOT>`。GroundMap 的 `wiki/...`、`raw/...` 等链接是相对于 workspace 根目录解析的，打开数据根目录会把多个 workspace 混在一个 Vault 中。

如果 workspace 尚未创建：

```powershell
$env:KB_ROOT = "<DATA_ROOT>"
python <ENGINE_ROOT>/scripts/k.py new-workspace personal-ai-os
```

然后在 Obsidian 中选择 **Open folder as vault**，打开：

```text
<DATA_ROOT>\workspaces\personal-ai-os
```

## GroundMap 启动

```powershell
cd <ENGINE_ROOT>\web
$env:KB_ROOT = "<DATA_ROOT>"
$env:KB_WORKSPACE = "personal-ai-os"
npm run dev:all
```

- 管理台：`http://localhost:3006`
- 查询控制台：`http://localhost:3100`

检查 workspace 是否适合作为 Vault：

```powershell
cd <ENGINE_ROOT>
$env:KB_ROOT = "<DATA_ROOT>"
python scripts/k.py --workspace personal-ai-os obsidian-check --json
```

该命令只读检查目录、根索引、Git 和 Wiki 健康度，不会创建或修改文件。

## 三者的职责

| 工具 | 负责内容 |
|---|---|
| Obsidian | 快速记录、阅读、人工整理和浏览 Markdown |
| GroundMap Web | 页面浏览、图谱、健康度、冲突和记忆审核 |
| Codex / Claude Code | convert、OCR、ingest、Wiki 更新、查询和输出生成 |

## 文件编辑边界

- `wiki/**`：可在 Obsidian 中人工编辑；修改后用 GroundMap health 检查。
- `raw/**`：保存不可变原件，不由 Agent 改写。
- `derived/**`：转换 Markdown、OCR、outline 和 Source Manifest，可重建，不手改。
- `my_thoughts/**`：人工专属区域；Agent 不写入。
- `wiki/memory/candidates/`：候选记忆，不能自动影响 Agent。
- `wiki/memory/confirmed.md`：仅保存用户确认后的长期记忆。
- `.cache/**`：GroundMap 派生缓存，不要人工编辑。

不要让 Obsidian 和 GroundMap Web 同时编辑同一个文件。Obsidian 的自动重命名、批量格式化或自动提交功能也应谨慎启用，先确保不会改写系统字段、锚点和引用。

## 日常闭环

```text
Obsidian 记录想法
        ↓
原始资料放入 raw/，转换视图生成到 derived/
        ↓
GroundMap convert / OCR
        ↓
外部 Agent 执行 ingest
        ↓
GroundMap Web 审阅冲突、记忆和健康度
        ↓
Obsidian 阅读和继续整理
```

## Git 和备份

个人数据根目录应作为独立 Git 仓库，代码仓库与个人资料仓库分开。至少确认以下内容：

```powershell
git -C <DATA_ROOT> rev-parse --show-toplevel
git -C <DATA_ROOT> status
```

数据仓库的 `.gitignore` 应排除原始资料、私人笔记和缓存，并保留 `wiki/`、`exports/`、`log.md`。首次正式使用前应先完成一次可恢复的备份。

## 不建议现在做的事

- 不要把 Wiki 复制一份到另一个 Obsidian Vault。
- 不要让 Obsidian 成为第二套数据库。
- 不要一开始启用自动 Git 提交或大量社区插件。
- 不要把隐私、家庭对话自动写入 `wiki/memory/`。
- 不要用 Obsidian Sync 替代个人数据仓库的 Git 备份。

后续可以在 GroundMap 页面加入“在 Obsidian 中打开”按钮；`obsidian://` URI 也可以定位到指定文件、标题或块。
