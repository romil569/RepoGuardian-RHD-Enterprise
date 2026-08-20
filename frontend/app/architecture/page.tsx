import { Database, GitBranch, Network, ServerCog, ShieldCheck, Workflow } from "lucide-react";

import { Sidebar } from "@/components/ui/sidebar";

const layers = [
  { label: "Vercel Web", detail: "Next.js public interface", icon: Network },
  { label: "Vercel FastAPI", detail: "Python serverless RHD API", icon: ServerCog },
  { label: "Neon PostgreSQL", detail: "Repositories, sessions, jobs, audit", icon: Database },
  { label: "pgvector", detail: "Repository-scoped retrieval", icon: GitBranch },
  { label: "Postgres Queue", detail: "Bounded staged analysis", icon: Workflow },
  { label: "RHD Guardrails", detail: "Read-only public action policy", icon: ShieldCheck },
];

export default function ArchitecturePage() {
  return (
    <main className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <section className="min-w-0 flex-1 px-5 py-6 md:px-8">
        <div className="max-w-6xl">
          <p className="text-sm font-medium text-signal">Vercel + Neon public deployment</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">RHD Production Architecture</h1>
          <div className="mt-7 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {layers.map((layer) => (
              <div key={layer.label} className="rounded-md border border-line bg-white p-5">
                <layer.icon size={18} className="text-signal" aria-hidden={true} />
                <h2 className="mt-3 text-sm font-semibold">{layer.label}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{layer.detail}</p>
              </div>
            ))}
          </div>
          <section className="mt-6 rounded-md border border-line bg-white p-5">
            <h2 className="text-sm font-semibold">Current Production Flow</h2>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Visitors connect public GitHub repositories through the Vercel frontend. The FastAPI serverless backend stores repository records, RHD sessions, staged jobs, audit events, and retrieval indexes in Neon PostgreSQL with pgvector. RHD answers with deterministic evidence-grounded analysis unless a cloud model provider is configured later.
            </p>
          </section>
        </div>
      </section>
    </main>
  );
}
