"use client";

import {
  Bot,
  ChevronLeft,
  ChevronRight,
  CircleStop,
  Download,
  GitBranch,
  Image,
  Mic,
  Paperclip,
  PanelRight,
  Plus,
  Search,
  Send,
  Sparkles,
  Waypoints
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { askRHD, fetchRepositories, fetchV5Architecture, fetchV51AnalysisJob, fetchV5Workspace, startV51RepositoryAnalysis } from "@/services/system";
import type { Repository, RHDQueryResponse, RHDReview, V51AnalysisJob } from "@/types/system";

type ChatMessage = {
  id: string;
  role: "user" | "rhd" | "system" | "artifact" | "evidence";
  title?: string;
  content: string;
  trace?: string[];
};

const examplePrompts = [
  "Review architecture",
  "Find risky code",
  "Explain a PR",
  "Investigate a bug",
  "Generate architecture diagram",
  "Show duplicate issues",
  "Review release risk"
];

const demoRepositoryUrl = "https://github.com/romil569/RepoGuardian-Demo";
const selectedRepositoryStorageKey = "repoguardian.v5.selectedRepositoryId";

const toolLinks = [
  ["/mission-control", "Mission Control"],
  ["/intelligence-map", "Intelligence Map"],
  ["/pull-requests", "PR Intelligence"],
  ["/incidents", "Incidents"],
  ["/code-intelligence", "Code"],
  ["/review-queue", "Review Queue"],
  ["/observatory", "Observatory"]
];

function restoredArtifactMessages(result: Record<string, unknown>): ChatMessage[] {
  const artifact = primaryArtifact(arrayOfRecords(result.artifacts));
  if (!artifact) return [];
  return [
    {
      id: crypto.randomUUID(),
      role: "rhd",
      title: "Repository analysis restored",
      content: `Loaded persisted architecture artifacts for ${repositoryNameFromArchitecture(result)}. Ask a follow-up to continue the review.`
    },
    artifactMessage(artifact)
  ];
}

export function ChatWorkspace() {
  const [workspace, setWorkspace] = useState<Record<string, unknown>>({});
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [repository, setRepository] = useState<Repository | null>(null);
  const [review, setReview] = useState<RHDReview | null>(null);
  const [architecture, setArchitecture] = useState<Record<string, unknown> | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionContext, setSessionContext] = useState<Record<string, unknown>>({});
  const [status, setStatus] = useState("Ready");
  const [busy, setBusy] = useState(false);
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [activeTab, setActiveTab] = useState("Context");

  useEffect(() => {
    async function load() {
      const [workspaceData, repoData] = await Promise.all([fetchV5Workspace(), fetchRepositories()]);
      setWorkspace(workspaceData);
      setRepositories(repoData);
      const storedRepositoryId = Number(window.localStorage.getItem(selectedRepositoryStorageKey) ?? "");
      const selectedRepo = repoData.find((item) => item.id === storedRepositoryId) ?? repoData[0] ?? null;
      setRepository(selectedRepo);
      if (selectedRepo) {
        fetchV5Architecture(selectedRepo.id)
          .then((result) => {
            setArchitecture(result);
            const restored = restoredArtifactMessages(result);
            if (restored.length) {
              setMessages((current) => (current.length ? current : restored));
            }
          })
          .catch(() => setArchitecture(null));
      }
    }
    load().catch(() => setStatus("Ready · context unavailable"));
  }, []);

  const detectedRepository = useMemo(() => parseRepositoryInput(input), [input]);
  const conversations = arrayOfRecords(workspace.conversations);
  const usage = recordOf(workspace.usage);
  const capabilities = recordOf(workspace.capabilities);
  const artifacts = arrayOfRecords(architecture?.artifacts);
  const visibleArtifact = primaryArtifact(artifacts);

  async function submit(nextInput = input) {
    const text = nextInput.trim();
    if (!text || busy) return;
    setInput("");
    setBusy(true);
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: text }]);
    try {
      const repoName = parseRepositoryInput(text);
      if (repoName) {
        await analyzeRepository(repoName);
      } else if (repository) {
        await askQuestion(text);
      } else {
        setMessages((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            role: "rhd",
            title: "Repository needed",
            content: "Give me a GitHub repository first, then I can ground answers in synchronized issues, pull requests, releases, code intelligence, and RHD evidence."
          }
        ]);
      }
    } finally {
      setBusy(false);
    }
  }

  async function analyzeRepository(repoInput: string) {
    setStatus("Starting analysis");
    pushSystem(`RHD is analyzing ${repoInput}`);
    const started = await startV51RepositoryAnalysis({
      repository: repoInput,
      session_id: String(sessionContext.session_id ?? ""),
      conversation_id: String(sessionContext.session_id ?? ""),
      requested_depth: "bounded"
    });
    setRepository(started.repository);
    window.localStorage.setItem(selectedRepositoryStorageKey, String(started.repository.id));
    setSessionContext((current) => ({ ...current, session_id: started.session_id, repository_id: started.repository_id }));
    setRepositories((current) => [started.repository, ...current.filter((item) => item.id !== started.repository.id)]);
    await pollAnalysisJob(started.job_id);
  }

  async function pollAnalysisJob(jobId: string) {
    let latest: V51AnalysisJob | null = null;
    const seenStages = new Set<string>();
    for (let attempt = 0; attempt < 42; attempt += 1) {
      latest = await fetchV51AnalysisJob(jobId);
      const stageLabel = latest.message || latest.current_stage || latest.status;
      setStatus(`${stageLabel} · ${latest.progress}%`);
      if (stageLabel && !seenStages.has(stageLabel)) {
        seenStages.add(stageLabel);
        pushSystem(`${stageLabel} (${latest.progress}%)`);
      }
      if (latest.repository) {
        setRepository(latest.repository);
        window.localStorage.setItem(selectedRepositoryStorageKey, String(latest.repository.id));
      }
      if (latest.status === "COMPLETED" || latest.status === "FAILED" || latest.status === "CANCELLED") break;
      await new Promise((resolve) => setTimeout(resolve, 1200));
    }
    if (!latest) throw new Error("Repository analysis did not start");
    if (latest.status === "FAILED") throw new Error(latest.error ?? "Repository analysis failed");
    if (latest.status !== "COMPLETED") throw new Error("Repository analysis did not complete before the polling limit");
    setReview(latest.review ?? null);
    setArchitecture(latest.architecture ?? null);
    if (latest.session_id || latest.repository?.id) {
      setSessionContext((current) => ({ ...current, session_id: latest.session_id ?? current.session_id, repository_id: latest.repository?.id ?? current.repository_id }));
    }
    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "rhd",
        title: "Repository analysis complete",
        content: completionText(latest)
      }
    ]);
    const firstArtifact = primaryArtifact(arrayOfRecords(latest.architecture?.artifacts));
    if (firstArtifact) {
      appendArtifactMessage(firstArtifact);
    }
    setStatus("Analyzed");
  }

  async function askQuestion(question: string) {
    if (!repository) return;
    if (architecture && /architecture|diagram|backend only|database flow|data flow|ai components/i.test(question)) {
      const firstArtifact = primaryArtifact(arrayOfRecords(architecture.artifacts));
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "rhd",
          title: "Architecture explanation",
          content: firstArtifact
            ? `This architecture is grounded in the generated ${String(firstArtifact.title)} artifact for ${repository.full_name}. It uses synchronized source-tree, code-symbol, issue, PR, release, and indexed evidence. Open the Architecture context tab or download the SVG/Mermaid artifact for the exact graph.`
            : "I couldn't infer a reliable architecture from the available repository evidence."
        }
      ]);
      return;
    }
    setStatus("RHD is investigating");
    const response: RHDQueryResponse = await askRHD(repository.id, question, sessionContext);
    setSessionContext(response.context);
    setMessages((current) => [...current, messageFromAnswer(response)]);
    setStatus("Ready");
  }

  async function loadArchitecture(repositoryId: number) {
    const result = await fetchV5Architecture(repositoryId);
    setArchitecture(result);
    const firstArtifact = primaryArtifact(arrayOfRecords(result.artifacts));
    if (firstArtifact) {
      appendArtifactMessage(firstArtifact);
    }
  }

  function appendArtifactMessage(artifact: Record<string, unknown>) {
    const next = artifactMessage(artifact);
    setMessages((current) => {
      if (current.some((message) => message.role === "artifact" && message.title === next.title)) return current;
      return [...current, next];
    });
  }

  function pushSystem(content: string) {
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "system", content }]);
  }

  function downloadSvg(artifact: Record<string, unknown>) {
    const blob = new Blob([String(artifact.svg ?? "")], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${String(artifact.id ?? "rhd-architecture")}.svg`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="flex min-h-screen bg-[#f7f7f5] text-[#17191f]">
      <aside className={`${leftOpen ? "hidden md:flex" : "hidden md:flex md:w-16"} min-h-screen w-[292px] shrink-0 flex-col border-r border-[#dedede] bg-[#fbfbfa] px-3 py-4`}>
        <div className="flex items-center justify-between">
          {leftOpen ? (
            <div>
              <div className="text-sm font-semibold">RepoGuardian</div>
              <div className="text-xs text-[#737780]">RHD</div>
            </div>
          ) : null}
          <button aria-label="Collapse sidebar" onClick={() => setLeftOpen(!leftOpen)} className="grid h-9 w-9 place-items-center rounded-md border border-[#dedede] bg-white">
            {leftOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
          </button>
        </div>
        {leftOpen ? (
          <>
            <button className="mt-5 inline-flex h-11 items-center justify-center gap-2 rounded-md bg-[#191b20] px-4 text-sm font-semibold text-white">
              <Plus size={16} />
              New Conversation
            </button>
            <div className="mt-3 flex items-center gap-2 rounded-md border border-[#dedede] bg-white px-3 py-2 text-sm text-[#737780]">
              <Search size={15} />
              Search chats
            </div>
            <SidebarSection title="Chats" rows={conversations.map((item) => String(item.title))} fallback={["RepoGuardian-Demo Review", "Authentication Incident", "PR #42 Analysis"]} />
            <SidebarSection title="Repositories" rows={repositories.map((item) => item.full_name)} fallback={["Paste a repository to begin"]} mono />
            <SidebarSection title="Tools" rows={toolLinks.map((item) => item[1])} fallback={[]} />
            <div className="mt-auto rounded-md border border-[#dedede] bg-white p-3">
              <div className="flex items-center gap-3">
                <div className="grid h-9 w-9 place-items-center rounded-full bg-[#eceef3] text-xs font-bold">GS</div>
                <div>
                  <div className="text-sm font-semibold">Guest Session</div>
                  <div className="text-xs text-[#737780]">Public Repository Mode</div>
                </div>
              </div>
              <div className="mt-3 grid gap-2 text-xs text-[#737780]">
                <span>Plan: Public demo</span>
                <span>Usage: {String(usage.token_usage_label ?? "N/A - deterministic execution")}</span>
              </div>
            </div>
          </>
        ) : null}
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-[#dedede] bg-[#fdfdfc]/90 px-4 backdrop-blur">
          <div className="flex items-center gap-3">
            <button onClick={() => setLeftOpen(!leftOpen)} className="grid h-9 w-9 place-items-center rounded-md border border-[#dedede] bg-white md:hidden">
              <ChevronRight size={16} />
            </button>
            <div>
              <div className="text-sm font-semibold">RHD Conversation</div>
              <div className="text-xs text-[#737780]">{repository?.full_name ?? "No repository selected"} · {status}{repository?.last_synced_at ? ` · synced ${new Date(repository.last_synced_at).toLocaleString()}` : ""}</div>
            </div>
          </div>
          <button onClick={() => setRightOpen(!rightOpen)} className="inline-flex h-9 items-center gap-2 rounded-md border border-[#dedede] bg-white px-3 text-sm">
            <PanelRight size={16} />
            Context
          </button>
        </header>

        <div className="flex-1 overflow-auto px-4 py-6">
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {!messages.length ? <Welcome detectedRepository={detectedRepository} repositorySelected={Boolean(repository)} onPrompt={setInput} onAnalyze={() => detectedRepository && submit(detectedRepository)} onDemo={() => submit(demoRepositoryUrl)} /> : null}
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {visibleArtifact ? <ArtifactCard key={String(visibleArtifact.id)} artifact={visibleArtifact} onDownload={() => downloadSvg(visibleArtifact)} /> : null}
          </div>
        </div>

        <div className="border-t border-[#dedede] bg-[#fdfdfc] p-4">
          <div className="mx-auto max-w-3xl rounded-2xl border border-[#cfd3dc] bg-white p-3 shadow-[0_12px_40px_rgba(22,24,29,0.08)]">
            {detectedRepository ? (
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-[#f3f5f9] px-3 py-2 text-sm">
                <span><span className="font-semibold">Repository detected</span> · <span className="font-mono">{detectedRepository}</span></span>
                <button onClick={() => submit(detectedRepository)} disabled={busy} className="rounded-md bg-[#191b20] px-3 py-1.5 text-xs font-semibold text-white">Analyze Repository</button>
              </div>
            ) : null}
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === "Enter") submit();
              }}
              placeholder="Ask RHD about this repository..."
              className="max-h-40 min-h-16 w-full resize-none border-0 bg-transparent text-[15px] leading-6 text-[#17191f] outline-none placeholder:text-[#8b9099]"
            />
            <div className="mt-2 flex items-center justify-between gap-3">
              <div className="flex items-center gap-1">
                <IconButton label="Attach">
                  <Paperclip size={17} />
                </IconButton>
                <IconButton label="Repository">
                  <GitBranch size={17} />
                </IconButton>
                <IconButton label="Voice">
                  <Mic size={17} />
                </IconButton>
                <span className="ml-2 rounded-full bg-[#f0f2f6] px-2 py-1 text-xs text-[#737780]">{String(usage.provider ?? "deterministic/template-router")}</span>
              </div>
              <button onClick={() => (busy ? setBusy(false) : submit())} disabled={!busy && !input.trim()} className="grid h-10 w-10 place-items-center rounded-full bg-[#191b20] text-white disabled:bg-[#c5c8d0]">
                {busy ? <CircleStop size={18} /> : <Send size={18} />}
              </button>
            </div>
          </div>
        </div>
      </section>

      {rightOpen ? (
        <aside className="hidden min-h-screen w-[360px] shrink-0 border-l border-[#dedede] bg-[#fbfbfa] p-4 xl:block">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold">Context</div>
            <button onClick={() => setRightOpen(false)} className="grid h-8 w-8 place-items-center rounded-md border border-[#dedede] bg-white">
              <ChevronRight size={16} />
            </button>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {["Context", "Architecture", "Code", "Evidence", "Agents", "Activity"].map((tab) => (
              <button key={tab} onClick={() => setActiveTab(tab)} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${activeTab === tab ? "bg-[#191b20] text-white" : "border border-[#dedede] bg-white text-[#555b66]"}`}>
                {tab}
              </button>
            ))}
          </div>
          <RightPanel tab={activeTab} repository={repository} review={review} architecture={architecture} capabilities={capabilities} />
        </aside>
      ) : null}
    </main>
  );
}

function Welcome({ detectedRepository, repositorySelected, onPrompt, onAnalyze, onDemo }: { detectedRepository: string | null; repositorySelected: boolean; onPrompt: (value: string) => void; onAnalyze: () => void; onDemo: () => void }) {
  return (
    <div className="pt-10 text-center">
      <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-[#d7dbe4] bg-white shadow-sm">
        <Sparkles size={23} />
      </div>
      <h1 className="mt-5 text-5xl font-semibold tracking-normal">RHD</h1>
      <p className="mt-2 text-lg text-[#555b66]">Repository Health Director</p>
      <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-[#737780]">Understand any software repository through conversation.</p>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[#555b66]">Give me a GitHub repository. I&apos;ll understand the engineering system behind it.</p>
      {detectedRepository ? (
        <button onClick={onAnalyze} className="mt-5 rounded-full bg-[#191b20] px-5 py-2.5 text-sm font-semibold text-white">Analyze {detectedRepository}</button>
      ) : null}
      <button onClick={onDemo} className="mt-5 rounded-full border border-[#d7dbe4] bg-white px-5 py-2.5 text-sm font-semibold text-[#17191f] shadow-sm">Try Demo Repository</button>
      <div className="mt-7 flex flex-wrap justify-center gap-2">
        {examplePrompts.map((prompt) => (
          <button key={prompt} disabled={!repositorySelected} onClick={() => onPrompt(prompt)} className="rounded-full border border-[#d7dbe4] bg-white px-3 py-2 text-sm text-[#555b66] shadow-sm hover:border-[#aeb5c3] disabled:cursor-not-allowed disabled:opacity-45">
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const Icon = message.role === "artifact" ? Image : message.role === "system" ? Waypoints : Bot;
  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser ? <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#eceef3]"><Icon size={16} /></div> : null}
      <div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-6 ${isUser ? "bg-[#191b20] text-white" : "border border-[#dedede] bg-white text-[#2b3038] shadow-sm"}`}>
        {message.title ? <div className="mb-1 text-xs font-bold uppercase text-[#737780]">{message.title}</div> : null}
        <p>{message.content}</p>
        {message.trace?.length ? (
          <div className="mt-3 border-t border-[#eceef3] pt-2 text-xs text-[#737780]">
            {message.trace.map((item) => <div key={item}>✓ {item}</div>)}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ArtifactCard({ artifact, onDownload }: { artifact: Record<string, unknown>; onDownload: () => void }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-[#d7dbe4] bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-[#eceef3] px-4 py-3">
        <div>
          <div className="text-sm font-semibold">{String(artifact.title)}</div>
          <div className="text-xs text-[#737780]">{String(artifact.grounding)}</div>
        </div>
        <button onClick={onDownload} className="inline-flex h-9 items-center gap-2 rounded-md border border-[#dedede] px-3 text-xs font-semibold">
          <Download size={15} />
          SVG
        </button>
      </div>
      <div className="overflow-auto bg-[#f7f8fb] p-4" dangerouslySetInnerHTML={{ __html: String(artifact.svg ?? "") }} />
      <details className="border-t border-[#eceef3] px-4 py-3 text-xs">
        <summary className="cursor-pointer font-semibold">Copy Mermaid</summary>
        <pre className="mt-2 overflow-auto rounded-md bg-[#f3f5f9] p-3 font-mono text-[11px] leading-5">{String(artifact.mermaid ?? "")}</pre>
      </details>
    </div>
  );
}

function RightPanel({ tab, repository, review, architecture, capabilities }: { tab: string; repository: Repository | null; review: RHDReview | null; architecture: Record<string, unknown> | null; capabilities: Record<string, unknown> }) {
  const artifacts = arrayOfRecords(architecture?.artifacts);
  const multimodal = recordOf(capabilities.multimodal);
  const attachments = recordOf(capabilities.attachments);
  const rows =
    tab === "Architecture"
      ? artifacts.map((item) => [String(item.title), String(item.grounding)])
      : tab === "Evidence"
        ? (review?.evidence ?? []).map((item) => [item.title, item.source_type ?? item.type ?? "evidence"])
        : tab === "Agents"
          ? [["Policy", "Human approval required"], ["Deterministic fallback", "Active"], ["Multimodal", String(multimodal.status ?? "PROVIDER_REQUIRED")]]
          : tab === "Code"
            ? [["Code-RAG", String(architecture?.status ?? "Awaiting repository evidence")], ["Attachments", arrayOfRecords(attachments.supported).length ? "Supported" : "Screenshots/text/source files"]]
            : [[repository?.full_name ?? "No repository", review?.executive_assessment.state ?? "Select or analyze a repository"], ["Voice", "Optional browser control"], ["Token usage", "N/A when deterministic"]];
  return (
    <div className="mt-5 space-y-3">
      {rows.map(([label, detail]) => (
        <div key={`${label}-${detail}`} className="rounded-xl border border-[#dedede] bg-white p-3">
          <div className="text-sm font-semibold">{label}</div>
          <div className="mt-1 text-xs leading-5 text-[#737780]">{detail}</div>
        </div>
      ))}
    </div>
  );
}

function SidebarSection({ title, rows, fallback, mono = false }: { title: string; rows: string[]; fallback: string[]; mono?: boolean }) {
  const items = rows.length ? rows : fallback;
  return (
    <div className="mt-5">
      <div className="mb-2 px-1 text-[11px] font-bold uppercase tracking-normal text-[#8b9099]">{title}</div>
      <div className="space-y-1">
        {items.slice(0, 7).map((item) => (
          <div key={item} className={`truncate rounded-md px-2 py-2 text-sm text-[#555b66] hover:bg-[#f0f2f6] ${mono ? "font-mono text-xs" : ""}`}>{item}</div>
        ))}
      </div>
    </div>
  );
}

function IconButton({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <button aria-label={label} title={label} className="grid h-9 w-9 place-items-center rounded-md text-[#555b66] hover:bg-[#f0f2f6]">
      {children}
    </button>
  );
}

function messageFromAnswer(response: RHDQueryResponse): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: "rhd",
    title: response.intent.replaceAll("_", " "),
    content: response.answer,
    trace: response.trace.map((item) => `${item.step}: ${item.summary}`)
  };
}

function parseRepositoryInput(value: string): string | null {
  const trimmed = value.trim();
  const github = trimmed.match(/^(?:https:\/\/)?github\.com\/([^/\s]+)\/([^/\s#?]+?)(?:\.git)?\/?$/i);
  const ownerRepo = trimmed.match(/^([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)$/);
  const match = github ?? ownerRepo;
  return match ? `${match[1]}/${match[2].replace(/\.git$/i, "")}` : null;
}

function artifactMessage(artifact: Record<string, unknown>): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: "artifact",
    title: String(artifact.title),
    content: String(artifact.grounding)
  };
}

function repositoryNameFromArchitecture(architecture: Record<string, unknown>) {
  const repo = recordOf(architecture.repository);
  return String(repo.full_name ?? "the repository");
}

function completionText(job: V51AnalysisJob) {
  const repo = job.repository?.full_name ?? "repository";
  const summary = job.completion_summary;
  if (!summary) {
    return `Analysis complete for ${repo}. Ask me anything about this repository.`;
  }
  return `Analysis complete for ${repo}.\n\nHealth: ${summary.health}\nArchitecture: ${summary.architecture}\nCode analyzed: ${summary.code_analyzed}\nIssues analyzed: ${summary.issues_analyzed}\nPRs analyzed: ${summary.prs_analyzed}\n\nAsk me anything about this repository.`;
}

function recordOf(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function arrayOfRecords(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && !Array.isArray(item)) : [];
}

function primaryArtifact(artifacts: Record<string, unknown>[]): Record<string, unknown> | undefined {
  return artifacts.find((artifact) => String(artifact.artifact_type ?? "").toUpperCase() === "SYSTEM" || /system architecture/i.test(String(artifact.title ?? ""))) ?? artifacts[0];
}
