import { ReviewQueue } from "@/components/review/review-queue";
import { Sidebar } from "@/components/ui/sidebar";

export default function ReviewQueuePage() {
  return (
    <main className="flex min-h-screen">
      <Sidebar />
      <section className="flex-1 px-8 py-7">
        <ReviewQueue />
      </section>
    </main>
  );
}
