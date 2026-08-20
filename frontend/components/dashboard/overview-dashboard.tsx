"use client";

import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  ClipboardList,
  Database,
  FileClock,
  GitBranch,
  GitPullRequest,
  LockKeyhole,
  Network,
  PlayCircle,
  Radar,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  askRHD,
  fetchAuditLog,
  fetchRepositories,
  fetchRHDInitialScan,
  fetchRHDReview,
  fetchSystemStatus,
  onboardRepositoryWithRHD,
} from "@/services/system";
import type { AuditLogEvent, Repository, RHDInitialScan, RHDQueryResponse, RHDReview, SystemStatus } from "@/types/system";

const demoRepository = process.env.NEXT_PUBLIC_DEMO_GITHUB_REPOSITORY ?? "romil569/RepoGuardian-Demo";

const suggestions = [
  "Give me a full review.",
  "What should I fix first?",
  "Why is repository health WATCH?",
  "Show duplicate issues.",
  "Which issues are security-sensitive?",
  "What happened after v1.2.0?",
  "Which issues need more information?",
  "Give me today's maintainer priorities.",
];

const toolkit = [
  "Repository Search",
  "Semantic Retrieval",
  "Issue Classifier",
  "Duplicate Engine",
  "Completeness Engine",
  "Security Analyzer",
  "Release Analyzer",
  "Priority Engine",
  "Evidence Validator",
  "Policy Gate",
];

const coreNodes = [
  { label: "Issues", left: "84%", top: "50%" },
  { label: "PR", left: "67%", top: "79%" },
  { label: "RAG", left: "33%", top: "79%" },
  { label: "Security", left: "16%", top: "50%" },
  { label: "Evidence", left: "33%", top: "21%" },
  { label: "Actions", left: "67%", top: "21%" },
];

export function OverviewDashboard() {
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [repository, setRepository] = useState<Repository | null>(null);
  const [review, setReview] = useState<RHDReview | null>(null);
  const [scan, setScan] = useState<RHDInitialScan | null>(null);
  const [audit, setAudit] = useState<AuditLogEvent[]>([]);
  const [repositoryInput, setRepositoryInput] = useState(`https://github.com/${demoRepository}`);
  const [question, setQuestion] = useState("What should I fix first?");
  const [answer, setAnswer] = useState<RHDQueryResponse | null>(null);
  const [sessionContext, setSessionContext] = useState<Record<string, unknown>>({});
  const [status, setStatus] = useState("READY");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    async function load() {
      const [systemStatus, repositories, auditLog] = await Promise.all([fetchSystemStatus(), fetchRepositories(), fetchAuditLog({ limit: 7 })]);
      const repo = repositories[0] ?? null;
      setSystem(systemStatus);
      setRepository(repo);
      setAudit(auditLog.items);
      if (!repo) {
        setStatus("READY");
        return;
      }
      const [loadedReview, loadedScan] = await Promise.all([fetchRHDReview(repo.id), fetchRHDInitialScan(repo.id)]);
      setReview(loadedReview);
      setScan(loadedScan);
      setRepositoryInput(repo.full_name);
      setStatus(repo.access_mode === "READ_ONLY_PUBLIC" ? "READ_ONLY_ANALYSIS" : "READY");
    }
    load().catch((error: Error) => setStatus(error.message));
  }, []);

  const accessMode = review?.repository.access_mode ?? repository?.access_mode ?? "WRITE_ENABLED_DEMO";
  const rhdState = review?.executive_assessment.state ?? status;
  const loadSignals = review?.maintainer_workload.signals ?? {};
  const mapNodes = useMemo(() => buildMapNodes(review), [review]);

  async function analyzeRepository() {
    if (!repositoryInput.trim()) return;
    setBusy(true);
    setStatus("SYNCING");
    try {
      const result = await onboardRepositoryWithRHD(repositoryInput, true);
      setRepository(result.repository);
      setReview(result.review);
      setScan(result.initial_scan);
      setAnswer(null);
      setStatus(result.access_mode === "READ_ONLY_PUBLIC" ? "READ_ONLY_ANALYSIS" : "READY");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "RHD onboarding failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitQuestion(nextQuestion = question) {
    if (!repository || !nextQuestion.trim()) return;
    setBusy(true);
    setStatus("INVESTIGATING");
    try {
      const response = await askRHD(repository.id, nextQuestion, sessionContext);
      setAnswer(response);
      setSessionContext(response.context);
      setQuestion(nextQuestion);
      setStatus(accessMode === "READ_ONLY_PUBLIC" ? "READ_ONLY_ANALYSIS" : "READY");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "RHD query failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-5">
      <div className="grid gap-5 2xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="rg-panel overflow-hidden rounded-md p-5">
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
            <div>
              <div className="rg-chip">
                <Sparkles size={14} aria-hidden={true} />
                RepoGuardian powered by RHD
              </div>
              <h2 className="mt-5 text-4xl font-semibold text-ink md:text-5xl">RHD</h2>
              <p className="mt-2 text-xl text-cyan-100">Repository Health Director</p>
              <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-600">Connect a repository. RHD investigates the rest with repository-scoped tools, verified evidence, deterministic fallback, and human-controlled external actions.</p>
              <div className="mt-6 grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px]">
                <div className="rounded-md border border-cyan-300/25 bg-[#07111f]/80 p-3 shadow-2xl shadow-cyan-950/20">
                  <label className="text-xs font-bold uppercase text-slate-500">GitHub Repository URL</label>
                  <div className="mt-2 flex items-center gap-2">
                    <GitBranch size={18} className="text-signal" aria-hidden={true} />
                    <input
                      value={repositoryInput}
                      onChange={(event) => setRepositoryInput(event.target.value)}
                      placeholder="https://github.com/owner/repository"
                      className="h-12 min-w-0 flex-1 border-0 bg-transparent text-base font-semibold outline-none"
                    />
                  </div>
                </div>
                <button onClick={analyzeRepository} disabled={busy || !repositoryInput.trim()} className="inline-flex h-full min-h-20 items-center justify-center gap-2 rounded-md bg-signal px-4 text-sm font-bold text-slate-950 shadow-lg shadow-teal-950/40 disabled:opacity-40">
                  <PlayCircle size={18} aria-hidden={true} />
                  Analyze Repository
                </button>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <StatusChip label="RHD Status" value={status} />
                <StatusChip label="Access" value={accessMode === "READ_ONLY_PUBLIC" ? "READ-ONLY ANALYSIS" : "WRITE-ENABLED DEMO REPOSITORY"} />
                <StatusChip label="Live Language Model" value={system?.live_ai_provider === "not_configured" ? "OPTIONAL / NOT CONFIGURED" : system?.live_ai_provider ?? "--"} />
                <StatusChip label="RHD Intelligence" value="ACTIVE" />
              </div>
            </div>
            <RHDCoreVisual state={rhdState} busy={busy} />
          </div>
        </div>

        <SystemPanel system={system} repository={review?.repository ?? repository} review={review} scan={scan} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="space-y-5">
          <RHDConsole question={question} setQuestion={setQuestion} submitQuestion={submitQuestion} answer={answer} disabled={!repository || busy} />

          <Panel icon={BrainCircuit} title="RHD Executive Assessment">
            <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
              <div className="rounded-md border border-line bg-panel p-4">
                <div className="text-xs font-bold uppercase text-slate-500">State</div>
                <div className="mt-2 text-3xl font-semibold text-ink">{review?.executive_assessment.state ?? "--"}</div>
                <div className="mt-1 text-sm text-signal">{review ? `${review.executive_assessment.health_score}/100` : "Waiting for repository review"}</div>
              </div>
              <div>
                <p className="text-sm leading-6 text-slate-600">{review?.executive_assessment.recommended_maintainer_focus ?? "Paste a GitHub repository URL to generate an evidence-backed RHD repository review."}</p>
                <div className="mt-4 grid gap-2 md:grid-cols-2">
                  {(review?.executive_assessment.main_signals ?? ["Repository-scoped RAG", "Evidence validation", "Human approval gate", "Deterministic fallback"]).map((item) => (
                    <div key={item} className="rounded-md border border-line bg-panel p-3 text-sm">{item}</div>
                  ))}
                </div>
              </div>
            </div>
          </Panel>

          <Panel icon={ClipboardList} title="Today's Maintainer Priorities">
            <div className="space-y-2">
              {(review?.recommended_action_plan ?? []).slice(0, 7).map((item, index) => (
                <a key={`${item.affected.id}-${item.reason}`} href={item.affected.url} target="_blank" className="grid gap-3 rounded-md border border-line bg-panel p-3 text-sm hover:border-cyan-300/30 md:grid-cols-[36px_1fr_110px]">
                  <span className="grid h-8 w-8 place-items-center rounded-full bg-cyan-300/10 font-bold text-signal">{index + 1}</span>
                  <span>
                    <span className="block font-semibold">Issue #{item.affected.number}: {item.affected.title}</span>
                    <span className="mt-1 block text-xs leading-5 text-slate-600">{item.recommended_human_action}</span>
                  </span>
                  <span className="self-start rounded-md border border-line px-2 py-1 text-center text-xs font-bold text-signal">{item.priority}</span>
                </a>
              ))}
              {!review?.recommended_action_plan.length ? <Small>No RHD priority actions yet. Run investigations or sync a repository to enrich the review.</Small> : null}
            </div>
          </Panel>

          <div className="grid gap-5 xl:grid-cols-2">
            <Panel icon={Radar} title="Repository Health + Risk Dimensions">
              <div className="space-y-3">
                {Object.entries(review?.health.dimension_scores ?? {}).map(([label, value]) => <ScoreBar key={label} label={formatLabel(label)} value={value} />)}
                {!review ? <Small>RHD health dimensions appear after repository review.</Small> : null}
              </div>
            </Panel>
            <Panel icon={Network} title="Repository Intelligence Map">
              <IntelligenceMap nodes={mapNodes} />
            </Panel>
          </div>

          <div className="grid gap-5 xl:grid-cols-3">
            <IntelligenceTile icon={AlertTriangle} label="Issue Backlog" value={review?.issue_backlog.open ?? "--"} detail={`${review?.issue_backlog.total ?? "--"} synchronized total`} />
            <IntelligenceTile icon={GitPullRequest} label="PR Activity" value={review?.pr_activity.open ?? "--"} detail={`${review?.pr_activity.total ?? "--"} synchronized PRs`} />
            <IntelligenceTile icon={FileClock} label="Releases" value={review?.release_stability.releases ?? "--"} detail="release history signals" />
          </div>

          <Panel icon={Workflow} title="RHD Issue Clusters">
            <div className="grid gap-3 md:grid-cols-2">
              {(review?.issue_backlog.clusters ?? []).slice(0, 6).map((cluster) => (
                <div key={cluster.name} className="rounded-md border border-line bg-panel p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-semibold">{cluster.name}</span>
                    <span className="rounded-md border border-line px-2 py-1 text-xs font-bold text-signal">{cluster.risk}</span>
                  </div>
                  <p className="mt-2 text-xs text-slate-600">{cluster.issue_count} issues / {cluster.duplicate_concentration} duplicate signals</p>
                </div>
              ))}
              {!review?.issue_backlog.clusters.length ? <Small>No issue clusters available yet.</Small> : null}
            </div>
          </Panel>
        </div>

        <aside className="space-y-5">
          <Panel icon={ShieldCheck} title="Automation Level">
            <Automation label="Analyze" value={review?.automation_level.analyze ?? "AUTOMATIC"} />
            <Automation label="Recommend" value={review?.automation_level.recommend ?? "AUTOMATIC"} />
            <Automation label="External Action" value={review?.automation_level.external_action ?? "HUMAN_APPROVAL_REQUIRED"} />
            <p className="mt-4 text-xs leading-5 text-slate-600">RHD investigates. RHD recommends. Humans authorize external action.</p>
          </Panel>

          <Panel icon={Database} title="RHD Toolkit">
            <div className="grid gap-2">
              {toolkit.map((tool) => (
                <div key={tool} className="flex items-center justify-between rounded-md border border-line bg-panel px-3 py-2 text-sm">
                  <span>{tool}</span>
                  <CheckCircle2 size={15} className="text-signal" aria-hidden={true} />
                </div>
              ))}
            </div>
          </Panel>

          <Panel icon={Activity} title="Maintainer Attention Load">
            <div className="text-3xl font-semibold text-ink">{review?.maintainer_workload.load ?? "--"}</div>
            <p className="mt-2 text-xs text-slate-600">{review?.maintainer_workload.rules ?? "Deterministic workload rules appear after review."}</p>
            <div className="mt-4 space-y-2">
              {Object.entries(loadSignals).map(([key, value]) => (
                <Runtime key={key} label={formatLabel(key)} value={String(value)} />
              ))}
            </div>
          </Panel>

          <Panel icon={FileClock} title="Live RHD Activity">
            <div className="space-y-2">
              {audit.map((item) => (
                <div key={item.id} className="rounded-md border border-line bg-panel p-3 text-sm">
                  <div className="font-semibold">{item.event_type}</div>
                  <p className="mt-1 text-xs leading-5 text-slate-600">{item.safe_summary}</p>
                </div>
              ))}
              {!audit.length ? <Small>No audit events recorded yet.</Small> : null}
            </div>
          </Panel>
        </aside>
      </div>
    </section>
  );
}

function RHDConsole({ question, setQuestion, submitQuestion, answer, disabled }: { question: string; setQuestion: (value: string) => void; submitQuestion: (value?: string) => void; answer: RHDQueryResponse | null; disabled: boolean }) {
  return (
    <Panel icon={Terminal} title="RHD Console">
      <div className="rounded-md border border-cyan-300/25 bg-[#07111f]/80 p-3">
        <div className="flex items-center gap-2 text-xs font-bold uppercase text-slate-500">
          <Terminal size={14} className="text-signal" aria-hidden={true} />
          &gt; rhd ask
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <input value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => event.key === "Enter" && submitQuestion()} className="h-11 min-w-0 flex-1 rounded-md border border-line px-3 text-sm" />
          <button disabled={disabled || !question.trim()} onClick={() => submitQuestion()} className="inline-flex h-11 items-center gap-2 rounded-md bg-signal px-4 text-sm font-bold text-slate-950 disabled:opacity-40">
            <Search size={16} aria-hidden={true} />
            Ask RHD
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {suggestions.map((item) => (
            <button key={item} disabled={disabled} onClick={() => submitQuestion(item)} className="rounded-md border border-line bg-panel px-2 py-1.5 text-xs font-medium text-slate-600 hover:text-ink disabled:opacity-40">{item}</button>
          ))}
        </div>
      </div>
      {answer ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
          <div className="rounded-md border border-line bg-panel p-4">
            <div className="text-xs font-bold uppercase text-signal">Answer / {answer.intent}</div>
            <p className="mt-3 text-sm leading-6 text-slate-600">{answer.answer}</p>
            <h3 className="mt-4 text-sm font-semibold">Recommended Actions</h3>
            <ul className="mt-2 space-y-2 text-sm text-slate-600">
              {answer.recommended_actions.map((item) => <li key={item}>{item}</li>)}
            </ul>
            <p className="mt-4 text-xs text-slate-500">RHD confidence indicates evidence strength, not certainty: {answer.confidence}</p>
          </div>
          <div className="rounded-md border border-line bg-panel p-4">
            <div className="text-xs font-bold uppercase text-slate-500">RHD Investigation Trace</div>
            <div className="mt-3 space-y-2">
              {answer.trace.map((step) => (
                <div key={`${step.step}-${step.summary}`} className="text-xs leading-5 text-slate-600">✓ {step.step}: {step.summary}</div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </Panel>
  );
}

function RHDCoreVisual({ state, busy }: { state: string; busy: boolean }) {
  return (
    <div className="relative min-h-[300px] overflow-hidden rounded-md border border-line bg-[#07111f]/80">
      <div className={`absolute left-1/2 top-1/2 grid h-28 w-28 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-cyan-300/40 bg-cyan-300/10 text-center shadow-[0_0_70px_rgba(34,211,238,0.25)] ${busy ? "animate-pulse" : ""}`}>
        <div>
          <div className="text-2xl font-semibold text-ink">RHD</div>
          <div className="mt-1 text-[0.65rem] font-bold uppercase text-signal">{state}</div>
        </div>
      </div>
      {coreNodes.map((node) => {
        return (
          <div key={node.label} className="absolute rounded-md border border-line bg-panel px-2 py-1 text-xs font-semibold text-slate-600" style={{ left: node.left, top: node.top, transform: "translate(-50%, -50%)" }}>
            {node.label}
          </div>
        );
      })}
      <div className="absolute inset-x-8 top-1/2 rg-hairline" />
      <div className="absolute inset-y-8 left-1/2 w-px bg-gradient-to-b from-transparent via-cyan-300/40 to-transparent" />
    </div>
  );
}

function SystemPanel({ system, repository, review, scan }: { system: SystemStatus | null; repository: Repository | null | undefined; review: RHDReview | null; scan: RHDInitialScan | null }) {
  return (
    <div className="rounded-md border border-line bg-white p-5">
      <div className="flex items-center gap-2">
        <Database size={18} className="text-signal" aria-hidden={true} />
        <h2 className="text-sm font-semibold">RHD System</h2>
      </div>
      <dl className="mt-4 space-y-3 text-sm">
        <Runtime label="Repository" value={repository?.full_name ?? "--"} />
        <Runtime label="Sync Status" value={repository?.last_synced_at ? new Date(repository.last_synced_at).toLocaleString() : "--"} />
        <Runtime label="Indexed Documents" value={String(review?.repository.indexed_documents ?? repository?.indexed_documents ?? "--")} />
        <Runtime label="Vector Backend" value={system?.vector_backend ?? "--"} />
        <Runtime label="RAG Status" value={review?.evidence.length ? "repository-scoped evidence available" : "waiting for indexed evidence"} />
        <Runtime label="AI Provider" value={system?.live_ai_provider ?? system?.ai_provider ?? "--"} />
        <Runtime label="Deterministic Engine" value={system?.deterministic_intelligence ?? "--"} />
        <Runtime label="Evidence Validator" value="active" />
        <Runtime label="Human Policy Gate" value={review?.automation_level.external_action ?? "HUMAN_APPROVAL_REQUIRED"} />
        <Runtime label="Tool Count" value={String(toolkit.length)} />
      </dl>
      <div className="mt-4 rounded-md border border-line bg-panel p-3">
        <div className="text-xs font-bold uppercase text-slate-500">RHD Initial Scan</div>
        <div className="mt-2 max-h-44 space-y-2 overflow-auto">
          {(scan?.steps ?? []).slice(0, 15).map((step) => (
            <div key={step.name} className="text-xs leading-5 text-slate-600">✓ {step.name}: {typeof step.summary === "string" ? step.summary : JSON.stringify(step.summary)}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

function IntelligenceMap({ nodes }: { nodes: Array<{ label: string; value: string; icon: LucideIcon }> }) {
  return (
    <div className="relative min-h-[260px] overflow-hidden rounded-md border border-line bg-panel p-4">
      <div className="absolute inset-x-6 top-1/2 h-px bg-cyan-300/20" />
      <div className="absolute inset-y-6 left-1/2 w-px bg-cyan-300/20" />
      <div className="relative grid h-full gap-3 md:grid-cols-2">
        {nodes.map((node) => (
          <div key={node.label} className="rounded-md border border-line bg-[#091322]/90 p-3">
            <node.icon size={16} className="text-signal" aria-hidden={true} />
            <div className="mt-2 text-sm font-semibold">{node.label}</div>
            <div className="mt-1 text-xs text-slate-600">{node.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function buildMapNodes(review: RHDReview | null): Array<{ label: string; value: string; icon: LucideIcon }> {
  return [
    { label: "Repository", value: review?.repository.full_name ?? "waiting for repository", icon: GitBranch },
    { label: "Issues", value: `${review?.issue_backlog.open ?? "--"} open`, icon: AlertTriangle },
    { label: "Duplicate Clusters", value: `${review?.duplicate_burden.count ?? "--"} clusters`, icon: Workflow },
    { label: "Security Signals", value: `${review?.security_signals.length ?? "--"} signals`, icon: LockKeyhole },
    { label: "PRs", value: `${review?.pr_activity.open ?? "--"} open`, icon: GitPullRequest },
    { label: "Evidence", value: `${review?.evidence.length ?? "--"} sources`, icon: Database },
  ];
}

function Panel({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-line bg-white p-5">
      <div className="flex items-center gap-2">
        <Icon size={18} className="text-signal" aria-hidden={true} />
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function IntelligenceTile({ icon: Icon, label, value, detail }: { icon: LucideIcon; label: string; value: number | string; detail: string }) {
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <Icon size={17} className="text-signal" aria-hidden={true} />
      <div className="mt-3 text-xs font-bold uppercase text-slate-500">{label}</div>
      <div className="mt-2 text-3xl font-semibold text-ink">{value}</div>
      <div className="mt-1 text-xs text-slate-600">{detail}</div>
    </div>
  );
}

function StatusChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-panel px-3 py-2 text-xs">
      <span className="font-bold uppercase text-slate-500">{label}: </span>
      <span className="font-semibold text-signal">{value}</span>
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const bounded = Math.max(0, Math.min(100, value));
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-slate-600">{value}</span>
      </div>
      <div className="mt-2 h-2 rounded bg-panel">
        <div className="h-2 rounded bg-gradient-to-r from-cyan-300 via-teal-300 to-violet-300" style={{ width: `${bounded}%` }} />
      </div>
    </div>
  );
}

function Runtime({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-line pb-3 last:border-b-0 last:pb-0">
      <dt className="text-slate-600">{label}</dt>
      <dd className="max-w-[210px] text-right font-medium text-ink">{value}</dd>
    </div>
  );
}

function Automation({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line py-3 first:pt-0 last:border-b-0">
      <span className="text-sm text-slate-600">{label}</span>
      <span className="rounded-md border border-line bg-panel px-2 py-1 text-xs font-bold text-signal">{value.replaceAll("_", " ")}</span>
    </div>
  );
}

function Small({ children }: { children: React.ReactNode }) {
  return <p className="text-sm leading-6 text-slate-600">{children}</p>;
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
