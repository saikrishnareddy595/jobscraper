"use client";

import { useState, useEffect, useCallback } from "react";

type RunStatus = "completed" | "in_progress" | "queued" | "waiting" | "requested" | "pending";
type RunConclusion = "success" | "failure" | "cancelled" | "skipped" | null;

interface WorkflowRun {
  id: number;
  status: RunStatus;
  conclusion: RunConclusion;
  created_at: string;
  html_url: string;
  run_number: number;
}

interface Toast {
  id: number;
  type: "success" | "error" | "info";
  message: string;
}

function statusColor(status: RunStatus, conclusion: RunConclusion) {
  if (status === "in_progress" || status === "queued") return "text-yellow-400";
  if (conclusion === "success") return "text-green-400";
  if (conclusion === "failure") return "text-red-400";
  if (conclusion === "cancelled") return "text-slate-400";
  return "text-slate-400";
}

function statusLabel(status: RunStatus, conclusion: RunConclusion) {
  if (status === "in_progress") return "Running";
  if (status === "queued" || status === "waiting" || status === "requested" || status === "pending") return "Queued";
  if (conclusion === "success") return "Success";
  if (conclusion === "failure") return "Failed";
  if (conclusion === "cancelled") return "Cancelled";
  return status;
}

function statusDot(status: RunStatus, conclusion: RunConclusion) {
  const base = "inline-block w-2 h-2 rounded-full mr-2";
  if (status === "in_progress") return `${base} bg-yellow-400 blink`;
  if (status === "queued" || status === "waiting" || status === "requested" || status === "pending")
    return `${base} bg-yellow-500 blink`;
  if (conclusion === "success") return `${base} bg-green-400`;
  if (conclusion === "failure") return `${base} bg-red-400`;
  return `${base} bg-slate-500`;
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

let toastId = 0;

export default function WorkflowTrigger() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [triggering, setTriggering] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [expanded, setExpanded] = useState(false);

  const addToast = (type: Toast["type"], message: string) => {
    const id = ++toastId;
    setToasts((t) => [...t, { id, type, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  };

  const fetchRuns = useCallback(async () => {
    try {
      const res = await fetch("/api/trigger-workflow");
      if (!res.ok) return;
      const data = await res.json();
      setRuns(data.runs ?? []);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 30_000);
    return () => clearInterval(interval);
  }, [fetchRuns]);

  const latestRun = runs[0];
  const isRunning =
    latestRun &&
    (latestRun.status === "in_progress" ||
      latestRun.status === "queued" ||
      latestRun.status === "waiting" ||
      latestRun.status === "requested");

  const trigger = async () => {
    setTriggering(true);
    try {
      const res = await fetch("/api/trigger-workflow", { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        addToast("success", "Scraper workflow triggered! It will start shortly.");
        setTimeout(fetchRuns, 3000);
      } else {
        addToast("error", data.error ?? "Failed to trigger workflow.");
      }
    } catch {
      addToast("error", "Network error — could not reach the server.");
    } finally {
      setTriggering(false);
    }
  };

  const toastStyle: Record<Toast["type"], string> = {
    success: "bg-green-950 border-green-700 text-green-300",
    error: "bg-red-950 border-red-700 text-red-300",
    info: "bg-blue-950 border-blue-700 text-blue-300",
  };
  const toastIcon: Record<Toast["type"], string> = {
    success: "✓",
    error: "✕",
    info: "i",
  };

  return (
    <>
      {/* ── Trigger panel ───────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3">
        {/* Big trigger button */}
        <div className="relative">
          <button
            onClick={trigger}
            disabled={triggering || !!isRunning}
            className={`
              relative w-full flex items-center justify-center gap-3
              px-6 py-3.5 rounded-xl font-semibold text-sm
              transition-all duration-200 overflow-hidden
              ${triggering || isRunning
                ? "bg-slate-700 text-slate-400 cursor-not-allowed"
                : "bg-gradient-to-r from-sky-500 via-blue-600 to-indigo-600 text-white hover:from-sky-400 hover:via-blue-500 hover:to-indigo-500 hover:shadow-lg hover:shadow-blue-500/30 hover:-translate-y-0.5 active:translate-y-0 pulse-ring"
              }
            `}
          >
            {/* Shine sweep */}
            {!triggering && !isRunning && (
              <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full hover:translate-x-full transition-transform duration-700 pointer-events-none" />
            )}

            {triggering ? (
              <>
                <span className="w-4 h-4 border-2 border-slate-400 border-t-white rounded-full animate-spin" />
                Triggering…
              </>
            ) : isRunning ? (
              <>
                <span className="w-2 h-2 rounded-full bg-yellow-400 blink" />
                Scraper Running…
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 3l14 9-14 9V3z" />
                </svg>
                Run Scraper Now
              </>
            )}
          </button>
        </div>

        {/* Latest status badge */}
        {latestRun && (
          <button
            onClick={() => setExpanded((e) => !e)}
            className="flex items-center justify-between px-3.5 py-2.5 rounded-lg glass border border-slate-700/50 hover:border-slate-600 transition-colors text-xs w-full text-left"
          >
            <span className="flex items-center">
              <span className={statusDot(latestRun.status, latestRun.conclusion)} />
              <span className={`font-semibold ${statusColor(latestRun.status, latestRun.conclusion)}`}>
                {statusLabel(latestRun.status, latestRun.conclusion)}
              </span>
              <span className="text-slate-500 ml-1.5">— run #{latestRun.run_number}</span>
            </span>
            <span className="flex items-center gap-2 text-slate-500">
              {timeAgo(latestRun.created_at)}
              <svg
                className={`w-3 h-3 transition-transform ${expanded ? "rotate-180" : ""}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </span>
          </button>
        )}

        {/* Run history dropdown */}
        {expanded && runs.length > 0 && (
          <div className="glass rounded-xl border border-slate-700/50 overflow-hidden fade-in-up">
            <div className="px-3 py-2 border-b border-slate-700/50">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Recent Runs</p>
            </div>
            {runs.map((run) => (
              <a
                key={run.id}
                href={run.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between px-3 py-2.5 hover:bg-slate-800/50 transition-colors border-b border-slate-800/60 last:border-0"
              >
                <span className="flex items-center gap-2 text-xs">
                  <span className={statusDot(run.status, run.conclusion)} />
                  <span className={`font-medium ${statusColor(run.status, run.conclusion)}`}>
                    {statusLabel(run.status, run.conclusion)}
                  </span>
                  <span className="text-slate-500">#{run.run_number}</span>
                </span>
                <span className="flex items-center gap-1.5 text-[11px] text-slate-500">
                  {timeAgo(run.created_at)}
                  <svg className="w-3 h-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </span>
              </a>
            ))}
          </div>
        )}
      </div>

      {/* ── Toasts ──────────────────────────────────────────────────────── */}
      <div className="fixed bottom-6 right-6 flex flex-col gap-2 z-50 pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`toast-enter flex items-start gap-3 px-4 py-3 rounded-xl border glass-strong shadow-2xl max-w-sm pointer-events-auto ${toastStyle[t.type]}`}
          >
            <span className="flex-shrink-0 w-5 h-5 rounded-full border border-current flex items-center justify-center text-[11px] font-bold mt-0.5">
              {toastIcon[t.type]}
            </span>
            <p className="text-sm leading-snug">{t.message}</p>
          </div>
        ))}
      </div>
    </>
  );
}
