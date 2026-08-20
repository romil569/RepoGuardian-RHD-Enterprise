"use client";

import { Command, ExternalLink, GitBranch, Search, ShieldCheck, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { fetchRepositories, searchRepository } from "@/services/system";
import type { Repository, SearchResult } from "@/types/system";

const commands = [
  { label: "Command Center", href: "/", tokens: ["home", "overview", "dashboard"] },
  { label: "Repositories", href: "/repositories", tokens: ["sync", "github", "rag", "search"] },
  { label: "Issues", href: "/issues", tokens: ["issue", "triage", "classification"] },
  { label: "Investigations", href: "/investigations", tokens: ["agent", "evidence", "duplicate", "security"] },
  { label: "Review Queue", href: "/review-queue", tokens: ["approval", "actions", "human", "policy"] },
  { label: "Repository Health", href: "/health", tokens: ["risk", "score", "signals"] },
  { label: "Weekly Brief", href: "/weekly", tokens: ["brief", "summary", "week"] },
  { label: "Evaluation", href: "/evaluation", tokens: ["feedback", "agreement", "quality"] },
  { label: "Audit Log", href: "/audit-log", tokens: ["events", "safe", "history"] },
  { label: "Settings", href: "/settings", tokens: ["policy", "runtime", "github"] }
];

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [repository, setRepository] = useState<Repository | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [status, setStatus] = useState("Repository search is ready when synced data exists");

  useEffect(() => {
    fetchRepositories()
      .then((repositories) => setRepository(repositories[0] ?? null))
      .catch(() => setRepository(null));
  }, []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const filteredCommands = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return commands;
    return commands.filter((item) => [item.label, item.href, ...item.tokens].some((value) => value.toLowerCase().includes(needle)));
  }, [query]);

  async function runRepositorySearch() {
    if (!repository || !query.trim()) return;
    setStatus("Searching verified repository context");
    try {
      setResults(await searchRepository(repository.id, query));
      setStatus("Repository search completed");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Repository search failed");
    }
  }

  function navigate(href: string) {
    setOpen(false);
    router.push(href);
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed right-5 top-5 z-40 hidden h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-slate-600 shadow-2xl shadow-black/20 backdrop-blur xl:inline-flex"
      >
        <Command size={16} aria-hidden={true} />
        Ctrl K
      </button>
      {open ? (
        <div className="fixed inset-0 z-50 bg-black/55 p-4 backdrop-blur-sm" onMouseDown={() => setOpen(false)}>
          <div className="mx-auto mt-16 w-full max-w-3xl overflow-hidden rounded-md border border-line bg-white shadow-2xl shadow-cyan-950/40" onMouseDown={(event) => event.stopPropagation()}>
            <div className="flex items-center gap-3 border-b border-line px-4 py-3">
              <Sparkles size={18} className="text-signal" aria-hidden={true} />
              <input
                autoFocus
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void runRepositorySearch();
                }}
                placeholder="Search routes or verified repository context..."
                className="h-11 min-w-0 flex-1 border-0 bg-transparent text-sm outline-none"
              />
              <button type="button" onClick={runRepositorySearch} disabled={!repository || !query.trim()} className="inline-flex h-9 items-center gap-2 rounded-md bg-signal px-3 text-sm font-semibold text-slate-950 disabled:opacity-40">
                <Search size={15} aria-hidden={true} />
                Search
              </button>
            </div>
            <div className="grid gap-0 md:grid-cols-[280px_1fr]">
              <div className="border-b border-line p-3 md:border-b-0 md:border-r">
                <div className="mb-2 px-2 text-xs font-semibold uppercase text-slate-500">Navigate</div>
                {filteredCommands.map((item) => (
                  <button key={item.href} type="button" onClick={() => navigate(item.href)} className="flex w-full items-center justify-between rounded-md px-2 py-2 text-left text-sm hover:bg-panel">
                    <span>{item.label}</span>
                    <GitBranch size={14} className="text-slate-500" aria-hidden={true} />
                  </button>
                ))}
              </div>
              <div className="min-h-[320px] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold">Verified Repository Context</div>
                    <p className="mt-1 text-xs text-slate-600">{repository?.full_name ?? "Connect and sync a repository first"}</p>
                  </div>
                  <ShieldCheck size={18} className="text-signal" aria-hidden={true} />
                </div>
                <p className="mt-4 text-sm text-slate-600">{status}</p>
                <div className="mt-4 space-y-2">
                  {results.map((item) => (
                    <a key={`${item.source_type}-${item.source_id}`} href={item.source_url ?? "#"} target="_blank" className="block rounded-md border border-line p-3 text-sm hover:bg-panel">
                      <div className="flex items-center gap-2 font-semibold">
                        <ExternalLink size={14} className="text-signal" aria-hidden={true} />
                        {item.source_type} {item.github_number ? `#${item.github_number}` : ""}: {item.title}
                      </div>
                      <p className="mt-1 text-xs leading-5 text-slate-600">{item.snippet}</p>
                    </a>
                  ))}
                  {!results.length ? <div className="rounded-md border border-line bg-panel p-4 text-sm text-slate-600">Press Enter or Search to query the existing RAG-backed repository index.</div> : null}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
