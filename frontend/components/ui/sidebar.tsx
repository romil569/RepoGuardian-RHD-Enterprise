import { Activity, GitBranch, Home, SearchCheck, Settings, ShieldCheck } from "lucide-react";
import Link from "next/link";

const items = [
  { href: "/", label: "Overview", icon: Home },
  { href: "/repositories", label: "Repositories", icon: GitBranch },
  { href: "/investigations", label: "Investigations", icon: SearchCheck },
  { href: "/health", label: "Repository Health", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings }
];

export function Sidebar() {
  return (
    <aside className="flex min-h-screen w-64 shrink-0 flex-col border-r border-line bg-white px-4 py-5">
      <div className="flex items-center gap-3 px-2">
        <div className="grid h-9 w-9 place-items-center rounded-md bg-signal text-white">
          <ShieldCheck size={20} aria-hidden="true" />
        </div>
        <div>
          <div className="text-sm font-semibold text-ink">RepoGuardian</div>
          <div className="text-xs text-slate-500">Maintainer assistant</div>
        </div>
      </div>
      <nav className="mt-8 flex flex-col gap-1">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-slate-650 hover:bg-panel"
          >
            <item.icon size={18} aria-hidden="true" />
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
