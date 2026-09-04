// Next.js 约定：app/icon.tsx 自动出 favicon，无需 favicon.ico 文件。
// 设计：暗底白字 "G"（GroundMap），32×32 浏览器 tab 图标。
export const size = { width: 32, height: 32 };
export const contentType = "image/svg+xml";

export default function Icon() {
  return new Response(
    '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><rect width="32" height="32" fill="#0f172a"/><text x="16" y="23" text-anchor="middle" fill="white" font-family="Arial,sans-serif" font-size="22" font-weight="700">G</text></svg>',
    { headers: { "Content-Type": contentType } },
  );
}
