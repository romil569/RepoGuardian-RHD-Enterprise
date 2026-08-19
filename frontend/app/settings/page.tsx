import { Sidebar } from "@/components/ui/sidebar";

export default function SettingsPage() {
  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex-1 px-8 py-7">
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="mt-3 text-sm text-slate-600">Demo repository allow-list and credentials are configured through environment variables.</p>
      </section>
    </main>
  );
}
