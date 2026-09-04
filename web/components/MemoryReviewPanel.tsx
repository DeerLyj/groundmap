"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useT } from "@/lib/i18n-client";
import type { MemoryRecord } from "@/lib/memory";

export function MemoryReviewPanel({ records }: { records: MemoryRecord[] }) {
  const t = useT();
  const router = useRouter();
  const [busyPath, setBusyPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const candidates = records.filter((record) => record.memory_state === "candidate");
  const confirmed = records.filter((record) => record.memory_state === "confirmed");
  const rejected = records.filter((record) => record.memory_state === "rejected");

  async function transition(record: MemoryRecord, action: "confirm" | "reject") {
    if (busyPath) return;
    setBusyPath(record.path);
    setError(null);
    try {
      const response = await fetch("/api/memory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, path: record.path, user_confirmed: true }),
      });
      const data = (await response.json()) as { ok?: boolean; error?: string };
      if (!response.ok || data.ok !== true) {
        setError(t("memory.error", { error: data.error || "unknown" }));
        return;
      }
      router.refresh();
    } catch (e) {
      setError(t("memory.error", { error: e instanceof Error ? e.message : String(e) }));
    } finally {
      setBusyPath(null);
    }
  }

  return (
    <div className="space-y-8">
      <MemorySection
        title={t("memory.candidates")}
        empty={t("memory.empty_candidates")}
        records={candidates}
        busyPath={busyPath}
        onAction={transition}
        action="candidate"
        t={t}
      />
      <MemorySection
        title={t("memory.confirmed")}
        empty={t("memory.empty_confirmed")}
        records={confirmed}
        busyPath={busyPath}
        onAction={transition}
        action="confirmed"
        t={t}
      />
      {rejected.length > 0 && (
        <MemorySection
          title={t("memory.rejected")}
          empty=""
          records={rejected}
          busyPath={busyPath}
          onAction={transition}
          action="rejected"
          t={t}
        />
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

function MemorySection({
  title,
  empty,
  records,
  busyPath,
  onAction,
  action,
  t,
}: {
  title: string;
  empty: string;
  records: MemoryRecord[];
  busyPath: string | null;
  onAction: (record: MemoryRecord, action: "confirm" | "reject") => void;
  action: "candidate" | "confirmed" | "rejected";
  t: ReturnType<typeof useT>;
}) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-semibold">{title}</h2>
      {records.length === 0 ? (
        <p className="rounded-md border p-5 text-sm text-muted-foreground">{empty}</p>
      ) : (
        <div className="space-y-3">
          {records.map((record) => (
            <article key={record.path} className="rounded-md border p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <h3 className="font-semibold">{record.title}</h3>
                  <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
                    {record.content}
                  </p>
                </div>
                <span className="shrink-0 rounded border px-2 py-0.5 text-xs">
                  {action === "confirmed"
                    ? t("memory.confirmed_badge")
                    : action === "rejected"
                      ? t("memory.rejected_badge")
                      : t("status.draft")}
                </span>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                {t("memory.scope", { scope: record.scope || "—" })} · {t("memory.confidence", { confidence: record.confidence })}
              </p>
              <p className="mt-1 break-all font-mono text-[11px] text-muted-foreground">{record.path}</p>
              {action === "candidate" && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
                    disabled={busyPath !== null}
                    onClick={() => onAction(record, "confirm")}
                  >
                    {busyPath === record.path ? t("memory.processing") : t("memory.confirm")}
                  </button>
                  <button
                    className="rounded border px-3 py-1.5 text-sm disabled:opacity-50"
                    disabled={busyPath !== null}
                    onClick={() => onAction(record, "reject")}
                  >
                    {t("memory.reject")}
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
