# GroundMap 内部测试用户手册

本手册适用于 Windows 10/11 单人、单机内部测试包。请按顺序操作。第一次先使用包内演示库，确认运行正常后，再建立自己的知识库。

## 一、使用边界

- 当前版本是内部测试版，不是公网多人系统。
- 每名测试者使用一份独立压缩包和独立数据目录。
- 包内 `groundmap-demo` 全部是虚构数据，可以安全用于功能测试。
- 自己的原始文件只放在自己的数据目录，不要发回给维护者，也不要混入演示库。
- API Key 只保存在本机 `test-kit/.env.local`，不得写入 Markdown、截图、反馈文档或 Git。
- “仅本地”不会调用 Web；“联网搜索”先查本地，再强制调用 Web 补充。Web 内容不会自动写入 Wiki。

## 二、开始前准备

建议配置：

- Windows 10/11 64 位；
- 至少 8 GB 内存，建议 16 GB；
- 首次配置期间保持联网；
- 至少 3 GB 可用磁盘空间；
- 有权在本机安装软件，或能联系内部 IT；
- 不要把程序和数据放在 OneDrive、企业网盘、共享盘或只读目录。

推荐安装位置示例：

```text
D:\GroundMap-Test\
```

如果没有 D 盘，可以放在：

```text
C:\Users\你的用户名\GroundMap-Test\
```

路径尽量短，只使用中文、英文、数字、连字符或下划线。不要直接在 ZIP 内运行程序。

## 三、解压和首次配置

1. 收到 ZIP 后，先保存维护者单独发送的文件名和 SHA256。
2. 右键 ZIP，选择“属性”。如果看到“解除锁定”，勾选后应用。
3. 右键 ZIP，选择“全部解压”。
4. 打开解压后的最外层目录，确认能看到：

```text
GroundMap.cmd
START-HERE.md
USER-GUIDE.zh-CN.md
test-kit\
scripts\
web\
```

5. 双击 `GroundMap.cmd`。
6. 首次运行会自动完成：
   - 检查 Python、Node.js、npm 和 Git；
   - 在 winget 可用时自动安装缺失的运行时；
   - 安装文档转换、OCR 和音频转写组件；
   - 准备 faster-whisper `small` 语音模型；
   - 安装两个本地 Web 应用的依赖；
   - 转换演示文件；
   - 执行知识库健康检查和测试；
   - 创建桌面快捷方式；
   - 启动服务，并在浏览器中同时打开知识库管理台和查询工作台。
7. 安装过程可能弹出 Windows 管理员授权，请核对程序来自本测试包或 Windows Package Manager 后再允许。
8. 第一次运行耗时取决于网络和电脑性能。窗口没有显示错误时不要重复双击。

首次成功后会生成：

```text
test-kit\.setup-complete
test-kit\.env.local
test-kit\.runtime\
```

其中 `.env.local` 是本机私密配置，不能转发；`.runtime` 是运行日志和进程记录；`.setup-complete` 表示首次配置已完成。

## 四、如何判断首次配置成功

成功时应看到绿色提示，并自动打开查询控制台：

```text
http://127.0.0.1:3100/?ws=groundmap-demo
```

知识库管理台地址：

```text
http://127.0.0.1:3006
```

浏览器顶栏当前 workspace 应显示 `groundmap-demo`。如果浏览器没有自动打开，但命令窗口显示成功，可以手动复制以上地址。

查询工作台顶栏提供“知识库 ↗”按钮，可以随时在新标签页打开当前 workspace 的知识库管理台。

首次验证建议在“仅本地”模式询问：

```text
星港屋顶温室试点的预算、面积、下一里程碑和主要风险分别是什么？
```

预期回答包含演示库事实，并显示本地来源。

## 五、日常启动和停止

### 启动

以后直接使用任一方式：

- 双击解压目录根部的 `GroundMap.cmd`；
- 双击桌面的 `GroundMap Internal Test` 快捷方式；
- 排障时双击 `test-kit/02-START-GROUNDMAP.cmd`。

不要连续启动多次。启动成功后可以关闭命令窗口，但不要删除 `.runtime` 中正在使用的记录。

### 停止

完成测试后双击：

```text
test-kit\03-STOP-GROUNDMAP.cmd
```

关闭浏览器标签页不等于停止本地服务。需要重新配置 API Key、数据根或 workspace 时，也应先停止服务。

## 六、配置本地问答和联网搜索

用记事本打开：

```text
test-kit\.env.local
```

只测试知识库浏览、转换和本地检索时，可以不填写任何 API Key。

如需使用 DeepSeek 问答与联网补充，填写自己的 Key：

```dotenv
DEEPSEEK_API_KEY=你的真实Key
WEB_SEARCH_MODEL=deepseek-v4-flash
```

规则：

- 等号两边不要加空格；
- 值不要加引号；
- 一行只写一个变量；
- 不要删除文件中其他配置；
- 保存后先停止 GroundMap，再重新启动；
- 不要把 `.env.local` 发给任何人。

界面模式含义：

- `仅本地`：只查当前 workspace 的 Wiki 和派生文件，不调用 Web；
- `联网搜索`：先查当前本地知识库，再强制调用 Web 补充；
- 回答中的 `[LOCAL]` 和 `[WEB]` 应分区显示；
- Web 查询结果只用于当前回答，不会自动写入 Wiki。

## 七、第一次建立自己的知识库

不要把真实资料放进 `test-kit/demo-data`。建议单独建立数据根，例如：

```text
C:\Users\你的用户名\GroundMap-UserData\
```

### 1. 打开正确的 PowerShell

在解压后的 GroundMap 根目录空白处按住 Shift 并右键，选择“在此处打开 PowerShell 窗口”或“在终端中打开”。执行：

```powershell
$dataRoot = Join-Path $env:USERPROFILE 'GroundMap-UserData'
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
$env:KB_ROOT = $dataRoot
$dataRoot
```

最后一行会显示真实数据路径。请复制保存。

### 2. 确定 workspace 名称

workspace 是相互隔离的知识空间。名称只能使用小写英文字母、数字、连字符和下划线，并以字母或数字开头，例如：

```text
my-research
phd-thesis
hardware-project
commercialization
```

建议初次测试只建一个综合 workspace，例如 `my-work`。只有确实需要权限、身份或知识边界隔离时，再拆分多个 workspace。

### 3. 创建 workspace

在同一个 PowerShell 窗口执行：

```powershell
python .\scripts\k.py new-workspace my-work --json
```

成功后会生成：

```text
GroundMap-UserData\
└─ workspaces\
   └─ my-work\
      ├─ raw\
      ├─ derived\
      ├─ wiki\
      ├─ projects\
      ├─ exports\
      ├─ my_thoughts\
      └─ log.md
```

### 4. 让网页长期使用新 workspace

停止 GroundMap，用记事本打开 `test-kit/.env.local`，把以下两行改为自己的真实值：

```dotenv
KB_ROOT=C:\Users\你的用户名\GroundMap-UserData
KB_WORKSPACE=my-work
```

保存后重新双击 `GroundMap.cmd`。顶栏应出现并选中 `my-work`。

注意：`.env.local` 中不能使用“你的用户名”占位文字，必须粘贴 PowerShell 实际输出的完整路径。

## 八、文件应该放在哪里

所有原始文件都放在当前 workspace 的 `raw` 下。可以按领域自由建立子目录，例如：

```text
GroundMap-UserData\workspaces\my-work\raw\
├─ phd\
├─ research-papers\
├─ engineering\
├─ projects\
├─ commercialization\
├─ meetings\
└─ personal-history\
```

系统会递归扫描这些子目录。分类名称主要供人理解，不影响转换能力。

当前支持：

- 文档：PDF、DOCX、PPTX、XLSX、XLS、EPUB；
- 文本与数据：Markdown、HTML、CSV、JSON、XML；
- 图片：PNG、JPG、JPEG、GIF、BMP、TIFF、WebP；
- 音频：MP3、WAV、M4A；
- 邮件：MSG。

文件规则：

- `raw` 是原件区，放入后不要让程序或 Agent改写原文件；
- 同一资料不要在多个目录重复保存；
- 转换后尽量不要重命名或移动原件，否则旧引用可能失效；
- 扫描件、复杂表格、嵌入图片和长音频应重点检查质量报告；
- 不要把 API Key、密码、私钥或账号恢复码作为知识资料导入；
- 导入单位或客户资料前，先确认内部授权和保密边界。

## 九、执行文件转换和 ingest

### 1. 每次打开 PowerShell先设置数据根

`.env.local` 只供网页启动脚本读取，不会自动改变新开的 PowerShell。每次执行 CLI 前先运行：

```powershell
$env:KB_ROOT = Join-Path $env:USERPROFILE 'GroundMap-UserData'
```

如果数据根不在该位置，请改为自己的完整路径。

### 2. 预览待转换文件

```powershell
python .\scripts\convert.py --workspace my-work --dry-run
```

先核对待转换数量和文件名。`dry-run` 不会写入文件。

### 3. 开始增量转换

```powershell
python .\scripts\convert.py --workspace my-work
```

它只转换新增或发生变化的原件，未变化的文件会显示“已是最新”。不要为了保险反复使用 `--force`。

如只处理特定格式：

```powershell
python .\scripts\convert.py --workspace my-work --ext .pdf,.docx
```

确实需要重建全部派生文件时才运行：

```powershell
python .\scripts\convert.py --workspace my-work --force
```

### 4. 理解转换结果

目录会保持对应关系，例如：

```text
raw\phd\chapter-1.pdf
    ↓
derived\phd\chapter-1.md
derived\phd\chapter-1.outline.json
derived\phd\chapter-1.source.json
derived\phd\chapter-1.quality.json
derived\phd\chapter-1.evidence.json（适用时）
```

- `.md`：可检索的正文；
- `.outline.json`：章节和稳定锚点；
- `.source.json`：原件哈希、转换器和来源信息；
- `.quality.json`：成功、降级、失败和待复核问题；
- `.evidence.json`：页码、bbox、Sheet/range 等证据坐标；
- `visual/asset/transcript`：图片或音频适用的派生内容。

不要手动编辑 `derived`。发现问题应修复原件、配置或转换器后重新生成。

### 5. 检查转换质量

列出所有质量报告：

```powershell
Get-ChildItem -LiteralPath "$env:KB_ROOT\workspaces\my-work\derived" -Recurse -Filter '*.quality.json'
```

重点区分：

- `success`：转换完成，但重要事实仍应抽查；
- `degraded`：有低置信度 OCR、复杂布局、媒体或定位问题，需要人工检查；
- `failed`：不能作为可信来源使用，应先排障再重试。

### 6. 运行健康检查

```powershell
python .\scripts\k.py --workspace my-work health --json
python .\scripts\k.py --workspace my-work list-broken-refs --json
python .\scripts\k.py --workspace my-work list-source-issues --json
```

新建但尚未整理 Wiki 的 workspace 页面数量很少是正常的；转换命令成功不等于所有内容已经人工确认。

## 十、“转换”和“长期知识沉淀”的区别

GroundMap 有两层 ingest：

1. 技术转换：`raw → derived`。由 `convert.py` 自动完成，完成后内容已经可以被本地检索和问答读取。
2. 语义沉淀：`derived → wiki/projects`。由用户或外部 AI Agent 阅读、综合、引用和审核，把长期有价值的结论沉淀为知识页和项目状态。

系统不会因为上传了一份文件，就自动把模型生成的结论当作已确认事实。Agent 创建的 Wiki 页面应保持：

```yaml
status: draft
last_modified_by: LLM
```

只有人工核对后才能改为已审核状态。不同来源有冲突时，应保留双方论断及来源，不能静默覆盖。

如果测试者使用 Codex、Claude Code 或其他本地 Agent，可以给出以下任务：

```text
请使用数据根 C:\Users\我的用户名\GroundMap-UserData，workspace 为 my-work。
我已经把新文件放入 raw/。

请完成：
1. 先运行 convert.py 的 dry-run，再执行增量转换；
2. 检查所有 source manifest 和 quality report；
3. 按 outline 分段读取 derived 内容；
4. 在 wiki/sources 创建来源摘要，并用 derived 文件的块级 anchor 引用关键事实；
5. 更新相关 concepts、entities、analyses 和 root_index；
6. 所有 Agent 写入保持 status: draft、last_modified_by: LLM；
7. 保留冲突、未知项和低置信度提示；
8. 运行 health、list-broken-refs、list-source-issues 和 list-coarse-citations；
9. 汇报新增、修改、失败和需要我人工确认的内容。
```

## 十一、搜索和检查自己的资料

命令行搜索：

```powershell
$env:KB_ROOT = Join-Path $env:USERPROFILE 'GroundMap-UserData'
python .\scripts\k.py --workspace my-work search "你的关键词" --json
```

查看某份派生文档的大纲：

```powershell
python .\scripts\k.py --workspace my-work outline derived\phd\chapter-1.md --json
```

在网页端：

1. 启动 GroundMap；
2. 确认顶栏 workspace 为 `my-work`；
3. 选择“仅本地”；
4. 先问文件中可以直接核实的问题；
5. 检查回答是否列出本地来源和精确定位；
6. 对重要数字回到原件人工复核。

如果本地资料没有答案，系统应明确说明未知，而不是用 Web 或模型常识冒充本地事实。

## 十二、如何管理后续项目

一个 workspace 可以同时包含科研、工程和商业资料；每个现实项目放在：

```text
workspaces\my-work\projects\项目ID\
```

最小结构：

```text
projects\my-project\
├─ brief.md
├─ state.md
├─ decisions\
├─ progress\
└─ context.md
```

各文件用途：

- `brief.md`：目标、非目标、范围和证据入口；
- `state.md`：当前结果、下一行动、阻塞、风险和负责人；
- `decisions/DEC-xxx.md`：关键决策、原因和验证状态；
- `progress/EXEC-xxx.md`：现实行动、结果和修正；
- `context.md`：供其他模型继承背景的 Context Pack，由命令生成。

项目文件可以由 Agent 起草，但真实状态、决策和行动结果必须由人确认。常用命令：

```powershell
python .\scripts\k.py --workspace my-work project-list --json
python .\scripts\k.py --workspace my-work project-show my-project --json
python .\scripts\k.py --workspace my-work context-build my-project --json
```

不要用项目文件代替原始证据；项目状态中的关键事实仍应链接到 `wiki` 或 `derived` 来源。

## 十三、持续添加和更新文件

后续每次增加资料，重复以下流程即可：

1. 停止正在进行的批量转换；
2. 把新原件复制到对应 `raw` 子目录；
3. 运行 `--dry-run`；
4. 运行增量 `convert.py`；
5. 检查新增质量报告；
6. 运行本地查询抽查；
7. 让 Agent 更新 Wiki 或项目记录；
8. 人工审核重要结论；
9. 运行健康检查；
10. 备份数据根。

不要删除旧结论来掩盖变化。事实发生变化时，应保留旧版本、日期和来源，并明确当前采用的版本。

## 十四、备份、升级和卸载

### 备份

至少备份整个独立数据根：

```text
GroundMap-UserData\
```

重点保护：

- `raw` 原件；
- `wiki` 长期知识；
- `projects` 项目状态；
- `my_thoughts` 私人笔记；
- `exports` 已输出成果；
- Git 历史（如果已启用）。

`derived` 和缓存理论上可以重建，但首次内部测试建议一起备份，便于排障。

### 升级

1. 停止旧版本；
2. 备份数据根和旧 `.env.local`；
3. 把新版 ZIP 解压到一个新目录，不要直接覆盖旧程序目录；
4. 首次启动新版；
5. 将新版 `.env.local` 指向原来的独立数据根；
6. 执行 `--dry-run` 和健康检查；
7. 确认正常后再保留或归档旧程序目录。

### 卸载

先停止服务，然后删除程序解压目录和桌面快捷方式。独立的 `GroundMap-UserData` 不会自动删除；确认已备份且确实不再需要时再人工处理。

## 十五、常见问题

### 双击后提示缺少 winget

请从官方渠道或通过内部 IT 安装 Python 3.11–3.13、Node.js LTS 和 Git for Windows，然后重新双击 `GroundMap.cmd`。

### pip、npm 或语音模型下载失败

通常是代理、防火墙或软件源限制。不要从不明网盘下载依赖。请记录完整错误并联系内部 IT或维护者。

### 浏览器打不开

先确认命令窗口是否显示成功，再手动打开：

```text
http://127.0.0.1:3006
http://127.0.0.1:3100
```

仍失败时查看：

```text
test-kit\.runtime\web.err.log
test-kit\.runtime\console.err.log
```

### 端口被占用

先运行 `03-STOP-GROUNDMAP.cmd`。仍被占用时，在 PowerShell 执行：

```powershell
Get-NetTCPConnection -LocalPort 3006,3100 -ErrorAction SilentlyContinue
```

关闭占用这些端口的程序后重试。

### 联网搜索按钮不可用

确认 `.env.local` 已填写有效的 `DEEPSEEK_API_KEY`，保存后完整停止并重新启动。

### 网页仍显示演示库

检查 `.env.local` 的 `KB_ROOT` 和 `KB_WORKSPACE`，确认路径真实存在、workspace 名拼写一致，然后停止并重启。

### 文件转换成功但问不到内容

依次检查：

1. 顶栏是否选中了正确 workspace；
2. 文件是否放在该 workspace 的 `raw` 下；
3. `derived` 中是否生成对应 Markdown；
4. `.quality.json` 是否为 failed；
5. 使用 `k.py search` 是否能命中关键词；
6. 问题是否使用了原文件中真实出现的术语。

### 音频无法转写

打开 `test-kit/.setup-complete`，确认 `audioModelStatus` 为 `ready`。如为 `download_failed`，网络恢复后删除 `.setup-complete`，重新运行 `test-kit/01-FIRST-TIME-SETUP.cmd`。

如果只看到 pydub 的系统 FFmpeg 警告，但转换与健康检查继续成功，可以忽略。GroundMap 的 faster-whisper 路径使用 PyAV。

## 十六、反馈时需要提供什么

请提供：

- Windows 版本；
- 测试包版本；
- 操作步骤；
- 预期结果和实际结果；
- 错误窗口完整文字；
- `.runtime` 中相关日志；
- 文件格式、大小和页数/时长；
- 是否为“仅本地”或“联网搜索”；
- 是否能够稳定复现。

反馈前必须删除 API Key、姓名、联系方式、项目敏感信息和原始文件内容。未经授权不要发送真实 `raw` 文件。
