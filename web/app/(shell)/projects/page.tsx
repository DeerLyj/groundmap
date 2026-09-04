import Link from "next/link";
import { PageRenderer } from "@/components/PageRenderer";
import { runKCli } from "@/lib/k-cli";
import { getServerLocale } from "@/lib/server-locale";
import { t } from "@/lib/i18n";
import { ProjectConfirmButton } from "./ProjectConfirmButton";

export const dynamic = "force-dynamic";

interface ProjectSummary {
  project_id: string;
  status: string;
  updated_at: string;
  next_action: string;
  decision_count: number;
  valid: boolean;
  errors: string[];
}

interface ProjectDetail {
  project: { project_id: string; context_path: string };
  brief?: { content: string } | null;
  state: { content: string; frontmatter: Record<string, unknown> };
  decisions: Array<{
    decision_id: string;
    title: string;
    decision_status: string;
    frontmatter: Record<string, unknown>;
    content: string;
  }>;
}

function isProjectId(value: string | undefined): value is string {
  return !!value && /^[a-z0-9][a-z0-9_-]*$/.test(value);
}

export default async function ProjectsPage({
  searchParams,
}: {
  searchParams?: { id?: string };
}) {
  const locale = getServerLocale();
  const listResult = await runKCli<ProjectSummary[]>(["project-list"]);
  const projects = listResult.ok && Array.isArray(listResult.data) ? listResult.data : [];
  const selectedId = isProjectId(searchParams?.id) ? searchParams.id : undefined;
  const detailResult = selectedId
    ? await runKCli<ProjectDetail>(["project-show", selectedId])
    : null;
  const contextResult = selectedId
    ? await runKCli<{ context: string; context_path: string }>([
        "context-build",
        selectedId,
        "--no-write",
      ])
    : null;
  const detail = detailResult?.ok ? detailResult.data : null;
  const context = contextResult?.ok ? contextResult.data : null;

  return (
    <main className="w-full overflow-auto p-6">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[20rem_minmax(0,1fr)]">
        <section>
          <h1 className="text-2xl font-bold">{t("projects.title", locale)}</h1>
          <p className="mt-2 text-sm text-muted-foreground">{t("projects.desc", locale)}</p>
          <div className="mt-6 space-y-2">
            {projects.length === 0 && (
              <p className="text-sm text-muted-foreground">{t("projects.empty", locale)}</p>
            )}
            {projects.map((project) => (
              <Link
                key={project.project_id}
                href={`/projects?id=${encodeURIComponent(project.project_id)}`}
                className={`block rounded border p-3 hover:bg-accent ${
                  project.project_id === selectedId ? "border-primary bg-accent" : ""
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{project.project_id}</span>
                  {!project.valid && <span className="text-xs text-destructive">{t("projects.invalid", locale)}</span>}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {t("projects.status", locale, { status: project.status || "—" })}
                  {" · "}
                  {t("projects.decisions", locale, { n: project.decision_count })}
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="min-w-0 rounded border p-5">
          {!detail && <p className="text-sm text-muted-foreground">{t("projects.empty", locale)}</p>}
          {detail && (
            <>
              <div className="mb-5 flex flex-wrap items-baseline justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold">{detail.project.project_id}</h2>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t("projects.status", locale, {
                      status: String(detail.state.frontmatter.status || "—"),
                    })}
                    {" · "}
                    {t("projects.updated", locale, {
                      date: String(detail.state.frontmatter.updated_at || "—"),
                    })}
                  </p>
                  <p className="mt-1 text-xs">
                    {detail.state.frontmatter.last_modified_by === "Human"
                      ? t("projects.state_confirmed", locale)
                      : t("projects.state_pending", locale)}
                  </p>
                </div>
                {detail.state.frontmatter.last_modified_by !== "Human" && (
                  <ProjectConfirmButton projectId={detail.project.project_id} target="state" />
                )}
                {context && (
                  <span className="text-xs text-muted-foreground">
                    {t("projects.context_ready", locale, { path: context.context_path })}
                  </span>
                )}
              </div>
              {detail.brief && <PageRenderer content={detail.brief.content} />}
              <div className="mt-6 border-t pt-5">
                <PageRenderer content={detail.state.content} />
              </div>
              <div className="mt-6 border-t pt-5">
                <h3 className="font-medium">{t("projects.decisions", locale, { n: detail.decisions.length })}</h3>
                <div className="mt-3 space-y-3">
                  {detail.decisions.map((decision) => {
                    const confirmed =
                      decision.frontmatter.last_modified_by === "Human" &&
                      ["reviewed", "executed"].includes(decision.decision_status);
                    const confirmStatus = ["reviewed", "executed"].includes(decision.decision_status)
                      ? decision.decision_status
                      : "reviewed";
                    return (
                      <article key={decision.decision_id} className="rounded border p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-medium">{decision.title}</span>
                          <span className="flex items-center gap-2 text-xs text-muted-foreground">
                            {decision.decision_status}
                            {confirmed ? (
                              <span>{t("projects.decision_confirmed", locale)}</span>
                            ) : decision.decision_status !== "deprecated" ? (
                              <ProjectConfirmButton
                                projectId={detail.project.project_id}
                                target="decision"
                                decisionId={decision.decision_id}
                                decisionStatus={confirmStatus}
                              />
                            ) : null}
                          </span>
                        </div>
                        <div className="mt-3">
                          <PageRenderer content={decision.content} />
                        </div>
                      </article>
                    );
                  })}
                </div>
              </div>
              {context && (
                <details className="mt-6 rounded border p-4" open>
                  <summary className="cursor-pointer font-medium">{t("projects.context", locale)}</summary>
                  <div className="mt-4">
                    <PageRenderer content={context.context} />
                  </div>
                </details>
              )}
            </>
          )}
        </section>
      </div>
    </main>
  );
}
