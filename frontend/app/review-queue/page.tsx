import { ReviewQueue } from "@/components/review/review-queue";
import { Sidebar } from "@/components/ui/sidebar";

export default function ReviewQueuePage() {
  return (
    <main className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <section className="min-w-0 flex-1 px-5 py-6 md:px-8">
        <ReviewQueue />
      </section>
    </main>
  );
}
