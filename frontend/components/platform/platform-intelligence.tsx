"use client";

import { Bot, BrainCircuit, CheckCircle2, RadioTower, ServerCog, ShieldCheck, Workflow, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { fetchMLModels, fetchModelGatewayStatus } from "@/services/system";
import type { MLModelCard, ModelProviderStatus } from "@/types/system";

const automationRules = [
  { trigger: "Issue opened", action: "RHD issue investigation", human: "Required for external writes", enabled: true },
  { trigger: "PR opened", action: "PR risk analysis", human: "Review before action", enabled: true },
  { trigger: "Release published", action: "Release risk scan", human: "Required for external writes", enabled: true },
  { trigger: "Security signal", action: "Security triage", human: "Always required", enabled: true },
  { trigger: "Push", action: "Bounded code index", human: "Read-only", enabled: false },
];

export function PlatformIntelligence({ mode = "overview" }: { mode?: "overview" | "models" | "automation" | "system" }) {
  const [providers, setProviders] = useState<ModelProviderStatus[]>([]);
  const [priority, setPriority] = useState<string[]>([]);
  const [models, setModels] = useState<MLModelCard[]>([]);
  const [status, setStatus] = useState("Loading platform intelligence");

  useEffect(() => {
    async function load() {
      const [gateway, modelResponse] = await Promise.all([fetchModelGatewayStatus(), fetchMLModels()]);
      setProviders(gateway.providers);
      setPriority(gateway.priority);
      setModels(modelResponse.models);
      setStatus("Platform intelligence loaded");
    }
    load().catch((error: Error) => setStatus(error.message));
  }, []);

  return (
    <section className="space-y-5">
      <div>
        <p className="text-sm font-medium text-signal">{status}</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">{titleFor(mode)}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">RHD combines deterministic tools, optional model providers, ML model cards, event automation, code intelligence foundations, and human-controlled execution.</p>
      </div>

      {(mode === "overview" || mode === "system") ? (
        <div className="grid gap-4 xl:grid-cols-3">
          <Tile icon={ServerCog} label="Persistence" value="SQLite local / PostgreSQL target" detail="pgvector production profile documented" />
          <Tile icon={Workflow} label="Queue" value="Local fallback" detail="Redis-backed production target" />
          <Tile icon={ShieldCheck} label="External Action" value="Human approval required" detail="Policy gate remains mandatory" />
        </div>
      ) : null}

      {(mode === "overview" || mode === "models" || mode === "system") ? (
        <Panel icon={Bot} title="Model Gateway">
          <div className="mb-4 rounded-md border border-line bg-panel p-3 text-xs text-slate-600">Provider priority: {priority.join(" -> ")}</div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {providers.map((provider) => (
              <div key={provider.provider} className="rounded-md border border-line bg-panel p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold capitalize">{provider.provider}</span>
                  {provider.configured ? <CheckCircle2 size={16} className="text-signal" aria-hidden={true} /> : <XCircle size={16} className="text-slate-500" aria-hidden={true} />}
                </div>
                <p className="mt-2 text-xs text-slate-600">{provider.model}</p>
                <p className="mt-2 text-xs text-slate-500">configured {String(provider.configured)} / circuit open {String(provider.circuit_open)}</p>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}

      {(mode === "overview" || mode === "models") ? (
        <Panel icon={BrainCircuit} title="ML Models">
          <div className="grid gap-3 lg:grid-cols-2">
            {models.map((model) => (
              <div key={model.name} className="rounded-md border border-line bg-panel p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold">{model.name}</div>
                    <div className="mt-1 text-xs text-slate-600">{model.task}</div>
                  </div>
                  <span className="rounded-md border border-line px-2 py-1 text-[0.68rem] font-bold text-signal">{model.status}</span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
                  <span>Training rows: {model.training_rows}</span>
                  <span>Test rows: {model.test_rows}</span>
                  <span>Fallback: {model.fallback}</span>
                  <span>Version: {model.version}</span>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}

      {(mode === "overview" || mode === "automation") ? (
        <Panel icon={RadioTower} title="RHD Automation Center">
          <div className="grid gap-3 lg:grid-cols-2">
            {automationRules.map((rule) => (
              <div key={rule.trigger} className="rounded-md border border-line bg-panel p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-semibold">{rule.trigger}</span>
                  <span className="rounded-md border border-line px-2 py-1 text-xs font-bold text-signal">{rule.enabled ? "ENABLED" : "PLANNED"}</span>
                </div>
                <p className="mt-2 text-sm text-slate-600">{rule.action}</p>
                <p className="mt-1 text-xs text-slate-500">{rule.human}</p>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}
    </section>
  );
}

function titleFor(mode: string) {
  if (mode === "models") return "RHD Model Intelligence";
  if (mode === "automation") return "RHD Automation Center";
  if (mode === "system") return "RHD System";
  return "RHD Platform Intelligence";
}

function Panel({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children: ReactNode }) {
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

function Tile({ icon: Icon, label, value, detail }: { icon: LucideIcon; label: string; value: string; detail: string }) {
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <Icon size={18} className="text-signal" aria-hidden={true} />
      <div className="mt-3 text-xs font-bold uppercase text-slate-500">{label}</div>
      <div className="mt-2 text-lg font-semibold text-ink">{value}</div>
      <div className="mt-1 text-xs text-slate-600">{detail}</div>
    </div>
  );
}
