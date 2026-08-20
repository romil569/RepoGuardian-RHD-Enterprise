"use client";

/* eslint-disable react-hooks/set-state-in-effect */

import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchAuditLog } from "@/services/system";
import type { AuditLogEvent } from "@/types/system";

const eventFilters = ["", "RECOMMENDATION_CREATED", "RECOMMENDATION_APPROVED", "RECOMMENDATION_REJECTED", "GITHUB_ACTION_EXECUTED", "GITHUB_ACTION_FAILED", "POLICY_BLOCKED_ACTION", "FEEDBACK_SUBMITTED"];

export function AuditLog() {
  const [items, setItems] = useState<AuditLogEvent[]>([]);
  const [filter, setFilter] = useState("");
  const [status, setStatus] = useState("Loading audit log");

  async function load(activeFilter = filter) {
    const response = await fetchAuditLog({ event_type: activeFilter || undefined, limit: 80 });
    setItems(response.items);
    setStatus(`${response.items.length} of ${response.total} audit events shown`);
  }

  useEffect(() => {
    load().catch((error: Error) => setStatus(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function chooseFilter(value: string) {
    setFilter(value);
    await load(value);
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-signal">{status}</p>
          <h1 className="mt-2 text-2xl font-semibold">Audit Log</h1>
        </div>
        <button onClick={() => load()} className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-medium hover:bg-panel">
          <RefreshCw size={16} aria-hidden="true" />
          Refresh
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {eventFilters.map((item) => (
          <button key={item || "ALL"} onClick={() => chooseFilter(item)} className={`rounded-md border px-3 py-2 text-xs font-medium ${filter === item ? "border-signal bg-teal-50 text-signal" : "border-line bg-white text-slate-600 hover:bg-panel"}`}>
            {item ? item.replaceAll("_", " ") : "ALL EVENTS"}
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-md border border-line bg-white">
        <div className="grid grid-cols-[190px_210px_110px_140px_1fr] gap-3 border-b border-line bg-panel px-4 py-3 text-xs font-semibold text-slate-600">
          <span>Time</span>
          <span>Event</span>
          <span>Issue</span>
          <span>Actor</span>
          <span>Description</span>
        </div>
        <div className="max-h-[70vh] overflow-auto">
          {items.map((item) => (
            <div key={item.id} className="grid grid-cols-[190px_210px_110px_140px_1fr] gap-3 border-b border-line px-4 py-3 text-sm">
              <span className="text-slate-600">{new Date(item.created_at).toLocaleString()}</span>
              <span className="font-medium">{item.event_type}</span>
              <span>{item.issue_id ? `#${item.issue_id}` : "--"}</span>
              <span>{item.actor}</span>
              <span className="text-slate-700">{item.safe_summary}</span>
            </div>
          ))}
          {!items.length ? <div className="p-5 text-sm text-slate-600">No audit events match the current filter.</div> : null}
        </div>
      </div>
    </section>
  );
}
