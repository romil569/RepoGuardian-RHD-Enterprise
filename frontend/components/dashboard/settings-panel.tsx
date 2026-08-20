"use client";

import { Settings2, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchPolicySettings, fetchSystemStatus } from "@/services/system";
import type { PolicySettings, SystemStatus } from "@/types/system";

export function SettingsPanel() {
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [policy, setPolicy] = useState<PolicySettings | null>(null);
  const [status, setStatus] = useState("Loading settings");

  useEffect(() => {
    async function load() {
      const [loadedSystem, loadedPolicy] = await Promise.all([fetchSystemStatus(), fetchPolicySettings()]);
      setSystem(loadedSystem);
      setPolicy(loadedPolicy);
      setStatus("Settings loaded");
    }
    load().catch((error: Error) => setStatus(error.message));
  }, []);

  return (
    <section className="max-w-5xl space-y-5">
      <div>
        <p className="text-sm font-medium text-signal">{status}</p>
        <h1 className="mt-2 text-2xl font-semibold">Settings</h1>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel icon={Settings2} title="Runtime">
          <SettingRow label="Environment" value={system?.app_env ?? "--"} />
          <SettingRow label="Database" value={system?.database ?? "--"} />
          <SettingRow label="Data backend" value={system?.data_backend ?? "--"} />
          <SettingRow label="Vector backend" value={system?.vector_backend ?? "--"} />
          <SettingRow label="AI provider" value={system?.ai_provider ?? "--"} />
          <SettingRow label="Demo repository" value={system?.demo_repository ?? "--"} />
        </Panel>

        <Panel icon={SlidersHorizontal} title="Policy">
          <SettingRow label="Duplicate possible" value={format(policy?.duplicate_possible_threshold)} />
          <SettingRow label="Duplicate very likely" value={format(policy?.duplicate_very_likely_threshold)} />
          <SettingRow label="Security escalation" value={format(policy?.security_escalation_threshold)} />
          <SettingRow label="Stale issue days" value={format(policy?.stale_issue_days)} />
          <SettingRow label="High priority score" value={format(policy?.high_priority_score_threshold)} />
          <SettingRow label="Critical priority score" value={format(policy?.critical_priority_score_threshold)} />
          <SettingRow label="Sync interval minutes" value={format(policy?.repo_sync_interval_minutes)} />
        </Panel>
      </div>
    </section>
  );
}

function Panel({ icon: Icon, title, children }: { icon: React.ComponentType<{ size?: number; className?: string; "aria-hidden"?: boolean }>; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-line bg-white p-5">
      <div className="flex items-center gap-2">
        <Icon size={18} className="text-signal" aria-hidden={true} />
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      <dl className="mt-4 space-y-3 text-sm">{children}</dl>
    </div>
  );
}

function SettingRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line pb-3 last:border-b-0 last:pb-0">
      <dt className="text-slate-600">{label}</dt>
      <dd className="max-w-[260px] text-right font-medium text-ink">{value}</dd>
    </div>
  );
}

function format(value: number | undefined) {
  return typeof value === "number" ? String(value) : "--";
}
