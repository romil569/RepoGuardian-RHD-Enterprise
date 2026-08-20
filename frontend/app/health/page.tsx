import { HealthDashboard } from "@/components/dashboard/health-dashboard";
import { Sidebar } from "@/components/ui/sidebar";

export default function HealthPage() {
  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex-1 px-8 py-7">
        <HealthDashboard />
      </section>
    </main>
  );
}
