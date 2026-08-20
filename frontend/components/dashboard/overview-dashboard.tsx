"use client";

import { Activity, AlertTriangle, BrainCircuit, ClipboardList, Database, FileClock, GitBranch, Info, Radar, SearchCheck, ShieldCheck, Sparkles, Workflow } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { fetchAuditLog, fetchIssues, fetchRepositories, fetchRepositoryHealth, fetchReviewQueue, fetchSystemStatus, fetchWeeklyBrief } from "@/services/system";
import type { ActionRecommendation, AuditLogEvent, Issue, Repository, RepositoryHealth, SystemStatus, WeeklyBrief } from "@/types/system";

const priorityRank: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };

export function OverviewDashboard() {
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [repository, setRepository] = useState<Repository | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [health, setHealth] = useState<RepositoryHealth | null>(null);
  const [brief, setBrief] = useState<WeeklyBrief | null>(null);
  const [queue, setQueue] = useState<ActionRecommendation[]>([]);
  const [audit, setAudit] = useState<AuditLogEvent[]>([]);
  const [status, setStatus] = useState("Loading repository intelligence");

  useEffect(() => {
    async function load() {
      const [systemStatus, repositories] = await Promise.all([fetchSystemStatus(), fetchRepositories()]);
      const repo = repositories[0] ?? null;
      setSystem(systemStatus);
      setRepository(repo);
      if (!repo) {
        setStatus("Connect and sync a repository first");
        return;
      }
      const [loadedIssues, loadedHealth, loadedBrief, pendingQueue, auditLog] = await Promise.all([
        fetchIssues(repo.id),
        fetchRepositoryHealth(repo.id),
        fetchWeeklyBrief(repo.id),
        fetchReviewQueue("PENDING"),
        fetchAuditLog({ limit: 7 })
      ]);
      setIssues(loadedIssues);
      setHealth(loadedHealth);
      setBrief(loadedBrief);
      setQueue(pendingQueue);
      setAudit(auditLog.items);
      setStatus("Live repository intelligence loaded");
    }
    load().catch((error: Error) => setStatus(error.message));
  }, []);

  const metrics = useMemo(() => {
    const openIssues = uniqueIssues(issues.filter((issue) => issue.state === "OPEN"));
    const duplicateIds = new Set<number>();
    const needsInfoIds = new Set<number>();
    const securityIds = new Set<number>();

    for (const issue of issues) {
      if (issue.escalation === "POSSIBLE_DUPLICATE") duplicateIds.add(issue.id);
      if (issue.escalation === "NEEDS_INFORMATION") needsInfoIds.add(issue.id);
      if (issue.labels.some((label) => label.toLowerCase().includes("security"))) securityIds.add(issue.id);
    }
    for (const item of queue) {
      if (item.action_type === "MARK_AS_POSSIBLE_DUPLICATE") duplicateIds.add(item.issue_id);
      if (item.action_type === "REQUEST_MORE_INFORMATION") needsInfoIds.add(item.issue_id);
      if (item.action_type === "ESCALATE_FOR_SECURITY_REVIEW" || item.security_signal) securityIds.add(item.issue_id);
    }

    return {
      open: openIssues.length,
      high: uniqueIssues(issues.filter((issue) => issue.priority === "HIGH")).length,
      critical: uniqueIssues(issues.filter((issue) => issue.priority === "CRITICAL")).length,
      duplicates: duplicateIds.size,
      needsInfo: needsInfoIds.size,
      security: securityIds.size,
      pendingActions: queue.length
    };
  }, [issues, queue]);

  const spotlight = [...issues]
    .filter((issue) => issue.state === "OPEN")
    .sort((a, b) => (priorityRank[b.priority ?? ""] ?? 0) - (priorityRank[a.priority ?? ""] ?? 0))
    .slice(0, 5);

  return (
    <section className="space-y-5">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rg-panel rounded-md p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="rg-chip">
                <BrainCircuit size={14} aria-hidden={true} />
                AI Command Center
              </div>
              <h2 className="mt-4 text-2xl font-semibold text-ink">Repository intelligence live for {repository?.full_name ?? system?.demo_repository ?? "demo repository"}</h2>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">{brief?.summary ?? status}</p>
            </div>
            <div className="rounded-md border border-line bg-panel p-4 text-right">
              <div className="text-xs font-semibold uppercase text-slate-500">Health Score</div>
              <div className="mt-2 text-5xl font-semibold text-ink">{health?.overall_score ?? "--"}</div>
              <div className="mt-1 text-sm text-signal">{health?.health_state ?? status}</div>
            </div>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <PipelineStep icon={GitBranch} title="GitHub Sync" detail={repository?.last_synced_at ? new Date(repository.last_synced_at).toLocaleString() : "Waiting for sync"} />
            <PipelineStep icon={SearchCheck} title="RAG Retrieval" detail={`${system?.vector_backend ?? "--"} evidence backend`} />
            <PipelineStep icon={ShieldCheck} title="Policy Gate" detail={`${queue.length} pending human approvals`} />
          </div>
        </div>

        <div className="rounded-md border border-line bg-white p-5">
          <div className="flex items-center gap-2">
            <Database size={18} className="text-signal" aria-hidden={true} />
            <h2 className="text-sm font-semibold">AI Stack Status</h2>
          </div>
          <dl className="mt-4 space-y-3 text-sm">
            <Runtime label="API" value={system ? "online" : "--"} />
            <Runtime label="Database" value={system?.database ?? "--"} />
            <Runtime label="Vector" value={system?.vector_backend ?? "--"} />
            <Runtime label="Live AI Provider" value={system?.live_ai_provider ?? system?.ai_provider ?? "--"} />
            <Runtime label="AI Mode" value={system?.ai_provider_mode ?? "--"} />
            <Runtime label="Deterministic Layer" value={system?.deterministic_intelligence ?? "--"} />
          </dl>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-7">
        <Metric icon={Activity} label="Open Issues" value={metrics.open} detail="unique synced GitHub issues" />
        <Metric icon={ShieldCheck} label="High Priority" value={metrics.high} detail="unique issues scored HIGH" />
        <Metric icon={AlertTriangle} label="Critical Issues" value={metrics.critical} detail="unique issues scored CRITICAL" />
        <Metric icon={ClipboardList} label="Duplicate Signals" value={metrics.duplicates} detail="unique issues flagged duplicate" />
        <Metric icon={Info} label="Needs Information" value={metrics.needsInfo} detail="unique issues blocked on info" />
        <Metric icon={Radar} label="Security Review" value={metrics.security} detail="unique issues needing safety review" />
        <Metric icon={Workflow} label="Pending Actions" value={metrics.pendingActions} detail="recommendations awaiting approval" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel icon={Radar} title="Risk Radar">
            <div className="space-y-3">
              {Object.entries(health?.dimension_scores ?? {}).map(([label, value]) => (
                <ScoreBar key={label} label={formatLabel(label)} value={value} />
              ))}
              {!Object.keys(health?.dimension_scores ?? {}).length ? <Small>{status}</Small> : null}
            </div>
          </Panel>

          <Panel icon={Sparkles} title="Issue Spotlight">
            <div className="space-y-2">
              {spotlight.map((issue) => (
                <a key={issue.id} href={issue.html_url} target="_blank" className="block rounded-md border border-line bg-panel p-3 hover:border-cyan-300/30">
                  <div className="flex items-start justify-between gap-3 text-sm">
                    <span className="font-semibold">#{issue.github_issue_number} {issue.title}</span>
                    <span className="rounded-md border border-line px-2 py-1 text-[0.68rem] font-bold text-signal">{issue.priority ?? "UNSCORED"}</span>
                  </div>
                  <div className="mt-2 text-xs text-slate-600">{issue.classification ?? "UNANALYZED"} / {issue.escalation ?? "NO_ESCALATION"}</div>
                </a>
              ))}
              {!spotlight.length ? <Small>No open issues synchronized yet.</Small> : null}
            </div>
          </Panel>
        </div>

        <Panel icon={FileClock} title="Live Agent Activity">
          <div className="space-y-2">
            {audit.map((item) => (
              <div key={item.id} className="rounded-md border border-line bg-panel p-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-semibold">{item.event_type}</span>
                  <span className="text-xs text-slate-500">{new Date(item.created_at).toLocaleTimeString()}</span>
                </div>
                <p className="mt-1 text-xs leading-5 text-slate-600">{item.safe_summary}</p>
              </div>
            ))}
            {!audit.length ? <Small>No audit events recorded yet.</Small> : null}
          </div>
        </Panel>
      </div>
    </section>
  );
}

function uniqueIssues(items: Issue[]) {
  return Array.from(new Map(items.map((item) => [item.id, item])).values());
}

function Metric({ icon: Icon, label, value, detail }: { icon: LucideIcon; label: string; value: number | string; detail: string }) {
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xs font-bold uppercase text-slate-500">{label}</h2>
        <Icon size={17} className="text-signal" aria-hidden={true} />
      </div>
      <div className="mt-4 text-3xl font-semibold text-ink">{value}</div>
      <p className="mt-1 text-xs leading-5 text-slate-600">{detail}</p>
    </div>
  );
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

function PipelineStep({ icon: Icon, title, detail }: { icon: LucideIcon; title: string; detail: string }) {
  return (
    <div className="rounded-md border border-line bg-panel p-4">
      <Icon size={18} className="text-signal" aria-hidden={true} />
      <div className="mt-3 text-sm font-semibold">{title}</div>
      <div className="mt-1 text-xs leading-5 text-slate-600">{detail}</div>
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
        <div className="h-2 rounded bg-gradient-to-r from-cyan-300 to-teal-300" style={{ width: `${bounded}%` }} />
      </div>
    </div>
  );
}

function Runtime({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line pb-3 last:border-b-0 last:pb-0">
      <dt className="text-slate-600">{label}</dt>
      <dd className="text-right font-medium text-ink">{value}</dd>
    </div>
  );
}

function Small({ children }: { children: React.ReactNode }) {
  return <p className="text-sm leading-6 text-slate-600">{children}</p>;
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
