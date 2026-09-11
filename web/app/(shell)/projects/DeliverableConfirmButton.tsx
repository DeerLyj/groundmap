"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useT } from "@/lib/i18n-client";

interface Props {
  projectId: string;
  deliverableId: string;
  version: number;
}

export function DeliverableConfirmButton({ projectId, deliverableId, version }: Props) {
  const t = useT();
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function confirm() {
    if (!window.confirm(t("projects.deliverable_confirm_prompt"))) return;
    setBusy(true);
    try {
      const response = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "deliverable-confirm",
          project_id: projectId,
          deliverable_id: deliverableId,
          version,
        }),
      });
      if (!response.ok) throw new Error("deliverable_confirm_failed");
      router.refresh();
    } catch {
      window.alert(t("projects.confirm_failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={confirm}
      disabled={busy}
      className="rounded border px-2 py-1 text-xs hover:bg-accent disabled:opacity-50"
    >
      {busy ? t("projects.confirming") : t("projects.deliverable_confirm")}
    </button>
  );
}
