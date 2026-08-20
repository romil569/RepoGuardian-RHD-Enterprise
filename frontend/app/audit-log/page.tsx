import { AuditLog } from "@/components/audit/audit-log";
import { Sidebar } from "@/components/ui/sidebar";

export default function AuditLogPage() {
  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex-1 px-8 py-7">
        <AuditLog />
      </section>
    </main>
  );
}
