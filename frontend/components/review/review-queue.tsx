"use client";

/* eslint-disable react-hooks/set-state-in-effect */

import { CheckCircle2, ExternalLink, PlayCircle, RefreshCw, ShieldAlert, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { approveActionRecommendation, executeActionRecommendation, fetchActionRecommendation, fetchReviewQueue, rejectActionRecommendation } from "@/services/system";
import type { ActionRecommendation } from "@/types/system";

const filters = ["PENDING", "URGENT", "SECURITY", "POSSIBLE_DUPLICATE", "NEEDS_INFORMATION", "HIGH_PRIORITY", "FAILED_ACTIONS"];

export function ReviewQueue() {
  const [items, setItems] = useState<ActionRecommendation[]>([]);
  const [selected, setSelected] = useState<ActionRecommendation | null>(null);
  const [filter, setFilter] = useState("PENDING");
  const [status, setStatus] = useState("Loading review queue");

  async function load(activeFilter = filter) {
    const queue = await fetchReviewQueue(activeFilter);
    setItems(queue);
    setSelected(queue[0] ? await fetchActionRecommendation(queue[0].id) : null);
    setStatus(queue.length ? `${queue.length} recommendations loaded` : "No recommendations match this filter");
  }

  useEffect(() => {
    load().catch((error: Error) => setStatus(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function chooseFilter(value: string) {
    setFilter(value);
    setStatus("Loading review queue");
    await load(value);
  }

  async function refreshSelected(next: Promise<ActionRecommendation>) {
    const updated = await next;
    setSelected(await fetchActionRecommendation(updated.id));
    setItems(await fetchReviewQueue(filter));
  }

  return (
    <section className="min-w-0 space-y-5">
      <div className="rounded-md border border-line bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-signal">Human Approval Console</p>
          <h1 className="mt-2 text-2xl font-semibold">Review Queue</h1>
          <p className="mt-2 text-sm text-slate-600">{status}. These are policy-gated recommendations, not autonomous writes.</p>
        </div>
        <button onClick={() => load()} className="inline-flex items-center gap-2 rounded-md border border-line bg-panel px-3 py-2 text-sm font-medium hover:bg-panel">
          <RefreshCw size={16} aria-hidden="true" />
          Refresh
        </button>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-4">
        <Mini label="Visible Actions" value={items.length} />
        <Mini label="Pending" value={items.filter((item) => item.status === "PENDING").length} />
        <Mini label="Security" value={items.filter((item) => item.action_type === "ESCALATE_FOR_SECURITY_REVIEW" || item.security_signal).length} />
        <Mini label="Failed" value={items.filter((item) => item.status === "FAILED").length} />
      </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {filters.map((item) => (
          <button key={item} onClick={() => chooseFilter(item)} className={`rounded-md border px-3 py-2 text-xs font-medium ${filter === item ? "border-signal bg-teal-50 text-signal" : "border-line bg-white text-slate-600 hover:bg-panel"}`}>
            {item.replaceAll("_", " ")}
          </button>
        ))}
      </div>

      <div className="grid min-w-0 gap-4 2xl:grid-cols-[minmax(520px,1fr)_420px]">
        <div className="min-w-0 overflow-x-auto overflow-y-hidden rounded-md border border-line bg-white">
          <div className="min-w-[980px]">
          <div className="grid grid-cols-[90px_1fr_120px_150px_110px] gap-3 border-b border-line bg-panel px-4 py-3 text-xs font-semibold text-slate-600">
            <span>Issue</span>
            <span>Title</span>
            <span>Priority</span>
            <span>Action</span>
            <span>Status</span>
          </div>
          <div className="max-h-[66vh] overflow-auto">
            {items.map((item) => (
              <button key={item.id} onClick={() => fetchActionRecommendation(item.id).then(setSelected)} className={`grid w-full grid-cols-[90px_1fr_120px_150px_110px] gap-3 border-b border-line px-4 py-3 text-left text-sm hover:bg-panel ${selected?.id === item.id ? "bg-teal-50" : "bg-white"}`}>
                <span className="font-semibold">#{item.issue_number}</span>
                <span className="truncate">{item.issue_title}</span>
                <Badge value={item.priority ?? "UNKNOWN"} />
                <span className="truncate text-xs">{item.action_type}</span>
                <Badge value={item.status} />
              </button>
            ))}
            {!items.length ? <div className="p-5 text-sm text-slate-600">No review items yet. Run an investigation to create a recommendation.</div> : null}
          </div>
          </div>
        </div>

        <aside className="min-w-0 rounded-md border border-line bg-white p-5">
          {selected ? (
            <div className="space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold">#{selected.issue_number} {selected.issue_title}</div>
                  <p className="mt-1 text-xs text-slate-600">{selected.repository}</p>
                </div>
                {selected.issue_url ? (
                  <a href={selected.issue_url} target="_blank" className="text-signal" aria-label="Open GitHub issue">
                    <ExternalLink size={18} aria-hidden="true" />
                  </a>
                ) : null}
              </div>

              <Detail label="Recommended Action" value={selected.action_type} />
              <Detail label="Confidence" value={selected.confidence.toFixed(2)} />
              <Detail label="Priority" value={selected.priority ?? "--"} />
              <Detail label="Escalation" value={selected.escalation ?? "--"} />
              <Detail label="Security Signal" value={selected.security_signal ?? "--"} />
              <Detail label="Duplicate State" value={selected.duplicate_state ?? "--"} />

              <div>
                <h2 className="text-sm font-semibold">Why</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{selected.reason}</p>
              </div>

              <div>
                <h2 className="text-sm font-semibold">Action Preview</h2>
                <pre className="mt-2 max-h-56 overflow-auto rounded-md bg-panel p-3 text-xs text-slate-700">{previewPayload(selected)}</pre>
              </div>

              <div className="rounded-md border border-line bg-panel p-3 text-sm">
                <div className="font-semibold">Policy Validation</div>
                <p className="mt-1 text-slate-600">{selected.policy_validation?.decision ?? selected.policy_decision}: {selected.policy_validation?.reason ?? "Pending detailed validation"}</p>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <button disabled={selected.status !== "PENDING"} onClick={() => refreshSelected(approveActionRecommendation(selected.id))} className="inline-flex items-center justify-center gap-2 rounded-md bg-signal px-3 py-2 text-sm font-medium text-white disabled:opacity-40">
                  <CheckCircle2 size={16} aria-hidden="true" />
                  Approve
                </button>
                <button disabled={!["PENDING", "APPROVED", "FAILED"].includes(selected.status)} onClick={() => refreshSelected(rejectActionRecommendation(selected.id, "Rejected in local review"))} className="inline-flex items-center justify-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium hover:bg-panel disabled:opacity-40">
                  <XCircle size={16} aria-hidden="true" />
                  Reject
                </button>
                <button disabled={selected.status !== "APPROVED"} onClick={() => refreshSelected(executeActionRecommendation(selected.id))} className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-3 py-2 text-sm font-medium text-white disabled:opacity-40">
                  <PlayCircle size={16} aria-hidden="true" />
                  Execute
                </button>
              </div>
              <p className="flex items-start gap-2 text-xs leading-5 text-slate-600">
                <ShieldAlert size={15} className="mt-0.5 shrink-0 text-amber" aria-hidden="true" />
                Approval is recorded before execution. External writes are blocked unless server-side policy allows the demo repository action.
              </p>
            </div>
          ) : (
            <p className="text-sm text-slate-600">Select a recommendation to inspect the exact proposed GitHub action.</p>
          )}
        </aside>
      </div>
    </section>
  );
}

function Badge({ value }: { value: string }) {
  const strong = ["HIGH", "CRITICAL", "URGENT_REVIEW", "FAILED", "SECURITY_REVIEW"].some((term) => value.includes(term));
  return <span className={`inline-flex h-7 items-center rounded-md px-2 text-xs font-semibold ${strong ? "bg-amber/10 text-amber" : "bg-panel text-slate-700"}`}>{value}</span>;
}

function Mini({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-line bg-panel p-3">
      <div className="text-xs font-bold uppercase text-slate-500">{label}</div>
      <div className="mt-2 text-xl font-semibold text-ink">{value}</div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-slate-600">{label}</span>
      <span className="font-medium text-ink">{value}</span>
    </div>
  );
}

function previewPayload(item: ActionRecommendation) {
  return JSON.stringify(
    {
      action: item.action_type,
      repository: item.repository,
      issue: `#${item.issue_number}`,
      payload: item.recommended_payload
    },
    null,
    2
  );
}
