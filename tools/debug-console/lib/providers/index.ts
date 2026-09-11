/**
 * Provider registry — 集中创建实例 + 查询接口
 */
import type { Provider, ProviderId, ProviderInfo } from "./types";
import { makeDeepSeekProvider } from "./deepseek";
import { makeClaudeCodeProvider } from "./claude-code";
import { makeCodexProvider } from "./codex";
import { webSearchCapability } from "../hybrid-query";

let _registry: Map<ProviderId, Provider> | null = null;

function registry(): Map<ProviderId, Provider> {
  if (!_registry) {
    _registry = new Map<ProviderId, Provider>([
      ["deepseek", makeDeepSeekProvider()],
      ["claude-code", makeClaudeCodeProvider()],
      ["codex", makeCodexProvider()],
    ]);
  }
  return _registry;
}

export function getProvider(id: ProviderId): Provider | undefined {
  return registry().get(id);
}

export function listProviders(): ProviderInfo[] {
  const web = webSearchCapability();
  return Array.from(registry().values()).map((p) => {
    const available = p.isAvailable();
    return {
      id: p.id,
      name: p.name,
      available,
      unavailable_reason: p.unavailableReason(),
      models: p.listModels(),
      is_agent: p.is_agent,
      capabilities: {
        local_qa: available,
        hybrid_qa: available && web.available,
        hybrid_reason: available ? web.reason : p.unavailableReason(),
      },
    };
  });
}
