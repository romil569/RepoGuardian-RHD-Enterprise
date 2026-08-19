import { Sidebar } from "@/components/ui/sidebar";
import { StatusPanel } from "@/components/dashboard/status-panel";

export default function Page() {
  const demoRepository = process.env.NEXT_PUBLIC_DEMO_GITHUB_REPOSITORY;

  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex-1 px-8 py-7">
        <div className="max-w-6xl">
          <p className="text-sm font-medium text-signal">Agentic Repository Intelligence & Maintenance</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal text-ink">RepoGuardian</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            A maintainer-oriented foundation for repository health, issue triage, and safe demo-only automation.
          </p>
          <div className="mt-7">
            <StatusPanel demoRepository={demoRepository} />
          </div>
        </div>
      </section>
    </main>
  );
}
