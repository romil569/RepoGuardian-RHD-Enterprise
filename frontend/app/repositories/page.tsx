import { Sidebar } from "@/components/ui/sidebar";
import { RepositoryWorkspace } from "@/components/repository/repository-workspace";

export default function RepositoriesPage() {
  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex-1 px-8 py-7">
        <RepositoryWorkspace />
      </section>
    </main>
  );
}
