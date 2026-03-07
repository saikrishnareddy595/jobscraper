"use client";

import { Job, Filters, JobType } from "@/lib/types";
import JobCard from "./JobCard";

interface Props {
  jobs: Job[];
  filters: Filters;
  onApplied: (id: number, applied: boolean) => void;
  onSaved: (id: number, saved: boolean) => void;
}

export default function JobsGrid({ jobs, filters, onApplied, onSaved }: Props) {
  // Apply filters
  let filtered = jobs.filter((job) => {
    if (filters.role !== "all" && job.role_category !== filters.role)
      return false;
    if (
      filters.jobTypes.length > 0 &&
      !filters.jobTypes.includes(job.job_type as JobType)
    )
      return false;
    if (job.score < filters.minScore) return false;
    if (filters.remoteOnly && !job.location.toLowerCase().includes("remote"))
      return false;
    if (filters.easyApplyOnly && !job.easy_apply) return false;
    if (filters.sources.length > 0 && !filters.sources.includes(job.source))
      return false;
    if (filters.search) {
      const q = filters.search.toLowerCase();
      const haystack = `${job.title} ${job.company} ${job.location}`.toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });

  // Sort
  filtered = [...filtered].sort((a, b) => {
    if (filters.sortBy === "date") {
      return (
        new Date(b.posted_date).getTime() - new Date(a.posted_date).getTime()
      );
    }
    if (filters.sortBy === "salary") {
      return (b.salary ?? 0) - (a.salary ?? 0);
    }
    // default: score (llm_score preferred)
    const sa = b.llm_score ?? b.score;
    const sb = a.llm_score ?? a.score;
    return sa - sb;
  });

  if (filtered.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <div className="text-5xl mb-4">🔍</div>
        <p className="text-lg">No jobs match your filters.</p>
        <p className="text-sm mt-2">Try adjusting the role, score, or job type.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">
        {filtered.length} of {jobs.length} jobs
      </p>
      {filtered.map((job) => (
        <JobCard
          key={job.id}
          job={job}
          onApplied={onApplied}
          onSaved={onSaved}
        />
      ))}
    </div>
  );
}
