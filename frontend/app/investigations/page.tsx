import { Sidebar } from "@/components/ui/sidebar";
import { InvestigationWorkspace } from "@/components/repository/investigation-workspace";

export default function InvestigationsPage() {
  return (
    <main className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <section className="min-w-0 flex-1 px-5 py-6 md:px-8">
        <InvestigationWorkspace />
      </section>
    </main>
  );
}
