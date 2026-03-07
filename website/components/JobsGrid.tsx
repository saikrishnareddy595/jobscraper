"use client";

import { Job, Filters, JobType } from "@/lib/types";
import JobCard from "./JobCard";

interface Props {
  jobs: Job[];
  filters: Filters;
  onApplied: (id: number, applied: boolean) => void;
  onSaved: (id: number, saved: boolean) => void;
}

function SkeletonCard() {
  return (
    <div className="glass border border-slate-700/40 rounded-xl p-4">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl shimmer flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-4 shimmer rounded-lg w-3/4" />
          <div className="h-3 shimmer rounded-lg w-1/2" />
        </div>
        <div className="w-28 h-7 shimmer rounded-lg" />
      </div>
      <div className="flex gap-2 mt-3">
        <div className="h-5 w-20 shimmer rounded-full" />
        <div className="h-5 w-24 shimmer rounded-full" />
        <div className="h-5 w-16 shimmer rounded-full" />
      </div>
    </div>
  );
}

function exportCSV(jobs: Job[]) {
  const headers = ["Title", "Company", "Location", "Score", "Salary", "Type", "Source", "Posted", "URL", "Easy Apply", "Visa Sponsorship"];
  const rows = jobs.map((j) => [
    `"${(j.title || "").replace(/"/g, '""')}"`,
    `"${(j.company || "").replace(/"/g, '""')}"`,
    `"${(j.location || "").replace(/"/g, '""')}"`,
    j.score,
    j.salary ?? "",
    j.job_type,
    j.source,
    j.posted_date ? new Date(j.posted_date).toLocaleDateString() : "",
    j.url,
    j.easy_apply ? "Yes" : "No",
    j.visa_sponsorship === true ? "Sponsors" : j.visa_sponsorship === false ? "No" : "Unknown",
  ]);
  const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `jobs-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function JobsGrid({ jobs, filters, onApplied, onSaved }: Props) {
  // Apply filters
  let filtered = jobs.filter((job) => {
    if (filters.role !== "all" && job.role_category !== filters.role) return false;
    if (filters.jobTypes.length > 0 && !filters.jobTypes.includes(job.job_type as JobType)) return false;
    if (job.score < filters.minScore) return false;
    if (filters.remoteOnly && !job.location.toLowerCase().includes("remote")) return false;
    if (filters.easyApplyOnly && !job.easy_apply) return false;
    if (filters.sources.length > 0 && !filters.sources.includes(job.source)) return false;
    if (filters.visaFilter === "sponsors"       && job.visa_sponsorship !== true)  return false;
    if (filters.visaFilter === "no_sponsorship" && job.visa_sponsorship !== false) return false;
    if (filters.search) {
      const q = filters.search.toLowerCase();
      const hay = `${job.title} ${job.company} ${job.location} ${(job.skills ?? []).join(" ")}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  // Sort
  filtered = [...filtered].sort((a, b) => {
    if (filters.sortBy === "date") {
      const da = a.posted_date ? new Date(a.posted_date).getTime() : 0;
      const db = b.posted_date ? new Date(b.posted_date).getTime() : 0;
      return db - da;
    }
    if (filters.sortBy === "salary") return (b.salary ?? 0) - (a.salary ?? 0);
    // score (llm_score preferred)
    return (b.llm_score ?? b.score) - (a.llm_score ?? a.score);
  });

  if (filtered.length === 0) {
    const hasActiveFilters =
      filters.role !== "all" || filters.jobTypes.length > 0 ||
      filters.minScore > 0 || filters.remoteOnly || filters.easyApplyOnly ||
      filters.visaFilter !== "all" || !!filters.search || filters.sources.length > 0;

    return (
      <div className="flex flex-col items-center justify-center py-20 text-center gap-4">
        <div className="w-16 h-16 rounded-2xl glass border border-slate-700/50 flex items-center justify-center text-3xl">
          {hasActiveFilters ? "🔍" : "📭"}
        </div>
        <div>
          <p className="text-slate-300 font-semibold">
            {hasActiveFilters ? "No jobs match your filters" : "No jobs loaded yet"}
          </p>
          <p className="text-slate-500 text-sm mt-1">
            {hasActiveFilters
              ? "Try lowering the min score, expanding job types, or clearing role filters."
              : "Run the scraper to fetch jobs, or check your Supabase connection."}
          </p>
        </div>
        {hasActiveFilters && (
          <div className="text-xs text-slate-500 space-y-0.5">
            {filters.minScore > 0 && <p>↳ Min score: {filters.minScore} — try lowering it</p>}
            {filters.visaFilter !== "all" && <p>↳ Visa filter active — many jobs don&apos;t have sponsorship data</p>}
            {filters.remoteOnly && <p>↳ Remote only — try disabling for more results</p>}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500">
          <span className="text-slate-300 font-semibold">{filtered.length}</span> of{" "}
          <span className="text-slate-400">{jobs.length}</span> jobs
        </p>
        <button
          onClick={() => exportCSV(filtered)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs glass border border-slate-700/50 rounded-lg text-slate-400 hover:text-slate-200 hover:border-slate-600 transition-all"
          title="Export visible jobs as CSV"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Export CSV
        </button>
      </div>

      {filtered.map((job) => (
        <JobCard key={job.id} job={job} onApplied={onApplied} onSaved={onSaved} />
      ))}
    </div>
  );
}

export { SkeletonCard };
