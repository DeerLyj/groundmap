# GroundMap 内部单机测试包

本目录用于把 GroundMap 交给内部人员做单人、单机测试。包内数据全部是虚构合成数据，不包含私人数据仓库中的项目资料、个人经历、联系方式、账号或密钥。

完整的环境配置、自建知识库、文件 ingest、项目使用、备份和排障步骤见 [USER-GUIDE.zh-CN.md](USER-GUIDE.zh-CN.md)。

配置完成后的新项目 ingest、指定文件/项目撤出及启动命令见 [PROJECT-INGEST-OPERATIONS.zh-CN.md](PROJECT-INGEST-OPERATIONS.zh-CN.md)。

## 最短使用路径

1. 解压到仅测试者本人可访问的本地目录，路径建议只含英文和数字。
2. 在压缩包根目录双击 `GroundMap.cmd`。首次运行会自动配置环境、执行自检并打开浏览器；以后双击同一文件会直接启动。它等同于 `test-kit/00-INSTALL-AND-START.cmd`。
3. 如需模型问答，按 [CONFIGURATION.md](CONFIGURATION.md) 填写 `test-kit/.env.local` 后停止并重新启动。只测试本地知识库时可以不填 API Key。
5. 按 [TEST_PLAN.md](TEST_PLAN.md) 完成固定测试任务，将结果填写到 [FEEDBACK_TEMPLATE.md](FEEDBACK_TEMPLATE.md)。
6. 测试完成后双击 `03-STOP-GROUNDMAP.cmd`。

首次配置成功后，桌面还会创建 `GroundMap Internal Test` 快捷方式。`01-FIRST-TIME-SETUP.cmd` 和 `02-START-GROUNDMAP.cmd` 仍保留，供排障或分别执行配置与启动。

## 默认地址

- 知识库管理台：http://127.0.0.1:3006
- 查询控制台：http://127.0.0.1:3100/?ws=groundmap-demo

服务只监听测试者自己的电脑。此包没有登录、权限隔离或多人并发能力，不应用于公网，也不要放入真实敏感资料。

## 数据说明

默认数据根是 `test-kit/demo-data`，workspace 是 `groundmap-demo`。虚构项目名为“星港屋顶温室试点”，所有组织、人物、日期、预算和指标均为测试值。

样本覆盖：Markdown、DOCX、PPTX、XLSX、PDF 和 PNG。首次初始化会从 `raw/` 生成 `derived/`，并安装 OCR 与音频转写组件、准备默认的 `small` 语音模型。测试者可删除 `derived/` 后重新生成，但不要改动 `raw/`，这样才能验证原件不可变和可重复摄入。

首次运行需要联网下载运行时依赖和语音模型。安装完成后，日常启动和“仅本地”查询不需要联网；联网问答及首次处理尚未缓存的模型仍需要网络。

## 安全边界

- 每名测试者使用自己的本地副本，不共用数据目录。
- API Key 只写入 `test-kit/.env.local`，不要发到群聊、邮件或 Git。
- “仅本地”只查知识库；“联网搜索”先查本地，再强制调用 Web 补充。
- Web 结果只进入当前回答，不自动写入 Wiki。
- 需要导入真实资料时，先复制一份新数据根并完成组织内部授权；不要覆盖本演示库。

## 重新打包

项目维护者先复制敏感词模板并填写本机、私人数据仓和项目标识（每行一项）：

```powershell
Copy-Item .\test-kit\.sensitive-markers.example .\test-kit\.sensitive-markers.local
```

`.sensitive-markers.local` 已被 Git 忽略；缺少或内容为空时打包会直接失败。然后在 GroundMap 仓库根目录中运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\test-kit\package.ps1
```

输出位于 `dist/`。打包采用代码白名单，并排除密钥、私人数据、Git 历史、依赖和运行缓存。
