/**
 * KB 工具注册表 — 单一 source of truth
 *
 * 每个工具的 name / description / JSON schema 在此定义一次，
 * 然后导出两种格式供不同 provider 使用：
 *   - getOpenAITools()      → OpenAI function calling 格式（DeepSeek/Moonshot/...）
 *   - listToolNames()       → 仅名字列表（给 Claude Code / Codex 桥接展示用）
 *
 * 工具集合对齐 web/app/api/agent-tool/route.ts 的白名单。
 * 新增工具时两处必须同步改。
 */

export interface KbTool {
  name: string;
  description: string;
  /** JSON Schema (draft-07 子集) 描述参数 */
  input_schema: {
    type: "object";
    properties: Record<string, unknown>;
    required?: string[];
  };
}

const PATH_DESCRIPTION =
  "知识库相对路径，必须落在 wiki/、raw/ 或 derived/ 下（如 derived/papers/example.md）";

export const KB_TOOLS: KbTool[] = [
  {
    name: "search",
    description:
      "跨 wiki/ 关键词搜索（标题×5 + 正文×1 权重）。返回命中页面列表，含 path / title / snippet / score。",
    input_schema: {
      type: "object",
      properties: {
        query: { type: "string", description: "搜索关键词" },
        limit: {
          type: "integer",
          description: "返回结果数上限，默认 20",
          minimum: 1,
          maximum: 100,
        },
      },
      required: ["query"],
    },
  },
  {
    name: "read_page",
    description:
      "读取一个 wiki/ 页面的完整内容（frontmatter + 正文）。最常用——读 root_index、子索引、具体概念页都用这个。",
    input_schema: {
      type: "object",
      properties: {
        path: { type: "string", description: PATH_DESCRIPTION },
      },
      required: ["path"],
    },
  },
  {
    name: "outline",
    description:
      "返回文档的章节大纲树（H1-H6 + 段落预览 + agent_summary）。**先 outline 再 read_section** 是标准节奏。",
    input_schema: {
      type: "object",
      properties: {
        path: { type: "string", description: PATH_DESCRIPTION },
      },
      required: ["path"],
    },
  },
  {
    name: "read_section",
    description:
      "按 anchor (如 'h-2-3-a3f2c1') 读取整个 H2/H3 段。常用于精确读 derived/papers 或 derived/articles 的某一节。",
    input_schema: {
      type: "object",
      properties: {
        path: { type: "string", description: PATH_DESCRIPTION },
        anchor: {
          type: "string",
          description: "段落 anchor，形如 h-2-3-a3f2c1（从 outline 拿到）",
        },
      },
      required: ["path", "anchor"],
    },
  },
  {
    name: "read_block",
    description:
      "按 anchor (如 'p-12-7d8e9a') 读取单个块原文（段落 / 列表 / 表格 / 代码块）。比 read_section 更精确，适合 audit 模式校验某条引用。",
    input_schema: {
      type: "object",
      properties: {
        path: { type: "string", description: PATH_DESCRIPTION },
        anchor: {
          type: "string",
          description: "块 anchor，形如 p-12-7d8e9a / t-3-... / c-1-...",
        },
      },
      required: ["path", "anchor"],
    },
  },
  {
    name: "blocks",
    description:
      "列出文档所有 block 的索引（每块的 anchor / 类型 / 所属章节 / 120 字预览）。用于了解文档结构。",
    input_schema: {
      type: "object",
      properties: {
        path: { type: "string", description: PATH_DESCRIPTION },
      },
      required: ["path"],
    },
  },
  {
    name: "find_anchor",
    description: "在指定文档中根据文本片段反查 anchor。当只记得段落大意但忘了 anchor 时用。",
    input_schema: {
      type: "object",
      properties: {
        path: { type: "string", description: PATH_DESCRIPTION },
        snippet: { type: "string", description: "要查找的文本片段（最多 500 字符）" },
        limit: { type: "integer", description: "返回数上限，默认 10", minimum: 1, maximum: 100 },
      },
      required: ["path", "snippet"],
    },
  },
  {
    name: "backlinks",
    description:
      "查询某 wiki 页的反向链接（谁链接到此页 + 上下文 + 行号）。顺藤摸瓜定位相关讨论的必备工具。",
    input_schema: {
      type: "object",
      properties: {
        path: { type: "string", description: PATH_DESCRIPTION },
      },
      required: ["path"],
    },
  },
  {
    name: "outlinks",
    description: "查询某 wiki 页的出向链接（此页链到哪 + alias + 行号）。常和 backlinks 配对使用。",
    input_schema: {
      type: "object",
      properties: {
        path: { type: "string", description: PATH_DESCRIPTION },
      },
      required: ["path"],
    },
  },
  {
    name: "list_pages",
    description:
      "按 frontmatter 过滤 Wiki Markdown 页面列表。可选过滤：type / status / confidence / tag / modified_by。无参数 = 列全部；不能据此判断 raw/ 下是否存在未转换的原始文件。",
    input_schema: {
      type: "object",
      properties: {
        type: { type: "string", description: "页面类型：entity / concept / source_summary / analysis / comparison / index / memory" },
        status: { type: "string", description: "状态：draft / reviewed / deprecated" },
        confidence: { type: "string", description: "置信度：high / medium / low" },
        tag: { type: "string", description: "标签精确匹配（如 stub / to-be-updated）" },
        modified_by: { type: "string", description: "LLM / Human" },
      },
    },
  },
  {
    name: "list_orphans",
    description: "列出无入链的孤儿页面（除 root_index 外没人引用）。",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "list_conflicts",
    description: "列出带 [!CONFLICT] 标注的页面（知识库中悬而未决的矛盾）。",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "list_to_update",
    description: "列出带 #to-be-updated 标签的页面（懒标记积压）。",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "list_broken_refs",
    description: "扫描 wiki/ 中所有失效的 raw/derived 块级引用。",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "list_source_issues",
    description:
      "扫描 source_count 与 sources 数组不一致 / 论断页无 source 也无 #to-be-updated 等问题。",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "health",
    description: "综合健康度报告：总页数、各类型计数、孤儿 / 冲突 / 失效引用统计。",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "list_projects",
    description:
      "列出当前知识库中的项目状态摘要。项目状态是工作上下文，不等于已确认的个人记忆。",
    input_schema: {
      type: "object",
      properties: {
        status: { type: "string", description: "可选：active / paused / blocked / completed / archived" },
      },
    },
  },
  {
    name: "show_project",
    description:
      "读取一个项目的 State、Brief 和 Decision Record 摘要；未被 Human 确认的内容必须保留其未确认状态。",
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "string", description: "项目 ID，如 china-bangladesh-ground-station" },
      },
      required: ["project_id"],
    },
  },
  {
    name: "context_pack",
    description:
      "生成并返回一个项目的最小 Context Pack，用于当前对话上下文；不会自动确认、写入或激活任何状态。",
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "string", description: "项目 ID" },
        max_chars: { type: "integer", description: "上下文长度上限，默认 30000", minimum: 1000, maximum: 100000 },
      },
      required: ["project_id"],
    },
  },
];

const KB_TOOLS_BY_NAME = new Map(KB_TOOLS.map((t) => [t.name, t]));

export function getTool(name: string): KbTool | undefined {
  return KB_TOOLS_BY_NAME.get(name);
}

export function listToolNames(): string[] {
  return KB_TOOLS.map((t) => t.name);
}

/** OpenAI function calling 格式（DeepSeek / OpenAI / Moonshot 等通用）*/
export function getOpenAITools() {
  return KB_TOOLS.map((t) => ({
    type: "function" as const,
    function: {
      name: t.name,
      description: t.description,
      parameters: t.input_schema,
    },
  }));
}
