# GroundMap 新项目摄入、指定内容撤出与启动命令

本文假设测试包已经完成首次配置，并且解压目录根部能看到 `GroundMap.cmd`。所有命令都在该根目录的 PowerShell 中执行。

示例变量：

```powershell
$dataRoot = Join-Path $env:USERPROFILE 'GroundMap-UserData'
$workspace = 'my-work'
$projectId = 'my-project'
$env:KB_ROOT = $dataRoot
$workspaceRoot = Join-Path $dataRoot "workspaces\$workspace"
```

请把 `my-work`、`my-project` 和数据根替换成自己的真实值。项目和 workspace ID 只使用小写字母、数字、连字符或下划线。

## 一、启动知识库和查询工作台

### 推荐：一条命令同时启动

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\test-kit\start.ps1
```

也可以直接双击根目录的 `GroundMap.cmd`。成功后：

- 知识库管理台：<http://127.0.0.1:3006>
- 查询工作台：<http://127.0.0.1:3100>

只启动、不自动打开浏览器：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\test-kit\start.ps1 -NoBrowser
```

停止两个服务：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\test-kit\stop.ps1
```

### 排障：分别启动两个服务

先确认 `test-kit/.env.local` 的 `KB_ROOT` 和 `KB_WORKSPACE` 已正确配置。

PowerShell 窗口一启动知识库管理台：

```powershell
$env:KB_ROOT = Join-Path $env:USERPROFILE 'GroundMap-UserData'
$env:KB_WORKSPACE = 'my-work'
$env:NEXT_PUBLIC_CONSOLE_URL = 'http://127.0.0.1:3100'
npm.cmd --prefix .\web run dev
```

PowerShell 窗口二启动查询工作台：

```powershell
$env:KB_ROOT = Join-Path $env:USERPROFILE 'GroundMap-UserData'
$env:KB_WORKSPACE = 'my-work'
$env:KB_API_BASE = 'http://127.0.0.1:3006'
npm.cmd --prefix .\tools\debug-console run dev
```

分别启动时，两个 PowerShell 窗口都要保持打开；以上排障命令只覆盖本地模式所需变量，不会读取 `test-kit/.env.local` 中的 Provider Key。需要联网问答时使用 `start.ps1`。日常使用也建议使用 `start.ps1`，避免遗漏环境变量。

## 二、确认或创建 workspace

如果尚未创建 workspace：

```powershell
$dataRoot = Join-Path $env:USERPROFILE 'GroundMap-UserData'
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
$env:KB_ROOT = $dataRoot
python .\scripts\k.py new-workspace my-work --json
```

然后编辑 `test-kit/.env.local`：

```dotenv
KB_ROOT=C:\Users\你的真实用户名\GroundMap-UserData
KB_WORKSPACE=my-work
```

保存后停止并重新启动 GroundMap。

如果新项目包含与现有内容完全不同的身份、保密边界或长期领域，应新建 workspace；如果只是同一用户的新科研课题、工程或商业项目，通常放在现有 workspace 的新项目目录即可。

## 三、把一个新项目 ingest 到现有 workspace

### 第1步：确定项目 ID

示例：

```text
satellite-ground-station
phd-dissertation
sensor-commercialization
```

项目 ID 确定后尽量不要修改，因为它会出现在目录、决策、执行记录和 Context Pack 中。

### 第2步：创建项目原件目录

```powershell
$dataRoot = Join-Path $env:USERPROFILE 'GroundMap-UserData'
$workspace = 'my-work'
$projectId = 'my-project'
$env:KB_ROOT = $dataRoot
$workspaceRoot = Join-Path $dataRoot "workspaces\$workspace"
$rawProject = Join-Path $workspaceRoot "raw\projects\$projectId"
New-Item -ItemType Directory -Force -Path $rawProject | Out-Null
$rawProject
```

最后一行会显示项目原件目录。通过文件资源管理器把 PDF、Word、PPT、Excel、图片、音频、Markdown 等文件复制进去。

原件规则：

- 只把来源文件放入 `raw`；
- 不要放 API Key、密码或私钥；
- ingest 后尽量不要重命名或移动原件；
- 不要覆盖同名旧文件。新版本应使用日期或版本号区分；
- 单位、客户或个人敏感资料必须先确认授权。

### 第3步：预览本次转换

```powershell
python .\scripts\convert.py --workspace $workspace --dry-run
```

确认待转换数量和文件名正确后继续。

### 第4步：执行增量转换

```powershell
python .\scripts\convert.py --workspace $workspace
```

系统会递归扫描整个 workspace 的 `raw`，但只处理新增或变化的文件。项目结果位于：

```text
workspaces\my-work\derived\projects\my-project\
```

每个来源通常生成：

- `*.md`：可检索正文；
- `*.outline.json`：章节和锚点；
- `*.source.json`：Source Manifest 和哈希；
- `*.quality.json`：质量状态和问题；
- `*.evidence.json`：页码、bbox、Sheet/range 等定位，适用时生成；
- `*.visual.json`、`*.assets` 或 `*.transcript.json`：图片、嵌入媒体或音频适用时生成。

不要手动修改 `derived`。

### 第5步：检查质量报告

```powershell
$qualityRoot = Join-Path $workspaceRoot "derived\projects\$projectId"
Get-ChildItem -LiteralPath $qualityRoot -Recurse -Filter '*.quality.json'
```

重要文件为 `degraded` 或 `failed` 时，先检查 OCR、音频、复杂表格或证据定位问题，不要直接把输出当作确认事实。

### 第6步：验证本地检索

```powershell
python .\scripts\k.py --workspace $workspace search "项目中的真实关键词" --json
```

也可以启动查询工作台，选择“仅本地”后提问。先使用原件中明确出现的术语、数字或文件名验证。

完成以上步骤后，技术 ingest `raw → derived` 已完成，文件内容已经可以被本地检索读取。

### 第7步：沉淀为长期 Wiki 和项目总控

长期使用还需要把重要内容整理到：

```text
wiki\sources\
wiki\concepts\
wiki\entities\
wiki\analyses\
projects\my-project\
```

可以让 Codex、Claude Code 或其他 Agent执行：

```text
请使用数据根 C:\Users\我的用户名\GroundMap-UserData，workspace 为 my-work，
项目 ID 为 my-project。新文件位于 raw/projects/my-project/。

请先检查 convert、Source Manifest 和 quality report，然后按 outline 分段读取 derived；
创建带块级来源引用的 wiki/sources 摘要，更新相关 concepts/entities/analyses/root_index；
在 projects/my-project/ 下建立 brief.md、state.md、decisions/ 和 progress/；
所有 Agent 写入保持 status: draft、last_modified_by: LLM；
保留冲突、未知和低置信度内容；最后运行 health、list-broken-refs、
list-source-issues 和 list-coarse-citations，并列出需要人工确认的内容。
```

项目总控最小结构：

```text
projects\my-project\
├─ brief.md
├─ state.md
├─ decisions\
├─ progress\
└─ context.md
```

人工审核后，可生成 Context Pack：

```powershell
python .\scripts\k.py --workspace $workspace project-list --json
python .\scripts\k.py --workspace $workspace project-show $projectId --json
python .\scripts\k.py --workspace $workspace context-build $projectId --json
```

### 第8步：执行验收

```powershell
python .\scripts\k.py --workspace $workspace health --json
python .\scripts\k.py --workspace $workspace list-broken-refs --json
python .\scripts\k.py --workspace $workspace list-source-issues --json
python .\scripts\k.py --workspace $workspace list-coarse-citations --json
```

重要事实还应回到原件人工核对。命令成功只代表程序完成，不代表所有内容都准确。

## 四、撤出一份指定的已上传文件

GroundMap 默认把 `raw` 当作不可变证据。只有在文件传错、重复、无授权、涉及隐私或用户明确要求删除时，才执行撤出。

不要直接使用模糊通配符删除。推荐先把指定原件和派生结果移动到数据根的 `_removed` 隔离区；确认没有误删后，再通过文件资源管理器决定是否永久删除。

### 第1步：停止服务并备份

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\test-kit\stop.ps1
```

先备份整个数据根，或至少备份目标 workspace。

### 第2步：填写精确的来源路径

示例要撤出：

```text
raw\projects\my-project\report.pdf
```

执行以下 PowerShell。只修改 `$sourceRelative`：

```powershell
$dataRoot = Join-Path $env:USERPROFILE 'GroundMap-UserData'
$workspace = 'my-work'
$sourceRelative = 'raw\projects\my-project\report.pdf'
$workspaceRoot = Join-Path $dataRoot "workspaces\$workspace"
$sourcePath = Join-Path $workspaceRoot $sourceRelative

if (-not $sourceRelative.StartsWith('raw\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'sourceRelative 必须是 raw 下的相对路径，操作已停止。'
}

$resolvedWorkspace = (Resolve-Path -LiteralPath $workspaceRoot).Path.TrimEnd('\')
$resolvedSource = (Resolve-Path -LiteralPath $sourcePath).Path
if (-not $resolvedSource.StartsWith($resolvedWorkspace + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw '目标文件不在指定 workspace 内，操作已停止。'
}

Get-Item -LiteralPath $resolvedSource | Format-List FullName,Length,LastWriteTime
Get-FileHash -LiteralPath $resolvedSource -Algorithm SHA256
```

核对输出必须是准备撤出的那个文件。如果文件不对，停止操作。

### 第3步：移动原件到隔离区

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$quarantineRoot = Join-Path $dataRoot "_removed\$stamp\$workspace"
$sourceDestination = Join-Path $quarantineRoot $sourceRelative
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $sourceDestination) | Out-Null
Move-Item -LiteralPath $resolvedSource -Destination $sourceDestination
```

原件已经离开活动 workspace，但仍可恢复。

### 第4步：移动对应派生结果

```powershell
$relativeBelowRaw = $sourceRelative.Substring(4).TrimStart('\')
$relativeParent = Split-Path -Parent $relativeBelowRaw
$sourceStem = [IO.Path]::GetFileNameWithoutExtension($relativeBelowRaw)
$derivedRelativeDir = if ($relativeParent) { Join-Path 'derived' $relativeParent } else { 'derived' }
$derivedDir = Join-Path $workspaceRoot $derivedRelativeDir
$derivedDestination = Join-Path $quarantineRoot $derivedRelativeDir

$derivedItems = @()
if (Test-Path -LiteralPath $derivedDir) {
    $derivedItems = @(Get-ChildItem -LiteralPath $derivedDir -Force | Where-Object {
        $_.Name -eq $sourceStem -or $_.Name.StartsWith($sourceStem + '.', [StringComparison]::OrdinalIgnoreCase)
    })
}

$derivedItems | Select-Object FullName
```

先核对列表只包含目标来源对应的 `.md`、JSON、assets 等派生项。确认后执行：

```powershell
if ($derivedItems.Count -gt 0) {
    New-Item -ItemType Directory -Force -Path $derivedDestination | Out-Null
    foreach ($item in $derivedItems) {
        Move-Item -LiteralPath $item.FullName -Destination $derivedDestination
    }
}
```

### 第5步：查找 Wiki 和项目引用

```powershell
$referenceText = $sourceRelative.Replace('\','/')
Get-ChildItem -LiteralPath $workspaceRoot -Recurse -Filter '*.md' | Select-String -SimpleMatch $referenceText
```

逐条人工判断：

- 误传、隐私或无授权文件：移除其摘要、引用及从中提取的敏感事实；
- 合法撤回但历史判断仍需保留：保留历史说明，标明来源已撤出和日期，不再保留失效链接；
- 不确定时不要批量替换，先让数据负责人审核。

### 第6步：重新检查

```powershell
$env:KB_ROOT = $dataRoot
python .\scripts\convert.py --workspace $workspace --dry-run
python .\scripts\k.py --workspace $workspace list-broken-refs --json
python .\scripts\k.py --workspace $workspace list-source-issues --json
python .\scripts\k.py --workspace $workspace health --json
```

确认活动库无残留引用后再启动服务。隔离内容建议保留到内部删除确认完成；需要永久删除时，在文件资源管理器中精确打开 `_removed/<时间>/<workspace>`，再次核对后处理。

## 五、撤出一个项目总控记录

项目总控目录和项目来源文件是两类内容：

- `projects/my-project/`：状态、决策、执行记录、Context Pack；
- `raw/projects/my-project/`：上传原件；
- `derived/projects/my-project/`：可重建派生文件；
- `wiki/**`：可能引用该项目或其来源的长期知识。

只撤出项目总控记录不会自动删除原件和 Wiki。

先列出目标：

```powershell
$dataRoot = Join-Path $env:USERPROFILE 'GroundMap-UserData'
$workspace = 'my-work'
$projectId = 'my-project'
$workspaceRoot = Join-Path $dataRoot "workspaces\$workspace"
$projectPath = Join-Path $workspaceRoot "projects\$projectId"
$resolvedWorkspace = (Resolve-Path -LiteralPath $workspaceRoot).Path.TrimEnd('\')
$resolvedProject = (Resolve-Path -LiteralPath $projectPath).Path

if (-not $resolvedProject.StartsWith($resolvedWorkspace + '\projects\', [StringComparison]::OrdinalIgnoreCase)) {
    throw '目标不是当前 workspace 下的项目目录，操作已停止。'
}

Get-ChildItem -LiteralPath $resolvedProject -Recurse | Select-Object FullName
```

确认后移动到隔离区：

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$projectQuarantine = Join-Path $dataRoot "_removed\$stamp\$workspace\projects"
New-Item -ItemType Directory -Force -Path $projectQuarantine | Out-Null
Move-Item -LiteralPath $resolvedProject -Destination $projectQuarantine
```

检查其他 Markdown 是否仍引用项目 ID：

```powershell
Get-ChildItem -LiteralPath $workspaceRoot -Recurse -Filter '*.md' | Select-String -SimpleMatch $projectId
python .\scripts\k.py --workspace $workspace project-list --json
python .\scripts\k.py --workspace $workspace health --json
```

如果要求“删除整个项目及其上传文件”，还必须按上一节分别撤出 `raw/projects/<projectId>` 对应的每个来源及其派生结果，并审核 Wiki 引用。不要因为删除了 `projects/<projectId>` 就假定原始资料也已经删除。

## 六、撤出整个 workspace

这会让该知识库从活动列表消失，影响范围最大。先停止服务、完成备份，并确认 `.env.local` 后续将切换到另一个 workspace。

```powershell
$dataRoot = Join-Path $env:USERPROFILE 'GroundMap-UserData'
$workspace = 'my-work'
$workspacePath = Join-Path $dataRoot "workspaces\$workspace"
$workspacesRoot = (Resolve-Path -LiteralPath (Join-Path $dataRoot 'workspaces')).Path.TrimEnd('\')
$resolvedWorkspace = (Resolve-Path -LiteralPath $workspacePath).Path

if (-not $resolvedWorkspace.StartsWith($workspacesRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw '目标不在 workspaces 目录内，操作已停止。'
}

Get-ChildItem -LiteralPath $resolvedWorkspace -Force | Select-Object Name,FullName
```

确认后移动到隔离区：

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$workspaceQuarantine = Join-Path $dataRoot "_removed\$stamp\workspaces"
New-Item -ItemType Directory -Force -Path $workspaceQuarantine | Out-Null
Move-Item -LiteralPath $resolvedWorkspace -Destination $workspaceQuarantine
```

然后修改 `test-kit/.env.local` 的 `KB_WORKSPACE`，指向仍然存在的 workspace，再启动 GroundMap。

## 七、删除后的恢复

在没有永久删除 `_removed` 前，可以恢复：

1. 停止 GroundMap；
2. 找到 `_removed/<时间>/<workspace>/` 下的原件、派生项或项目目录；
3. 核对目标活动目录不存在同名内容；
4. 使用文件资源管理器将内容移回原位置；
5. 运行 `convert.py --dry-run`、`list-broken-refs` 和 `health`；
6. 重新启动并验证查询。

如活动目录已经出现同名新内容，不要直接覆盖；先让维护者比较版本和哈希。

## 八、最短命令速查

```powershell
# 选择数据根和 workspace
$env:KB_ROOT = Join-Path $env:USERPROFILE 'GroundMap-UserData'
$workspace = 'my-work'

# 盘点和增量 ingest
python .\scripts\convert.py --workspace $workspace --dry-run
python .\scripts\convert.py --workspace $workspace

# 查询和健康检查
python .\scripts\k.py --workspace $workspace search "关键词" --json
python .\scripts\k.py --workspace $workspace health --json
python .\scripts\k.py --workspace $workspace list-broken-refs --json

# 启动和停止
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\test-kit\start.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\test-kit\stop.ps1
```

执行任何撤出操作前，始终先停止服务、备份、显示完整路径和 SHA256，并只操作已经人工核对的精确目标。
