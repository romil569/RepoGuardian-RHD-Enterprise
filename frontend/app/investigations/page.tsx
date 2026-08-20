import { Sidebar } from "@/components/ui/sidebar";
import { InvestigationWorkspace } from "@/components/repository/investigation-workspace";

export default function InvestigationsPage() {
  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex-1 px-8 py-7">
        <InvestigationWorkspace />
      </section>
    </main>
  );
}
