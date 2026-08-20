import { SettingsPanel } from "@/components/dashboard/settings-panel";
import { Sidebar } from "@/components/ui/sidebar";

export default function SettingsPage() {
  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex-1 px-8 py-7">
        <SettingsPanel />
      </section>
    </main>
  );
}
