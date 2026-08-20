"use client";

import { ShieldCheck, Wrench } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { fetchEnterpriseReadiness, fetchRHDTools } from "@/services/system";
import type { EnterpriseReadiness, RHDToolSpec } from "@/types/system";

const order: RHDToolSpec["safety"][] = ["read", "analyze", "recommend", "write_gated"];

export function McpMatrix() {
  const [tools, setTools] = useState<RHDToolSpec[]>([]);
  const [readiness, setReadiness] = useState<EnterpriseReadiness | null>(null);
  const [status, setStatus] = useState("Loading MCP registry");

  useEffect(() => {
    async function load() {
      const [toolResponse, enterprise] = await Promise.all([fetchRHDTools(), fetchEnterpriseReadiness()]);
      setTools(toolResponse.tools);
      setReadiness(enterprise);
      setStatus("MCP registry loaded");
    }
    load().catch((error: Error) => setStatus(error.message));
  }, []);

  const grouped = useMemo(() => {
    return order.map((safety) => ({ safety, tools: tools.filter((tool) => tool.safety === safety) }));
  }, [tools]);

  return (
    <section className="space-y-5">
      <div>
        <p className="text-sm font-medium text-signal">{status}</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">RHD MCP Tool Matrix</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">MCP exposes the same shared RHD Tool Registry used by the REST API. Write-gated tools are visible for planning but still require human approval and server-side policy validation.</p>
      </div>

      <div className="grid gap-4 xl:grid-cols-4">
        {grouped.map((group) => (
          <div key={group.safety} className="rounded-md border border-line bg-white p-4">
            <div className="flex items-center gap-2">
              <Wrench size={16} className="text-signal" aria-hidden={true} />
              <h2 className="text-sm font-semibold uppercase">{label(group.safety)}</h2>
            </div>
            <div className="mt-4 space-y-3">
              {group.tools.map((tool) => (
                <div key={tool.name} className="rounded-md border border-line bg-panel p-3">
                  <div className="text-sm font-semibold text-ink">{tool.name}</div>
                  <p className="mt-2 text-xs leading-5 text-slate-600">{tool.description}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {tool.tags.map((tag) => (
                      <span key={tag} className="rounded-md border border-line px-2 py-1 text-[0.68rem] font-semibold text-slate-600">{tag}</span>
                    ))}
                  </div>
                  {tool.requires_approval ? <div className="mt-3 text-xs font-semibold text-signal">Human approval required</div> : null}
                </div>
              ))}
              {group.tools.length === 0 ? <div className="text-sm text-slate-500">No tools in this class.</div> : null}
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-md border border-line bg-white p-5">
        <div className="flex items-center gap-2">
          <ShieldCheck size={18} className="text-signal" aria-hidden={true} />
          <h2 className="text-sm font-semibold">Enterprise Runtime</h2>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {(readiness?.checks ?? []).map((check) => (
            <div key={check.component} className="rounded-md border border-line bg-panel p-3">
              <div className="text-sm font-semibold capitalize">{check.component}</div>
              <div className="mt-1 text-xs font-bold text-signal">{check.status}</div>
              <p className="mt-2 text-xs leading-5 text-slate-600">{check.detail}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function label(value: string) {
  return value.replace("_", " ");
}
