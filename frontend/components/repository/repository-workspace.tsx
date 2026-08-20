"use client";

/* eslint-disable react-hooks/exhaustive-deps, react-hooks/set-state-in-effect */

import { RefreshCw, Search, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import {
  connectRepository,
  fetchIssues,
  fetchPullRequests,
  fetchReleases,
  fetchRepositories,
  searchRepository,
  syncRepository
} from "@/services/system";
import type { Issue, PullRequest, Release, Repository, SearchResult } from "@/types/system";

const demoRepository = process.env.NEXT_PUBLIC_DEMO_GITHUB_REPOSITORY ?? "romil569/RepoGuardian-Demo";

export function RepositoryWorkspace() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selected, setSelected] = useState<Repository | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [pullRequests, setPullRequests] = useState<PullRequest[]>([]);
  const [releases, setReleases] = useState<Release[]>([]);
  const [query, setQuery] = useState("authentication fails after latest update");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [status, setStatus] = useState("Loading repositories");
  const [busy, setBusy] = useState(false);

  async function load() {
    const repos = await fetchRepositories();
    setRepositories(repos);
    const repo = repos[0] ?? null;
    setSelected(repo);
    if (repo) {
      await loadRepositoryData(repo);
    }
    setStatus(repo ? "Repository loaded" : "No repository connected");
  }

  async function loadRepositoryData(repo: Repository) {
    const [nextIssues, nextPrs, nextReleases] = await Promise.all([
      fetchIssues(repo.id),
      fetchPullRequests(repo.id),
      fetchReleases(repo.id)
    ]);
    setIssues(nextIssues);
    setPullRequests(nextPrs);
    setReleases(nextReleases);
  }

  useEffect(() => {
    load().catch((error: Error) => setStatus(error.message));
  }, []);

  async function handleConnect() {
    setBusy(true);
    setStatus("Connecting repository");
    try {
      const response = await connectRepository(demoRepository);
      setSelected(response.repository);
      await load();
      setStatus("Repository connected");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Connection failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSync() {
    if (!selected) return;
    setBusy(true);
    setStatus("Synchronizing repository");
    try {
      const response = await syncRepository(selected.id);
      await loadRepositoryData(selected);
      setStatus(`Sync complete: ${response.issues_added} issues added, ${response.issues_updated} updated`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Sync failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSearch() {
    if (!selected || !query.trim()) return;
    setBusy(true);
    try {
      setResults(await searchRepository(selected.id, query));
      setStatus("Repository search complete");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-line bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-signal">
              <ShieldCheck size={17} aria-hidden="true" />
              Demo allow-list: {demoRepository}
            </div>
            <h1 className="mt-2 text-2xl font-semibold">{selected?.full_name ?? "No repository connected"}</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">{selected?.description ?? "Connect the existing demo repository and synchronize GitHub data."}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={handleConnect} disabled={busy} className="rounded-md border border-line px-3 py-2 text-sm font-medium hover:bg-panel">
              Connect
            </button>
            <button onClick={handleSync} disabled={!selected || busy} className="inline-flex items-center gap-2 rounded-md bg-signal px-3 py-2 text-sm font-medium text-white disabled:opacity-50">
              <RefreshCw size={16} aria-hidden="true" />
              Sync
            </button>
          </div>
        </div>
        <p className="mt-4 text-sm text-slate-600">{status}</p>
      </section>

      {selected ? (
        <>
          <section className="grid gap-4 md:grid-cols-4">
            <Metric label="Open issues" value={issues.filter((issue) => issue.state === "OPEN").length} />
            <Metric label="Pull requests" value={pullRequests.length} />
            <Metric label="Releases" value={releases.length} />
            <Metric label="Last sync" value={selected.last_synced_at ? new Date(selected.last_synced_at).toLocaleString() : "Not synced"} />
          </section>

          <section className="rounded-md border border-line bg-white p-5">
            <div className="flex flex-wrap gap-2">
              <input value={query} onChange={(event) => setQuery(event.target.value)} className="min-w-0 flex-1 rounded-md border border-line px-3 py-2 text-sm" />
              <button onClick={handleSearch} disabled={busy} className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium hover:bg-panel">
                <Search size={16} aria-hidden="true" />
                Search
              </button>
            </div>
            <div className="mt-4 space-y-3">
              {results.map((result) => (
                <a key={`${result.source_type}-${result.source_id}`} href={result.source_url ?? "#"} target="_blank" className="block rounded-md border border-line p-3 hover:bg-panel">
                  <div className="text-sm font-semibold">{result.source_type} {result.github_number ? `#${result.github_number}` : ""}: {result.title}</div>
                  <p className="mt-1 text-sm text-slate-600">{result.snippet}</p>
                  <p className="mt-1 text-xs text-slate-500">score {result.relevance_score.toFixed(3)}</p>
                </a>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <div className="text-xs font-medium uppercase text-slate-500">{label}</div>
      <div className="mt-2 text-xl font-semibold">{value}</div>
    </div>
  );
}
