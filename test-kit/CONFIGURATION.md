# 配置步骤

## 1. 机器要求

- Windows 10 或 11，64 位
- PowerShell 5.1 或更高版本
- Git 2.40 或更高版本
- Python 3.11 至 3.13
- Node.js 20 或更新的 LTS 版本
- 至少 3 GB 可用磁盘空间
- 如需联网问答，可访问所选模型供应商 API

推荐直接双击压缩包根目录的 `GroundMap.cmd`。脚本会优先使用 Windows 自带的 `winget` 自动安装缺失的 Git、Python 和 Node.js；安装过程可能弹出系统管理员授权。若电脑没有 `winget`，脚本会停止并提示手动安装缺少的项目，不会从非官方站点下载安装包。

在 PowerShell 中执行以下命令确认版本：

```powershell
git --version
python --version
node --version
npm --version
```

## 2. 首次初始化

双击压缩包根目录的 `GroundMap.cmd`。首次运行会：

1. 检查 Git、Python、Node.js 和 npm，并在 `winget` 可用时自动补齐；
2. 安装 GroundMap Python 基础依赖、图片 OCR 依赖和音频转写依赖；
3. 下载并缓存默认的 faster-whisper `small` 模型；
4. 安装两个 Web 子项目的 Node.js 依赖；
5. 从虚构 `raw/` 样本生成 `derived/`；
6. 在 `demo-data` 内创建独立 Git 仓库并提交初始快照；
7. 运行 Python 健康检查和 Web 单元测试；
8. 创建桌面快捷方式并打开网页。

如果公司网络阻止 npm 或 pip 下载，请让内部 IT 提供代理或离线镜像后重试。不要从不明网盘下载依赖压缩包。

语音模型下载失败不会阻止基础知识库完成初始化；此时文字、文档和图片功能仍可测试。网络恢复后删除 `test-kit/.setup-complete`，再运行 `01-FIRST-TIME-SETUP.cmd` 重试完整配置。

## 3. 配置问答模型

首次初始化会从 `.env.example` 创建 `.env.local`。使用记事本打开：

```text
test-kit\.env.local
```

只测试知识管理功能时，所有 API Key 可以留空。要测试 DeepSeek 本地问答和联网补充，填写：

```dotenv
DEEPSEEK_API_KEY=你的真实Key
WEB_SEARCH_MODEL=deepseek-v4-flash
```

也可以按需填写：

```dotenv
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OPENAI_BASE_URL=
```

注意：

- 不要给值加引号。
- 一行只放一个变量。
- 修改后必须停止并重新启动 GroundMap。
- `.env.local` 不会被打包脚本包含，也不应提交到 Git。
- 未配置 `DEEPSEEK_API_KEY` 时，“联网搜索”按钮会禁用，这是预期行为。

## 4. 启动与停止

双击 `02-START-GROUNDMAP.cmd`。成功后会打开查询控制台，并在 `test-kit/.runtime/` 记录进程与日志。

如浏览器未自动打开，手动访问：

- http://127.0.0.1:3006
- http://127.0.0.1:3100/?ws=groundmap-demo

双击 `03-STOP-GROUNDMAP.cmd` 停止本测试包启动的两个本地服务。

## 5. 可选配置

`.env.local` 支持以下变量：

| 变量 | 默认值 | 用途 |
|---|---|---|
| `KB_ROOT` | `test-kit/demo-data` | 包含 `workspaces/` 的数据根 |
| `KB_WORKSPACE` | `groundmap-demo` | 默认 workspace |
| `KB_API_BASE` | `http://127.0.0.1:3006` | 管理台 API 地址 |
| `NEXT_PUBLIC_KB_URL` | `http://127.0.0.1:3006` | 调试工作台“知识库”按钮的目标地址 |
| `NEXT_PUBLIC_CONSOLE_URL` | `http://127.0.0.1:3100` | 管理台里的查询控制台入口 |
| `DEEPSEEK_API_KEY` | 空 | DeepSeek 问答与 Web Search |
| `WEB_SEARCH_MODEL` | `deepseek-v4-flash` | Web Search 模型 |
| `ANTHROPIC_API_KEY` | 空 | Anthropic provider |
| `OPENAI_API_KEY` | 空 | OpenAI 或兼容 provider |
| `OPENAI_BASE_URL` | 空 | OpenAI 兼容端点 |
| `KB_WHISPER_MODEL` | `small` | faster-whisper 模型名称 |
| `KB_WHISPER_DEVICE` | `cpu` | 音频推理设备；测试包默认不要求显卡 |
| `KB_WHISPER_COMPUTE_TYPE` | `int8` | CPU 推理精度与内存配置 |
| `KB_WHISPER_LANGUAGE` | `zh` | 默认转写语言 |
| `KB_WHISPER_CHUNK_SEC` | `600` | 长音频分段秒数 |

内部测试阶段建议保留默认 `KB_ROOT` 和端口。若确需测试另一份数据，先停止服务，将 `KB_ROOT` 改为该数据根的绝对路径，并确保目录内含 `workspaces/<workspace-name>/`。

## 6. 常见问题

### 端口被占用

先运行 `03-STOP-GROUNDMAP.cmd`。如果仍报错，在 PowerShell 中查看：

```powershell
Get-NetTCPConnection -LocalPort 3006,3100 -ErrorAction SilentlyContinue
```

关闭占用程序后重试。当前测试包固定使用 3006 和 3100 端口。

### 联网按钮不可点击

检查 `.env.local` 中是否填写 `DEEPSEEK_API_KEY`，然后完全停止并重启服务。联网模式依赖 DeepSeek Responses API 的 Web Search 能力。

### 启动后没有结果

查看：

```text
test-kit\.runtime\web.err.log
test-kit\.runtime\console.err.log
```

先确认两个地址都能打开，再按错误信息检查 Python、Node.js 或 API Key。

### 自动安装提示没有 winget

部分精简版 Windows 或受企业策略管理的电脑没有 Windows Package Manager。请让内部 IT 从官方渠道安装 Python 3.11-3.13、Node.js LTS 和 Git for Windows，重启终端后再次双击启动文件。核心应用不会绕过组织的软件安装策略。

### 音频无法转写

打开 `test-kit/.setup-complete`，确认 `audioModelStatus` 为 `ready`。若为 `download_failed`，检查是否能访问模型仓库，然后删除该标记文件并重新运行首次配置。默认 `small` 模型适合 CPU 内部测试；首次下载时间和磁盘占用会明显高于普通 Python 依赖。

初始化时若看到 pydub 关于系统 FFmpeg 的警告，但健康检查仍通过，可以忽略。GroundMap 的本地 faster-whisper 转写路径使用随依赖安装的 PyAV 读取音频，不要求测试者另装 FFmpeg。

### 重新生成演示派生文件

在项目根目录运行：

```powershell
$env:KB_ROOT = "$PWD\test-kit\demo-data"
python scripts\convert.py --workspace groundmap-demo --force
python scripts\k.py --workspace groundmap-demo health --json
```
