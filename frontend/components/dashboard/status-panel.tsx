import { CheckCircle2, CircleDashed, Database, Github } from "lucide-react";

type StatusPanelProps = {
  demoRepository?: string;
};

export function StatusPanel({ demoRepository }: StatusPanelProps) {
  return (
    <section className="grid gap-4 md:grid-cols-3">
      <div className="rounded-md border border-line bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Backend</h2>
          <CheckCircle2 className="text-signal" size={19} aria-hidden="true" />
        </div>
        <p className="mt-3 text-sm text-slate-600">FastAPI foundation is configured with health and system status endpoints.</p>
      </div>
      <div className="rounded-md border border-line bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Database</h2>
          <Database className="text-amber" size={19} aria-hidden="true" />
        </div>
        <p className="mt-3 text-sm text-slate-600">PostgreSQL with pgvector is Docker-ready for local development.</p>
      </div>
      <div className="rounded-md border border-line bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Demo Repository</h2>
          <Github className="text-slate-700" size={19} aria-hidden="true" />
        </div>
        <p className="mt-3 truncate text-sm text-slate-600">{demoRepository || "Configured after GitHub authentication"}</p>
      </div>
      <div className="rounded-md border border-dashed border-line bg-white p-5 md:col-span-3">
        <div className="flex items-center gap-3">
          <CircleDashed className="text-slate-500" size={19} aria-hidden="true" />
          <h2 className="text-sm font-semibold">Repository Connection</h2>
        </div>
        <p className="mt-3 text-sm text-slate-600">Connectors and AI investigations are intentionally reserved for the next implementation prompt.</p>
      </div>
    </section>
  );
}
