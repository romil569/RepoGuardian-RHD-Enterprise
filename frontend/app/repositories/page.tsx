import { Sidebar } from "@/components/ui/sidebar";
import { RepositoryWorkspace } from "@/components/repository/repository-workspace";

export default function RepositoriesPage() {
  return (
    <main className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <section className="min-w-0 flex-1 px-5 py-6 md:px-8">
        <RepositoryWorkspace />
      </section>
    </main>
  );
}
