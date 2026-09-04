import { MemoryReviewPanel } from "@/components/MemoryReviewPanel";
import { getServerLocale } from "@/lib/server-locale";
import { t } from "@/lib/i18n";
import { listMemoryRecords } from "@/lib/memory";

export const dynamic = "force-dynamic";

export default async function MemoryPage() {
  const locale = getServerLocale();
  const records = await listMemoryRecords();
  return (
    <main className="mx-auto w-full max-w-5xl overflow-y-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">{t("memory.title", locale)}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
          {t("memory.desc", locale)}
        </p>
      </div>
      <MemoryReviewPanel records={records} />
    </main>
  );
}
