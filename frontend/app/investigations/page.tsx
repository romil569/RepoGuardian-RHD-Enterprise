import { Sidebar } from "@/components/ui/sidebar";

export default function InvestigationsPage() {
  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex-1 px-8 py-7">
        <h1 className="text-2xl font-semibold">Investigations</h1>
        <p className="mt-3 text-sm text-slate-600">AI investigation workflows are not implemented in Prompt 1.</p>
      </section>
    </main>
  );
}
