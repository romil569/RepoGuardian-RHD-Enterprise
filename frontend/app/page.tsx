import { Sidebar } from "@/components/ui/sidebar";
import { OverviewDashboard } from "@/components/dashboard/overview-dashboard";

export default function Page() {
  return (
    <main className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <section className="min-w-0 flex-1 px-5 py-6 md:px-8">
        <div className="max-w-7xl">
          <p className="text-sm font-medium text-signal">RepoGuardian powered by RHD — Repository Health Director</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal text-ink">RHD Autonomous Repository Intelligence</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
            Paste a GitHub repository. RHD syncs, builds context, investigates, validates evidence, prioritizes, and recommends while humans control external action.
          </p>
          <div className="mt-7">
            <OverviewDashboard />
          </div>
        </div>
      </section>
    </main>
  );
}
