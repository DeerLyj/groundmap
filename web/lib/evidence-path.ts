const WORKSPACE_ASSET_PREFIXES = ["raw/", "derived/"] as const;

/** MIME types that the read-only asset endpoint may expose. */
export const ASSET_MIME_TYPES: Record<string, string> = {
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  gif: "image/gif",
  webp: "image/webp",
  bmp: "image/bmp",
  pdf: "application/pdf",
  mp3: "audio/mpeg",
  wav: "audio/wav",
  m4a: "audio/mp4",
  ogg: "audio/ogg",
  flac: "audio/flac",
  mp4: "video/mp4",
  webm: "video/webm",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
};

function extension(path: string): string {
  const name = path.split("/").at(-1) || "";
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(dot + 1).toLowerCase() : "";
}

export function isWorkspaceAssetPath(path: string): boolean {
  const normalized = path.replace(/\\/g, "/").replace(/^\.\/+/, "");
  return (
    WORKSPACE_ASSET_PREFIXES.some((prefix) => normalized.startsWith(prefix)) &&
    !normalized.split("/").includes("..") &&
    ASSET_MIME_TYPES[extension(normalized)] !== undefined
  );
}

export function assetMimeType(path: string): string | null {
  return ASSET_MIME_TYPES[extension(path)] || null;
}

export function encodeKbPath(path: string): string {
  return path.split("/").map(encodeURIComponent).join("/");
}

export function assetUrl(path: string): string {
  return `/api/assets/${encodeKbPath(path)}`;
}

export function evidenceHref(path: string, anchor?: string | null): string {
  const cleanAnchor = anchor?.replace(/^\^/, "") || "";
  const encoded = encodeKbPath(path);
  if (!cleanAnchor) return `/evidence/${encoded}`;
  const fragment = encodeURIComponent(cleanAnchor);
  return `/evidence/${encoded}?anchor=${fragment}#${fragment}`;
}

/** Resolve a Markdown image URL against its workspace-relative Markdown file. */
export function resolveMarkdownAssetPath(
  markdownPath: string | undefined,
  sourceUrl: string | undefined,
): string | null {
  if (!markdownPath || !sourceUrl) return null;
  let source = sourceUrl.trim().replace(/^<|>$/g, "").replace(/\\/g, "/");
  try {
    source = decodeURIComponent(source);
  } catch {
    // Keep malformed percent sequences unchanged; path validation below still applies.
  }
  if (!source || /^(?:[a-z][a-z0-9+.-]*:|\/)/i.test(source)) return null;

  const parts = source.startsWith("raw/") || source.startsWith("derived/")
    ? []
    : markdownPath.replace(/\\/g, "/").split("/").slice(0, -1);
  for (const part of source.split("/")) {
    if (!part || part === ".") continue;
    if (part === "..") {
      if (parts.length === 0) return null;
      parts.pop();
    } else {
      parts.push(part);
    }
  }
  const resolved = parts.join("/");
  return isWorkspaceAssetPath(resolved) ? resolved : null;
}

export function derivedMarkdownForRaw(rawPath: string): string | null {
  if (!rawPath.startsWith("raw/")) return null;
  const dot = rawPath.lastIndexOf(".");
  const stem = dot > rawPath.lastIndexOf("/") ? rawPath.slice(0, dot) : rawPath;
  return `derived/${stem.slice("raw/".length)}.md`;
}
