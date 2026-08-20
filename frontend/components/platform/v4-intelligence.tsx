"use client";

import { AlertTriangle, BrainCircuit, GitPullRequest, Map, RadioTower, SearchCheck, ShieldCheck, Waypoints } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { fetchRepositories, fetchV4AgentMesh, fetchV4MissionControl, fetchV4ModelLab, fetchV4NeuralMap, fetchV4Observatory, fetchV4RagPipeline } from "@/services/system";

type V4Mode = "mission" | "map" | "pull-requests" | "incidents" | "code" | "observatory" | "release";

export function V4Intelligence({ mode }: { mode: V4Mode }) {
  const [status, setStatus] = useState("Loading RHD v4 intelligence");
  const [mission, setMission] = useState<Record<string, unknown>>({});
  const [mesh, setMesh] = useState<Record<string, unknown>>({});
  const [pipeline, setPipeline] = useState<Record<string, unknown>>({});
  const [modelLab, setModelLab] = useState<Record<string, unknown>>({});
  const [observatory, setObservatory] = useState<Record<string, unknown>>({});
  const [map, setMap] = useState<Record<string, unknown>>({});

  useEffect(() => {
    async function load() {
      const [missionData, meshData, pipelineData, modelData, observatoryData, repositories] = await Promise.all([
        fetchV4MissionControl(),
        fetchV4AgentMesh(),
        fetchV4RagPipeline(),
        fetchV4ModelLab(),
        fetchV4Observatory(),
        fetchRepositories()
      ]);
      setMission(missionData);
      setMesh(meshData);
      setPipeline(pipelineData);
      setModelLab(modelData);
      setObservatory(observatoryData);
      const firstRepo = repositories[0];
      if (firstRepo) {
        setMap(await fetchV4NeuralMap(firstRepo.id));
      }
      setStatus("RHD v4 intelligence loaded");
    }
    load().catch((error: Error) => setStatus(error.message));
  }, []);

  const data = selectModeData(mode, mission, mesh, pipeline, modelLab, observatory, map);
  const capabilities = arrayOfRecords(mission.v4_capabilities);
  const agents = arrayOfRecords(mesh.agents);
  const stages = arrayOfRecords(pipeline.stages);
  const nodes = arrayOfRecords(map.nodes);
  const events = recordOf(observatory.events);

  return (
    <section className="space-y-5">
      <div>
        <p className="text-sm font-medium text-signal">{status}</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">{data.title}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">{data.copy}</p>
      </div>

      <div className="grid gap-4 xl:grid-cols-4">
        {data.tiles.map((tile) => (
          <Tile key={tile.label} icon={tile.icon} label={tile.label} value={tile.value} detail={tile.detail} />
        ))}
      </div>

      {mode === "mission" ? (
        <Panel icon={ShieldCheck} title="Capability Status">
          <div className="grid gap-3 lg:grid-cols-2">
            {capabilities.map((capability) => (
              <Row key={String(capability.name)} label={String(capability.name)} detail={String(capability.status)} />
            ))}
          </div>
        </Panel>
      ) : null}

      {mode === "map" || mode === "code" ? (
        <Panel icon={Map} title={mode === "code" ? "Code Intelligence Index" : "Repository Neural Map"}>
          <div className="grid gap-3 lg:grid-cols-2">
            {(nodes.length ? nodes.slice(0, 12) : [{ node_id: "awaiting-index", labels: ["Status"], properties: { status: map.status ?? "AWAITING_REPOSITORY_DATA" } }]).map((node) => (
              <Row key={String(node.node_id)} label={String(node.node_id)} detail={JSON.stringify(node.labels ?? node.properties)} />
            ))}
          </div>
        </Panel>
      ) : null}

      {mode === "pull-requests" ? (
        <Panel icon={GitPullRequest} title="PR Risk System">
          <div className="grid gap-3 lg:grid-cols-2">
            <Row label="Risk factors" detail="Auth, security, database, migration, deployment, permission, and code-symbol overlap are scored from synced PR evidence." />
            <Row label="Blast radius" detail="Affected components are inferred from PR metadata and indexed code symbols; missing file diffs are labeled as metadata-only." />
            <Row label="Reviewers" detail="Reviewer suggestions use observed author/symbol metadata only; no social graph is fabricated." />
            <Row label="Tests" detail="Recommendations map risk terms to backend, frontend, migration, and security checks." />
          </div>
        </Panel>
      ) : null}

      {mode === "incidents" || mode === "release" ? (
        <Panel icon={SearchCheck} title={mode === "release" ? "Release Intelligence" : "Incident Intelligence"}>
          <div className="grid gap-3 lg:grid-cols-2">
            {stages.map((stage) => (
              <Row key={String(stage.name)} label={String(stage.name)} detail={`${stage.status}: ${stage.implementation}`} />
            ))}
          </div>
        </Panel>
      ) : null}

      {mode === "observatory" ? (
        <Panel icon={RadioTower} title="Observatory Signals">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {Object.entries(events).map(([key, value]) => (
              <Row key={key} label={key.replaceAll("_", " ")} detail={String(value)} />
            ))}
          </div>
        </Panel>
      ) : null}
    </section>
  );
}

function selectModeData(
  mode: V4Mode,
  mission: Record<string, unknown>,
  mesh: Record<string, unknown>,
  pipeline: Record<string, unknown>,
  modelLab: Record<string, unknown>,
  observatory: Record<string, unknown>,
  map: Record<string, unknown>
) {
  const inventory = recordOf(mission.inventory);
  const eventCounts = recordOf(observatory.events);
  const gateway = recordOf(modelLab.gateway);
  const nodes = arrayOfRecords(map.nodes);
  const modeData = {
    mission: {
      title: "RHD Mission Control",
      copy: "RepoGuardian powered by RHD coordinates repository health, evidence-grounded reasoning, model governance, and human-controlled execution from one operational surface.",
      tiles: [
        { icon: ShieldCheck, label: "Mode", value: String(mission.operating_mode ?? "READ_ONLY"), detail: "Anonymous public users cannot execute write actions" },
        { icon: Waypoints, label: "Repositories", value: String(inventory.repositories ?? 0), detail: "Synced repository inventory" },
        { icon: AlertTriangle, label: "Issues", value: String(inventory.issues ?? 0), detail: "Backlog evidence available to RHD" },
        { icon: GitPullRequest, label: "PRs", value: String(inventory.pull_requests ?? 0), detail: "Risk analysis uses synced PR data" }
      ]
    },
    map: {
      title: "RHD Intelligence Map",
      copy: "Repository graph, code symbols, issues, pull requests, and releases are exposed as a scoped knowledge map for retrieval and blast-radius reasoning.",
      tiles: [
        { icon: Map, label: "Map Status", value: String(map.status ?? "LOADING"), detail: "Graph and code index readiness" },
        { icon: Waypoints, label: "Nodes", value: String(nodes.length), detail: "Preview nodes loaded from the first repository" },
        { icon: BrainCircuit, label: "RAG", value: String(pipeline.status ?? "ACTIVE"), detail: "Hybrid retrieval pipeline" },
        { icon: ShieldCheck, label: "Grounding", value: "ON", detail: "Repository isolation critic" }
      ]
    },
    "pull-requests": {
      title: "RHD Pull Request Intelligence",
      copy: "PR risk, blast radius, reviewer hints, and test recommendations are derived from synced pull request metadata and indexed source-code symbols.",
      tiles: [
        { icon: GitPullRequest, label: "Risk Engine", value: "DETERMINISTIC", detail: "No fabricated diffs or reviewers" },
        { icon: Map, label: "Blast Radius", value: "EVIDENCE", detail: "PR text plus code-symbol overlap" },
        { icon: ShieldCheck, label: "Execution", value: "HUMAN GATED", detail: "Never merges or writes automatically" },
        { icon: BrainCircuit, label: "ML Status", value: "FALLBACK", detail: "Predictive ML awaits labeled data" }
      ]
    },
    incidents: {
      title: "RHD Incident Intelligence",
      copy: "Incident investigations combine agentic RAG, release/PR/issue timelines, and cautious hypotheses that label correlation instead of pretending causation.",
      tiles: [
        { icon: SearchCheck, label: "Investigator", value: "ACTIVE", detail: "Repository-scoped evidence search" },
        { icon: RadioTower, label: "Timelines", value: "SYNCED", detail: "Issues, PRs, releases, and events" },
        { icon: ShieldCheck, label: "Critic", value: "ON", detail: "Evidence coverage and isolation checks" },
        { icon: AlertTriangle, label: "Causation", value: "CAUTIOUS", detail: "Correlation is explicitly labeled" }
      ]
    },
    code: {
      title: "RHD Code Intelligence",
      copy: "Bounded code scanning extracts file features and symbols for Code-RAG, root-cause candidates, and PR blast-radius analysis.",
      tiles: [
        { icon: BrainCircuit, label: "Code-RAG", value: "INDEXED", detail: "Active when code documents or symbols exist" },
        { icon: Waypoints, label: "Symbols", value: String(nodes.filter((node) => JSON.stringify(node.labels).includes("CodeSymbol")).length), detail: "Functions and classes in the graph preview" },
        { icon: Map, label: "Graph", value: String(map.status ?? "LOADING"), detail: "Repository knowledge map" },
        { icon: ShieldCheck, label: "Sandbox", value: "BOUNDED", detail: "Serverless filesystem scanning remains disabled" }
      ]
    },
    observatory: {
      title: "RHD Observatory",
      copy: "Operational traces expose audit events, conversations, model telemetry, PR risk assessments, and incident investigations without exposing private reasoning.",
      tiles: [
        { icon: RadioTower, label: "Audit", value: String(eventCounts.audit_log ?? 0), detail: "Safe event trail rows" },
        { icon: BrainCircuit, label: "Model Telemetry", value: String(eventCounts.model_telemetry ?? 0), detail: "Provider calls when recorded" },
        { icon: GitPullRequest, label: "PR Risk", value: String(eventCounts.pr_risk_assessments ?? 0), detail: "Persisted assessments" },
        { icon: SearchCheck, label: "Incidents", value: String(eventCounts.incident_investigations ?? 0), detail: "Persisted investigations" }
      ]
    },
    release: {
      title: "RHD Release Intelligence",
      copy: "Release intelligence connects release notes, post-release issues, related PRs, and RAG evidence to flag likely regressions without overstating proof.",
      tiles: [
        { icon: RadioTower, label: "Temporal Lens", value: "ACTIVE", detail: "Release and recency strategies" },
        { icon: GitPullRequest, label: "PR Context", value: "ACTIVE", detail: "Related PR evidence" },
        { icon: AlertTriangle, label: "Regression", value: "CAUTIOUS", detail: "Signals are not causation" },
        { icon: BrainCircuit, label: "Gateway Tasks", value: String(arrayOfRecords(gateway.tasks).length || "V4"), detail: "Task-aware provider routing" }
      ]
    }
  } satisfies Record<V4Mode, { title: string; copy: string; tiles: Array<{ icon: LucideIcon; label: string; value: string; detail: string }> }>;
  return modeData[mode];
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
      <div className="mt-2 break-words text-lg font-semibold text-ink">{value}</div>
      <div className="mt-1 text-xs leading-5 text-slate-600">{detail}</div>
    </div>
  );
}

function Row({ label, detail }: { label: string; detail: string }) {
  return (
    <div className="rounded-md border border-line bg-panel p-4">
      <div className="font-semibold capitalize text-ink">{label}</div>
      <div className="mt-2 break-words text-sm leading-5 text-slate-600">{detail}</div>
    </div>
  );
}

function recordOf(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function arrayOfRecords(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && !Array.isArray(item)) : [];
}
