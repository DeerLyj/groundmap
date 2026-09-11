import Link from "next/link";
import { PageRenderer } from "@/components/PageRenderer";
import { runKCli } from "@/lib/k-cli";
import { getServerLocale } from "@/lib/server-locale";
import { t } from "@/lib/i18n";
import { ProjectConfirmButton } from "./ProjectConfirmButton";
import { DeliverableConfirmButton } from "./DeliverableConfirmButton";

export const dynamic = "force-dynamic";

interface ProjectSummary {
  project_id: string;
  status: string;
  updated_at: string;
  next_action: string;
  decision_count: number;
  execution_count: number;
  control_loop?: { complete: boolean } | null;
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
  executions: Array<{
    execution_id: string;
    title: string;
    recorded_at: string;
    confirmed: boolean;
    content: string;
  }>;
  control_loop: {
    complete: boolean;
    missing: string[];
  };
}

interface DeliverableVersion {
  path: string;
  title: string;
  deliverable_id: string;
  kind: string;
  project_id: string;
  version: number;
  status: string;
  reviewed: boolean;
  source_refs: string[];
  content: string;
  valid: boolean;
  errors: string[];
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
  const deliverablesResult = selectedId
    ? await runKCli<DeliverableVersion[]>([
        "deliverable-list",
        "--project-id",
        selectedId,
      ])
    : null;
  const detail = detailResult?.ok ? detailResult.data : null;
  const context = contextResult?.ok ? contextResult.data : null;
  const deliverables = deliverablesResult?.ok && Array.isArray(deliverablesResult.data)
    ? deliverablesResult.data
    : [];

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
                  {" · "}
                  {t("projects.executions", locale, { n: project.execution_count })}
                </div>
                <div className="mt-1 text-xs">
                  {project.control_loop?.complete
                    ? t("projects.control_complete", locale)
                    : t("projects.control_incomplete", locale)}
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
                <h3 className="font-medium">
                  {t("projects.deliverables", locale, { n: deliverables.length })}
                </h3>
                {deliverables.length === 0 ? (
                  <p className="mt-3 text-sm text-muted-foreground">
                    {t("projects.no_deliverables", locale)}
                  </p>
                ) : (
                  <div className="mt-3 space-y-3">
                    {deliverables.map((deliverable) => (
                      <details key={deliverable.path} className="rounded border p-3">
                        <summary className="cursor-pointer">
                          <span className="font-medium">{deliverable.title}</span>
                          <span className="ml-2 text-xs text-muted-foreground">
                            v{String(deliverable.version).padStart(3, "0")}
                            {" · "}
                            {deliverable.kind}
                            {" · "}
                            {deliverable.reviewed
                              ? t("projects.deliverable_reviewed", locale)
                              : t("projects.deliverable_draft", locale)}
                          </span>
                        </summary>
                        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                          <span>
                            {t("projects.deliverable_sources", locale, {
                              n: deliverable.source_refs.length,
                            })}
                          </span>
                          {!deliverable.reviewed && deliverable.valid && (
                            <DeliverableConfirmButton
                              projectId={detail.project.project_id}
                              deliverableId={deliverable.deliverable_id}
                              version={deliverable.version}
                            />
                          )}
                        </div>
                        {deliverable.errors.map((error) => (
                          <p key={error} className="mt-2 text-xs text-destructive">{error}</p>
                        ))}
                        <div className="mt-3 border-t pt-3">
                          <PageRenderer content={deliverable.content} sourcePath={deliverable.path} />
                        </div>
                      </details>
                    ))}
                  </div>
                )}
              </div>
              <div className="mt-6 border-t pt-5">
                <h3 className="font-medium">
                  {t("projects.executions", locale, { n: detail.executions.length })}
                </h3>
                {detail.executions.length === 0 ? (
                  <p className="mt-3 text-sm text-muted-foreground">
                    {t("projects.no_executions", locale)}
                  </p>
                ) : (
                  <div className="mt-3 space-y-3">
                    {detail.executions.map((execution) => (
                      <article key={execution.execution_id} className="rounded border p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-medium">{execution.title}</span>
                          <span className="text-xs text-muted-foreground">
                            {execution.recorded_at}
                            {" · "}
                            {execution.confirmed
                              ? t("projects.execution_confirmed", locale)
                              : t("projects.execution_pending", locale)}
                            {!execution.confirmed && (
                              <span className="ml-2">
                                <ProjectConfirmButton
                                  projectId={detail.project.project_id}
                                  target="execution"
                                  executionId={execution.execution_id}
                                />
                              </span>
                            )}
                          </span>
                        </div>
                        <div className="mt-3">
                          <PageRenderer content={execution.content} />
                        </div>
                      </article>
                    ))}
                  </div>
                )}
                <p className="mt-3 text-xs">
                  {detail.control_loop.complete
                    ? t("projects.control_complete", locale)
                    : t("projects.control_incomplete", locale)}
                </p>
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
