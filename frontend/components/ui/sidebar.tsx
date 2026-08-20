"use client";

import { Activity, Bot, ClipboardList, Code2, Command, FileClock, GitBranch, GitPullRequest, Home, ListChecks, Map, RadioTower, SearchCheck, ServerCog, Settings, ShieldCheck, Sparkles, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const sections: Array<{ title: string; items: Array<{ href: string; label: string; icon: LucideIcon; detail: string }> }> = [
  {
    title: "Command",
    items: [
      { href: "/", label: "Command Center", icon: Home, detail: "Live repository posture" },
      { href: "/mission-control", label: "Mission Control", icon: ShieldCheck, detail: "RHD v4 command layer" },
      { href: "/repositories", label: "Repositories", icon: GitBranch, detail: "Sync and semantic search" },
      { href: "/issues", label: "Issues", icon: ListChecks, detail: "Backlog intelligence" },
      { href: "/investigations", label: "Investigations", icon: SearchCheck, detail: "Agent evidence graph" },
      { href: "/review-queue", label: "Review Queue", icon: ClipboardList, detail: "Human-gated actions" }
    ]
  },
  {
    title: "Intelligence",
    items: [
      { href: "/health", label: "Repository Health", icon: Activity, detail: "Risk dimensions" },
      { href: "/weekly", label: "Weekly Brief", icon: FileClock, detail: "Maintainer briefing" },
      { href: "/intelligence-map", label: "Intelligence Map", icon: Map, detail: "Graph and Code-RAG" },
      { href: "/pull-requests", label: "Pull Requests", icon: GitPullRequest, detail: "Risk and blast radius" },
      { href: "/incidents", label: "Incidents", icon: SearchCheck, detail: "Root-cause timeline" },
      { href: "/code-intelligence", label: "Code Intelligence", icon: Code2, detail: "Symbols and files" },
      { href: "/release-intelligence", label: "Releases", icon: RadioTower, detail: "Regression signals" },
      { href: "/evaluation", label: "Evaluation", icon: ShieldCheck, detail: "Feedback quality" },
      { href: "/mcp", label: "MCP", icon: Wrench, detail: "Tool matrix" },
      { href: "/models", label: "Models", icon: Bot, detail: "Provider and ML cards" }
    ]
  },
  {
    title: "Operations",
    items: [
      { href: "/automation", label: "Automation", icon: RadioTower, detail: "Event-driven jobs" },
      { href: "/observatory", label: "Observatory", icon: Activity, detail: "Traces and telemetry" },
      { href: "/system", label: "System", icon: ServerCog, detail: "Runtime foundations" },
      { href: "/audit-log", label: "Audit Log", icon: FileClock, detail: "Safe event trail" },
      { href: "/settings", label: "Settings", icon: Settings, detail: "Policy and runtime" }
    ]
  }
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="static flex h-auto w-full shrink-0 flex-col border-b border-line bg-[#fbfbfa] px-4 py-5 md:sticky md:top-0 md:h-screen md:w-72 md:border-b-0 md:border-r">
      <div className="flex items-center gap-3 px-2">
        <div className="grid h-11 w-11 place-items-center rounded-md border border-line bg-white text-signal shadow-sm">
          <ShieldCheck size={22} aria-hidden={true} />
        </div>
        <div>
          <div className="text-base font-semibold text-ink">RepoGuardian</div>
          <div className="text-xs text-slate-500">powered by RHD</div>
        </div>
      </div>

      <div className="mt-5 rounded-md border border-line bg-white p-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase text-signal">
          <Sparkles size={14} aria-hidden={true} />
          Demo Target
        </div>
        <div className="mt-2 truncate text-sm font-semibold">romil569/RepoGuardian-Demo</div>
        <div className="mt-2 flex items-center gap-2 text-xs text-slate-600">
          <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_18px_rgba(110,231,183,0.8)]" />
          Safe write policy enabled
        </div>
      </div>

      <nav className="mt-5 flex min-h-0 flex-col gap-5 overflow-auto pr-1 md:flex-1">
        {sections.map((section) => (
          <div key={section.title}>
            <div className="mb-2 px-2 text-[0.68rem] font-bold uppercase tracking-normal text-slate-500">{section.title}</div>
            <div className="space-y-1">
              {section.items.map((item) => {
                const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`group flex items-center gap-3 rounded-md border px-3 py-2.5 text-sm transition ${
                      active ? "border-[#cfd6e6] bg-white text-ink shadow-sm" : "border-transparent text-slate-600 hover:border-line hover:bg-panel hover:text-ink"
                    }`}
                  >
                    <item.icon size={17} className={active ? "text-signal" : "text-slate-500 group-hover:text-signal"} aria-hidden={true} />
                    <span className="min-w-0">
                      <span className="block truncate font-semibold">{item.label}</span>
                      <span className="block truncate text-[0.68rem] text-slate-500">{item.detail}</span>
                    </span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="mt-4 rounded-md border border-line bg-panel p-3 text-xs text-slate-600">
        <div className="flex items-center gap-2 font-semibold text-ink">
          <Command size={14} aria-hidden={true} />
          RHD command layer
        </div>
        <p className="mt-1 leading-5">Navigate and search verified repository context from any screen.</p>
      </div>
    </aside>
  );
}
