"use client";

/* eslint-disable react-hooks/set-state-in-effect */

import { ExternalLink, MessageSquare, PlayCircle, Send } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchIssues, fetchRepositories, investigateIssue, submitFeedback } from "@/services/system";
import type { Investigation, Issue, Repository } from "@/types/system";

export function InvestigationWorkspace() {
  const [repository, setRepository] = useState<Repository | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [selectedIssueId, setSelectedIssueId] = useState<number | null>(null);
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [status, setStatus] = useState("Loading synchronized issues");
  const [busy, setBusy] = useState(false);
  const [feedbackStatus, setFeedbackStatus] = useState("No feedback submitted");

  async function load() {
    const repos = await fetchRepositories();
    const repo = repos[0] ?? null;
    setRepository(repo);
    if (!repo) {
      setStatus("Connect and sync a repository first");
      return;
    }
    const loadedIssues = await fetchIssues(repo.id);
    setIssues(loadedIssues);
    setSelectedIssueId(loadedIssues[0]?.id ?? null);
    setStatus(loadedIssues.length ? "Issues loaded" : "No issues synchronized yet");
  }

  useEffect(() => {
    load().catch((error: Error) => setStatus(error.message));
  }, []);

  async function runInvestigation(issueId = selectedIssueId) {
    if (!issueId) return;
    setBusy(true);
    setStatus("Running multi-step investigation");
    try {
      const result = await investigateIssue(issueId);
      setInvestigation(result);
      setFeedbackStatus("No feedback submitted");
      setStatus("Investigation complete");
      if (repository) {
        setIssues(await fetchIssues(repository.id));
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Investigation failed");
    } finally {
      setBusy(false);
    }
  }

  async function sendFeedback(feedback_status: "CORRECT" | "INCORRECT" | "ADJUSTED") {
    if (!investigation) return;
    setFeedbackStatus("Submitting feedback");
    try {
      await submitFeedback(investigation.investigation_id, {
        target_type: "classification",
        original_value: investigation.classification.category,
        feedback_status,
        corrected_value: feedback_status === "CORRECT" ? investigation.classification.category : undefined,
        comment: `Maintainer marked classification as ${feedback_status}`
      });
      setFeedbackStatus(`Feedback recorded: ${feedback_status}`);
    } catch (error) {
      setFeedbackStatus(error instanceof Error ? error.message : "Unable to submit feedback");
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
      <section className="rounded-md border border-line bg-white p-4">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold">Issues</h1>
          <button onClick={() => selectedIssueId && runInvestigation(selectedIssueId)} disabled={!selectedIssueId || busy} className="inline-flex items-center gap-2 rounded-md bg-signal px-3 py-2 text-sm font-medium text-white disabled:opacity-50">
            <PlayCircle size={16} aria-hidden="true" />
            Investigate
          </button>
        </div>
        <p className="mt-2 text-sm text-slate-600">{status}</p>
        <div className="mt-4 max-h-[70vh] space-y-2 overflow-auto">
          {issues.map((issue) => (
            <button
              key={issue.id}
              onClick={() => setSelectedIssueId(issue.id)}
              className={`w-full rounded-md border p-3 text-left text-sm ${selectedIssueId === issue.id ? "border-signal bg-teal-50" : "border-line bg-white hover:bg-panel"}`}
            >
              <div className="font-semibold">#{issue.github_issue_number} {issue.title}</div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600">
                <span>{issue.state}</span>
                <span>{issue.classification ?? "UNANALYZED"}</span>
                <span>{issue.priority ?? "NO_PRIORITY"}</span>
                <span>{issue.escalation ?? "NO_ESCALATION"}</span>
              </div>
            </button>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        {investigation ? (
          <>
            <Panel title="GitHub Issue">
              <a href={investigation.issue.html_url} target="_blank" className="inline-flex items-center gap-2 text-sm font-semibold text-signal">
                #{investigation.issue.number} {investigation.issue.title}
                <ExternalLink size={15} aria-hidden="true" />
              </a>
              <p className="mt-3 text-sm text-slate-600">{investigation.summary}</p>
            </Panel>
            <div className="grid gap-4 md:grid-cols-3">
              <Panel title="Classification">
                <Strong>{investigation.classification.category}</Strong>
                <Small>confidence {investigation.classification.confidence.toFixed(2)}</Small>
              </Panel>
              <Panel title="Completeness">
                <Strong>{investigation.completeness.score}/100</Strong>
                <Small>{investigation.completeness.missing_information.join(", ") || "No major gaps"}</Small>
              </Panel>
              <Panel title="Priority">
                <Strong>{investigation.priority.level}</Strong>
                <Small>confidence {investigation.priority.confidence.toFixed(2)}</Small>
              </Panel>
            </div>
            <Panel title="Escalation Decision">
              <Strong>{investigation.escalation.decision}</Strong>
              <Small>{investigation.escalation.reason_codes.join(", ") || "No escalation reason codes"}</Small>
              <p className="mt-2 text-sm text-slate-600">{investigation.recommended_action}</p>
            </Panel>
            <div className="grid gap-4 lg:grid-cols-2">
              <Panel title="Duplicate Candidates">
                <div className="space-y-2">
                  {(investigation.duplicate_analysis?.duplicate_candidates ?? investigation.similar_issues).map((candidate) => (
                    <a key={candidate.candidate_issue_id} href={candidate.url} target="_blank" className="block rounded-md border border-line p-3 hover:bg-panel">
                      <div className="flex items-center justify-between gap-3 text-sm">
                        <span className="font-semibold">#{candidate.github_issue_number} {candidate.title}</span>
                        <span className="shrink-0 text-xs text-slate-600">{candidate.final_duplicate_score.toFixed(2)}</span>
                      </div>
                      <p className="mt-1 text-xs text-slate-600">{candidate.duplicate_state}: {candidate.why_similar}</p>
                    </a>
                  ))}
                  {!(investigation.duplicate_analysis?.duplicate_candidates.length ?? investigation.similar_issues.length) ? <Small>No duplicate candidates found</Small> : null}
                </div>
              </Panel>
              <Panel title="Security Signal">
                <Strong>{investigation.security_analysis?.security_state ?? "LOW_SECURITY_SIGNAL"}</Strong>
                <Small>confidence {(investigation.security_analysis?.confidence ?? 0).toFixed(2)}</Small>
                <p className="mt-2 text-sm text-slate-600">{investigation.security_analysis?.recommended_handling ?? "No special handling recommended."}</p>
              </Panel>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <Panel title="Release Regression">
                <Strong>{investigation.release_regression_analysis?.regression_state ?? "NO_RELEASE_CORRELATION"}</Strong>
                <p className="mt-2 text-sm text-slate-600">{investigation.release_regression_analysis?.explanation ?? "No release signal found."}</p>
              </Panel>
              <Panel title="Related Pull Requests">
                <div className="space-y-2">
                  {investigation.related_pull_requests.map((pr) => (
                    <a key={pr.number} href={pr.url} target="_blank" className="block rounded-md border border-line p-3 text-sm hover:bg-panel">
                      <span className="font-semibold">#{pr.number} {pr.title}</span>
                      <p className="mt-1 text-xs text-slate-600">{pr.why_relevant}</p>
                    </a>
                  ))}
                  {!investigation.related_pull_requests.length ? <Small>No related pull requests found</Small> : null}
                </div>
              </Panel>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <Panel title="Priority Signals">
                <Strong>{investigation.priority_analysis?.priority_score?.toFixed(2) ?? investigation.priority.confidence.toFixed(2)}</Strong>
                <Small>{(investigation.priority_analysis?.signals ?? investigation.priority.signals).join(", ") || "No strong signals"}</Small>
              </Panel>
              <Panel title="Operational Telemetry">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <Mini label="Steps" value={investigation.telemetry?.agent_steps ?? investigation.investigation_trace.length} />
                  <Mini label="Evidence" value={investigation.telemetry?.retrieved_evidence_sources ?? investigation.evidence.length} />
                  <Mini label="Duration ms" value={investigation.telemetry?.duration_ms ?? "--"} />
                  <Mini label="Status" value={investigation.telemetry?.final_status ?? "COMPLETED"} />
                </div>
              </Panel>
            </div>
            <Panel title="Human Feedback">
              <div className="flex flex-wrap items-center gap-2">
                <button onClick={() => sendFeedback("CORRECT")} className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium hover:bg-panel">
                  <Send size={15} aria-hidden="true" />
                  Correct
                </button>
                <button onClick={() => sendFeedback("INCORRECT")} className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium hover:bg-panel">
                  <MessageSquare size={15} aria-hidden="true" />
                  Incorrect
                </button>
                <button onClick={() => sendFeedback("ADJUSTED")} className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium hover:bg-panel">
                  <MessageSquare size={15} aria-hidden="true" />
                  Adjusted
                </button>
                <span className="text-sm text-slate-600">{feedbackStatus}</span>
              </div>
            </Panel>
            <Panel title="Evidence">
              <div className="space-y-2">
                {investigation.evidence.map((item) => (
                  <a key={`${item.source_type}-${item.title}-${item.github_number}`} href={item.source_url ?? "#"} target="_blank" className="block rounded-md border border-line p-3 hover:bg-panel">
                    <div className="text-sm font-semibold">{item.source_type} {item.github_number ? `#${item.github_number}` : ""}: {item.title}</div>
                    <p className="mt-1 text-xs text-slate-600">{item.why_relevant}</p>
                  </a>
                ))}
              </div>
            </Panel>
            <Panel title="Operational Timeline">
              <ol className="space-y-2">
                {investigation.investigation_trace.map((step) => (
                  <li key={step.step_number} className="rounded-md border border-line p-3 text-sm">
                    <span className="font-semibold">{step.step_number}. {step.tool_name}</span> — {step.status} — {step.summary}
                  </li>
                ))}
              </ol>
            </Panel>
          </>
        ) : (
          <Panel title="Investigation">
            <p className="text-sm text-slate-600">Select a synchronized issue and run an investigation.</p>
          </Panel>
        )}
      </section>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <h2 className="text-sm font-semibold">{title}</h2>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function Strong({ children }: { children: React.ReactNode }) {
  return <div className="text-xl font-semibold">{children}</div>;
}

function Small({ children }: { children: React.ReactNode }) {
  return <div className="mt-1 text-sm text-slate-600">{children}</div>;
}

function Mini({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-line bg-panel p-3">
      <div className="text-xs text-slate-600">{label}</div>
      <div className="mt-1 font-semibold">{value}</div>
    </div>
  );
}
