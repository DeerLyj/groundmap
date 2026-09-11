/* eslint-disable @next/next/no-img-element -- evidence images must use the original private asset URL. */
import Link from "next/link";
import { notFound } from "next/navigation";
import { PageRenderer } from "@/components/PageRenderer";
import { assetUrl } from "@/lib/evidence-path";
import { buildEvidenceView, type EvidenceLocator } from "@/lib/evidence";
import { getServerLocale } from "@/lib/server-locale";
import { t } from "@/lib/i18n";

export const dynamic = "force-dynamic";

function numberParam(value: string | undefined): number | undefined {
  if (value == null || value === "") return undefined;
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function explicitLocator(params: EvidencePageProps["searchParams"]): EvidenceLocator | null {
  const page = numberParam(params.page);
  const start = numberParam(params.start);
  const end = numberParam(params.end);
  const locator: EvidenceLocator = {};
  if (params.kind) locator.kind = params.kind;
  if (page !== undefined) locator.page = page;
  if (params.sheet) locator.sheet = params.sheet;
  if (params.range) locator.range = params.range;
  if (start !== undefined) locator.start = start;
  if (end !== undefined) locator.end = end;
  if (params.bbox) {
    try {
      const bbox = JSON.parse(params.bbox);
      if (Array.isArray(bbox)) locator.bbox = bbox;
    } catch {
      // Invalid optional bbox is ignored; path validation remains authoritative.
    }
  }
  return Object.keys(locator).length ? locator : null;
}

interface EvidencePageProps {
  params: { path: string[] };
  searchParams: {
    anchor?: string;
    kind?: string;
    page?: string;
    sheet?: string;
    range?: string;
    start?: string;
    end?: string;
    bbox?: string;
  };
}

export default async function EvidencePage({ params, searchParams }: EvidencePageProps) {
  let relPath: string;
  try {
    relPath = params.path.map((part) => decodeURIComponent(part)).join("/");
  } catch {
    notFound();
  }
  const view = await buildEvidenceView(relPath!, searchParams.anchor, explicitLocator(searchParams));
  if (!view) notFound();
  const locale = getServerLocale();
  const locator = view.locator;
  const originalUrl = view.originalPath ? assetUrl(view.originalPath) : null;
  const pdfPage = typeof locator?.page === "number" ? locator.page : 1;
  const start = typeof locator?.start === "number" ? locator.start : undefined;
  const end = typeof locator?.end === "number" ? locator.end : undefined;
  const timedUrl = originalUrl && start !== undefined
    ? `${originalUrl}#t=${start}${end !== undefined ? `,${end}` : ""}`
    : originalUrl;

  return (
    <main className="w-full overflow-auto p-6">
      <div className="mx-auto max-w-7xl space-y-5">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold">{t("evidence.title", locale)}</h1>
            <p className="mt-1 break-all font-mono text-xs text-muted-foreground">
              {view.originalPath || view.requestedPath}
            </p>
          </div>
          <Link href="/" className="text-sm text-primary hover:underline">
            ← {t("common.back", locale)}
          </Link>
        </header>

        {locator && (
          <div className="rounded border bg-muted/40 px-3 py-2">
            <div className="text-xs font-medium">{t("evidence.locator", locale)}</div>
            <code className="mt-1 block overflow-x-auto text-xs">
              {JSON.stringify(locator)}
            </code>
          </div>
        )}

        {originalUrl && (
          <section className="rounded border p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold">{t("evidence.original", locale)}</h2>
              <a
                href={originalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:underline"
              >
                {t("evidence.open_original", locale)}
              </a>
            </div>
            {view.mime?.startsWith("image/") && (
              <img
                src={originalUrl}
                alt={view.originalPath || view.requestedPath}
                className="mx-auto max-h-[75vh] max-w-full rounded border bg-white object-contain"
              />
            )}
            {view.mime === "application/pdf" && (
              <iframe
                src={`${originalUrl}#page=${pdfPage}`}
                title={view.originalPath || view.requestedPath}
                className="h-[75vh] w-full rounded border"
              />
            )}
            {view.mime?.startsWith("audio/") && (
              <audio controls preload="metadata" src={timedUrl || undefined} className="w-full" />
            )}
            {view.mime?.startsWith("video/") && (
              <video controls preload="metadata" src={timedUrl || undefined} className="max-h-[75vh] w-full" />
            )}
            {!view.mime?.startsWith("image/") &&
              view.mime !== "application/pdf" &&
              !view.mime?.startsWith("audio/") &&
              !view.mime?.startsWith("video/") && (
                <p className="text-sm text-muted-foreground">{t("evidence.download_hint", locale)}</p>
              )}
          </section>
        )}

        {view.content && view.markdownPath && (
          <section className="rounded border p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold">{t("evidence.extracted", locale)}</h2>
              <Link
                href={`/page/${view.markdownPath}${searchParams.anchor ? `#${encodeURIComponent(searchParams.anchor.replace(/^\^/, ""))}` : ""}`}
                className="text-sm text-primary hover:underline"
              >
                {t("evidence.open_page", locale)}
              </Link>
            </div>
            <PageRenderer content={view.content} sourcePath={view.markdownPath} />
          </section>
        )}
      </div>
    </main>
  );
}
