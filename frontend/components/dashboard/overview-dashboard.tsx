"use client";

import { Activity, AlertTriangle, Database, Github, Info, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchRepositories, fetchRepositoryHealth, fetchSystemStatus, fetchWeeklyBrief } from "@/services/system";
import type { Repository, RepositoryHealth, SystemStatus, WeeklyBrief } from "@/types/system";

export function OverviewDashboard() {
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [repository, setRepository] = useState<Repository | null>(null);
  const [health, setHealth] = useState<RepositoryHealth | null>(null);
  const [brief, setBrief] = useState<WeeklyBrief | null>(null);
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
      const [loadedHealth, loadedBrief] = await Promise.all([fetchRepositoryHealth(repo.id), fetchWeeklyBrief(repo.id)]);
      setHealth(loadedHealth);
      setBrief(loadedBrief);
      setStatus("Live repository intelligence loaded");
    }
    load().catch((error: Error) => setStatus(error.message));
  }, []);

  return (
    <section className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        <Metric icon={Activity} label="Health Score" value={health ? `${health.overall_score}` : "--"} detail={health?.health_state ?? status} />
        <Metric icon={AlertTriangle} label="Open Issues" value={health?.signals.open_issue_count ?? "--"} detail="synchronized backlog" />
        <Metric icon={ShieldCheck} label="High Priority" value={health?.signals.high_priority_count ?? "--"} detail="maintainer review load" />
        <Metric icon={Info} label="Needs Info" value={health?.signals.needs_information_count ?? "--"} detail="blocked triage items" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="rounded-md border border-line bg-white p-5">
          <h2 className="text-sm font-semibold">Weekly Brief</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">{brief?.summary ?? status}</p>
          <div className="mt-5 grid gap-3 md:grid-cols-4">
            <Mini label="Duplicates" value={brief?.possible_duplicates ?? "--"} />
            <Mini label="Needs Info" value={brief?.needs_information ?? "--"} />
            <Mini label="PR Activity" value={brief?.recent_pr_activity ?? "--"} />
            <Mini label="Releases" value={brief?.release_activity ?? "--"} />
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-md border border-line bg-white p-5">
            <div className="flex items-center gap-2">
              <Github size={18} className="text-slate-700" aria-hidden="true" />
              <h2 className="text-sm font-semibold">Repository</h2>
            </div>
            <p className="mt-3 text-sm font-medium text-ink">{repository?.full_name ?? system?.demo_repository ?? "No repository connected"}</p>
            <p className="mt-1 text-xs text-slate-600">{repository?.last_synced_at ? `Last synced ${new Date(repository.last_synced_at).toLocaleString()}` : "Waiting for first sync"}</p>
          </div>
          <div className="rounded-md border border-line bg-white p-5">
            <div className="flex items-center gap-2">
              <Database size={18} className="text-amber" aria-hidden="true" />
              <h2 className="text-sm font-semibold">Runtime</h2>
            </div>
            <dl className="mt-3 space-y-2 text-sm">
              <Runtime label="Database" value={system?.database ?? "--"} />
              <Runtime label="Vector" value={system?.vector_backend ?? "--"} />
              <Runtime label="AI" value={system?.ai_provider ?? "--"} />
            </dl>
          </div>
        </div>
      </div>
    </section>
  );
}

function Metric({ icon: Icon, label, value, detail }: { icon: React.ComponentType<{ size?: number; className?: string; "aria-hidden"?: boolean }>; label: string; value: number | string; detail: string }) {
  return (
    <div className="rounded-md border border-line bg-white p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">{label}</h2>
        <Icon size={18} className="text-signal" aria-hidden={true} />
      </div>
      <div className="mt-4 text-3xl font-semibold text-ink">{value}</div>
      <p className="mt-1 text-xs text-slate-600">{detail}</p>
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

function Runtime({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-slate-600">{label}</dt>
      <dd className="font-medium text-ink">{value}</dd>
    </div>
  );
}
