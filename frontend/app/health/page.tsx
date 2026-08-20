import { HealthDashboard } from "@/components/dashboard/health-dashboard";
import { Sidebar } from "@/components/ui/sidebar";

export default function HealthPage() {
  return (
    <main className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <section className="min-w-0 flex-1 px-5 py-6 md:px-8">
        <HealthDashboard />
      </section>
    </main>
  );
}
