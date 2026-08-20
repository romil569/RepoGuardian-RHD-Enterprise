"use client";

import { Activity, BarChart3, ClipboardCheck, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchEvaluation, fetchRepositories, fetchRepositoryHealth, fetchWeeklyBrief } from "@/services/system";
import type { Evaluation, Repository, RepositoryHealth, WeeklyBrief } from "@/types/system";

export function HealthDashboard() {
  const [repository, setRepository] = useState<Repository | null>(null);
  const [health, setHealth] = useState<RepositoryHealth | null>(null);
  const [brief, setBrief] = useState<WeeklyBrief | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [status, setStatus] = useState("Loading repository health");

  useEffect(() => {
    async function load() {
      const repositories = await fetchRepositories();
      const repo = repositories[0] ?? null;
      setRepository(repo);
      if (!repo) {
        setStatus("Connect and sync a repository first");
        return;
      }
      const [loadedHealth, loadedBrief, loadedEvaluation] = await Promise.all([fetchRepositoryHealth(repo.id), fetchWeeklyBrief(repo.id), fetchEvaluation(repo.id)]);
      setHealth(loadedHealth);
      setBrief(loadedBrief);
      setEvaluation(loadedEvaluation);
      setStatus("Repository health loaded");
    }
    load().catch((error: Error) => setStatus(error.message));
  }, []);

  return (
    <section className="space-y-5">
      <div>
        <p className="text-sm font-medium text-signal">{repository?.full_name ?? status}</p>
        <h1 className="mt-2 text-2xl font-semibold">Repository Health</h1>
      </div>

      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <div className="rounded-md border border-line bg-white p-5">
          <div className="flex items-center gap-2">
            <Activity size={19} className="text-signal" aria-hidden="true" />
            <h2 className="text-sm font-semibold">Health Score</h2>
          </div>
          <div className="mt-5 text-5xl font-semibold">{health?.overall_score ?? "--"}</div>
          <p className="mt-2 text-sm text-slate-600">{health?.health_state ?? status}</p>
        </div>

        <div className="rounded-md border border-line bg-white p-5">
          <h2 className="text-sm font-semibold">Dimensions</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {Object.entries(health?.dimension_scores ?? {}).map(([label, value]) => (
              <ScoreBar key={label} label={formatLabel(label)} value={value} />
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Distribution title="Priority Distribution" values={health?.distributions.priority ?? {}} />
        <Distribution title="Classification Distribution" values={health?.distributions.classification ?? {}} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel icon={TrendingUp} title="Backlog Trend">
          <div className="space-y-2">
            {(health?.history.issue_creation_vs_closure ?? []).map((point) => (
              <div key={point.label} className="grid grid-cols-[80px_1fr_1fr] items-center gap-3 text-sm">
                <span className="text-slate-600">{point.label}</span>
                <span>Created {point.created}</span>
                <span>Closed {point.closed}</span>
              </div>
            ))}
            {health?.history.insufficient_history ? <p className="text-sm text-slate-600">More issue history will make trend analysis stronger.</p> : null}
          </div>
        </Panel>

        <Panel icon={ClipboardCheck} title="Evaluation">
          <p className="text-sm text-slate-600">
            {evaluation?.status === "OK"
              ? `Human agreement rate ${(Number(evaluation.metrics.human_agreement_rate ?? 0) * 100).toFixed(0)}% across ${evaluation.labeled_count} labels.`
              : `Status ${evaluation?.status ?? "UNKNOWN"} with ${evaluation?.labeled_count ?? 0} labeled feedback items.`}
          </p>
          <div className="mt-4 space-y-2">
            {evaluation?.confusion_matrix.map((item) => (
              <div key={`${item.predicted}-${item.actual}`} className="text-sm text-slate-700">
                {item.predicted} {"->"} {item.actual}: {item.count}
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel icon={BarChart3} title="Weekly Brief">
        <p className="text-sm leading-6 text-slate-600">{brief?.summary ?? status}</p>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <Mini label="High Priority" value={brief?.high_priority_items.length ?? "--"} />
          <Mini label="Escalations" value={brief?.important_escalations.length ?? "--"} />
          <Mini label="Duplicates" value={brief?.possible_duplicates ?? "--"} />
          <Mini label="Needs Info" value={brief?.needs_information ?? "--"} />
        </div>
      </Panel>
    </section>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-slate-600">{value}</span>
      </div>
      <div className="mt-2 h-2 rounded bg-panel">
        <div className="h-2 rounded bg-signal" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

function Distribution({ title, values }: { title: string; values: Record<string, number> }) {
  const entries = Object.entries(values);
  return (
    <div className="rounded-md border border-line bg-white p-5">
      <h2 className="text-sm font-semibold">{title}</h2>
      <div className="mt-4 space-y-2">
        {entries.length ? entries.map(([label, value]) => <ScoreBar key={label} label={label} value={value} />) : <p className="text-sm text-slate-600">No analyzed issues yet.</p>}
      </div>
    </div>
  );
}

function Panel({ icon: Icon, title, children }: { icon: React.ComponentType<{ size?: number; className?: string; "aria-hidden"?: boolean }>; title: string; children: React.ReactNode }) {
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

function Mini({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-line bg-panel p-3">
      <div className="text-xs text-slate-600">{label}</div>
      <div className="mt-1 text-xl font-semibold">{value}</div>
    </div>
  );
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
