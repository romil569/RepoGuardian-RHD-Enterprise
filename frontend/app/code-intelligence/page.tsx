import { V4Intelligence } from "@/components/platform/v4-intelligence";
import { Sidebar } from "@/components/ui/sidebar";

export default function CodeIntelligencePage() {
  return (
    <main className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <section className="min-w-0 flex-1 px-5 py-6 md:px-8">
        <V4Intelligence mode="code" />
      </section>
    </main>
  );
}
