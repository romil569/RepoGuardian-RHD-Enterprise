import { McpMatrix } from "@/components/platform/mcp-matrix";
import { Sidebar } from "@/components/ui/sidebar";

export default function McpPage() {
  return (
    <main className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <section className="min-w-0 flex-1 px-5 py-6 md:px-8">
        <McpMatrix />
      </section>
    </main>
  );
}
