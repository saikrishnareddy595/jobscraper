"use client";

import { useState, MouseEvent } from "react";
import { Job } from "@/lib/types";

interface Props {
  job: Job;
  onApplied: (id: number, applied: boolean) => void;
  onSaved: (id: number, saved: boolean) => void;
}

const TYPE_COLORS: Record<string, string> = {
  full_time:        "bg-green-900/60 text-green-300 border border-green-700/40",
  contract:         "bg-orange-900/60 text-orange-300 border border-orange-700/40",
  contract_to_hire: "bg-yellow-900/60 text-yellow-300 border border-yellow-700/40",
  part_time:        "bg-purple-900/60 text-purple-300 border border-purple-700/40",
};

const ROLE_COLORS: Record<string, string> = {
  data_engineer: "bg-blue-900/60 text-blue-300 border border-blue-700/40",
  ai_engineer:   "bg-violet-900/60 text-violet-300 border border-violet-700/40",
  ml_engineer:   "bg-indigo-900/60 text-indigo-300 border border-indigo-700/40",
  nlp_engineer:  "bg-teal-900/60 text-teal-300 border border-teal-700/40",
  cv_engineer:   "bg-cyan-900/60 text-cyan-300 border border-cyan-700/40",
  data_scientist:"bg-pink-900/60 text-pink-300 border border-pink-700/40",
};

function scoreColor(score: number): string {
  if (score >= 80) return "bg-green-500 shadow-lg shadow-green-500/30";
  if (score >= 60) return "bg-yellow-500 shadow-lg shadow-yellow-500/30";
  if (score >= 40) return "bg-orange-500";
  return "bg-red-500";
}

function scoreRingColor(score: number): string {
  if (score >= 80) return "border-green-500/50";
  if (score >= 60) return "border-yellow-500/50";
  if (score >= 40) return "border-orange-500/50";
  return "border-red-500/50";
}

/** Safe date → "Xd ago" or "Today" or "Unknown" */
function safePostedLabel(posted_date: string | undefined | null): string {
  if (!posted_date) return "Unknown";
  const d = new Date(posted_date);
  if (isNaN(d.getTime())) return "Unknown";
  const days = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (days <= 0) return "Today";
  return `${days}d ago`;
}

export default function JobCard({ job, onApplied, onSaved }: Props) {
  const [expanded, setExpanded]   = useState(false);
  const [applying, setApplying]   = useState(false);
  const [saving,   setSaving]     = useState(false);
  const [feedback, setFeedback]   = useState<"liked" | "disliked" | null>(null);

  const handleFeedback = async (liked: boolean, e: MouseEvent) => {
    e.stopPropagation();
    setFeedback(liked ? "liked" : "disliked");
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: job.id, table: "jobs", liked }),
    });
  };

  const handleApply = async (e: MouseEvent) => {
    e.stopPropagation();
    if (applying) return;
    setApplying(true);
    try {
      await fetch("/api/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: job.id, applied: !job.applied }),
      });
      onApplied(job.id, !job.applied);
    } finally { setApplying(false); }
  };

  const handleSave = async (e: MouseEvent) => {
    e.stopPropagation();
    if (saving) return;
    setSaving(true);
    try {
      await fetch("/api/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: job.id, saved: !job.saved }),
      });
      onSaved(job.id, !job.saved);
    } finally { setSaving(false); }
  };

  const typeLabel  = (job.job_type || "full_time").replace(/_/g, "-");
  const roleLabel  = (job.role_category || "other").replace(/_/g, " ");
  const postedLabel = safePostedLabel(job.posted_date);

  // Visa sponsorship badge
  const visaBadge =
    job.visa_sponsorship === true  ? { label: "Sponsors Visa",    cls: "bg-emerald-900/60 text-emerald-300 border border-emerald-700/40" } :
    job.visa_sponsorship === false ? { label: "No Sponsorship",   cls: "bg-red-900/60 text-red-300 border border-red-700/40" }            :
    null;

  const borderCls = job.applied
    ? "border-blue-600/60"
    : job.saved
    ? "border-pink-600/60"
    : `border-slate-700/50 ${scoreRingColor(job.score)}`;

  return (
    <div
      className={`glass border rounded-xl p-4 transition-all cursor-pointer hover:border-slate-500/70 hover:-translate-y-0.5 hover:shadow-xl ${borderCls}`}
      onClick={() => setExpanded(!expanded)}
    >
      {/* ── Header ───────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            {/* Score badge */}
            <span className={`flex-shrink-0 inline-flex items-center justify-center w-10 h-10 rounded-xl text-white font-bold text-sm ${scoreColor(job.score)}`}>
              {job.score}
            </span>
            <div className="min-w-0">
              <h3 className="font-semibold text-slate-100 text-sm leading-tight truncate max-w-xs">
                {job.title}
              </h3>
              <p className="text-slate-400 text-xs mt-0.5 flex items-center gap-1">
                <span className="font-medium text-slate-300">{job.company}</span>
                <span className="text-slate-600">·</span>
                <span>{job.location}</span>
              </p>
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <button
            onClick={(e) => handleFeedback(true, e)}
            title="Great fit"
            className={`p-1.5 rounded-lg text-sm transition-all ${feedback === "liked" ? "bg-green-600 text-white scale-110" : "glass border border-slate-700/50 text-slate-400 hover:text-green-400 hover:border-green-700/50"}`}
          >👍</button>
          <button
            onClick={(e) => handleFeedback(false, e)}
            title="Not for me"
            className={`p-1.5 rounded-lg text-sm transition-all ${feedback === "disliked" ? "bg-red-700 text-white scale-110" : "glass border border-slate-700/50 text-slate-400 hover:text-red-400 hover:border-red-700/50"}`}
          >👎</button>
          <button
            onClick={handleSave}
            disabled={saving}
            title={job.saved ? "Unsave" : "Save"}
            className={`p-1.5 rounded-lg text-sm transition-all ${job.saved ? "bg-pink-600 text-white" : "glass border border-slate-700/50 text-slate-400 hover:text-pink-400 hover:border-pink-700/50"}`}
          >{job.saved ? "★" : "☆"}</button>
          <button
            onClick={handleApply}
            disabled={applying}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${job.applied ? "bg-blue-800 text-blue-300 border border-blue-700/50" : "bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white shadow-md shadow-blue-500/20"}`}
          >{job.applied ? "Applied ✓" : "Mark Applied"}</button>
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e: MouseEvent) => e.stopPropagation()}
            className="px-3 py-1.5 rounded-lg text-xs font-medium glass border border-slate-700/50 hover:border-slate-500 text-slate-200 transition-all"
          >View →</a>
        </div>
      </div>

      {/* ── Tags ─────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-1.5 mt-3">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TYPE_COLORS[job.job_type] || "bg-slate-700 text-slate-300"}`}>
          {typeLabel}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ROLE_COLORS[job.role_category] || "bg-slate-700 text-slate-300"}`}>
          {roleLabel}
        </span>
        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700/70 text-slate-400 border border-slate-600/40">
          {job.source}
        </span>
        {job.salary && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-900/60 text-emerald-300 border border-emerald-700/40">
            ${job.salary.toLocaleString()}/yr
          </span>
        )}
        {job.easy_apply && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-teal-900/60 text-teal-300 border border-teal-700/40">
            ⚡ Easy Apply
          </span>
        )}
        {visaBadge && (
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${visaBadge.cls}`}>
            {visaBadge.label}
          </span>
        )}
        {job.applicants != null && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700/70 text-slate-400 border border-slate-600/40">
            {job.applicants} applicants
          </span>
        )}
        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800/80 text-slate-500 ml-auto border border-slate-700/30">
          {postedLabel}
        </span>
      </div>

      {/* ── AI Score + Reason ─────────────────────────────────────── */}
      {typeof job.llm_score === "number" && (
        <div className="mt-2 flex items-center gap-2 text-xs">
          <span className="text-slate-500">AI:</span>
          <span className={`font-bold ${job.llm_score >= 80 ? "text-green-400" : job.llm_score >= 60 ? "text-yellow-400" : "text-slate-400"}`}>
            {job.llm_score}
          </span>
          {job.llm_reason && (
            <span className="text-slate-500 truncate">— {job.llm_reason}</span>
          )}
        </div>
      )}

      {/* ── Skills ───────────────────────────────────────────────── */}
      {job.skills && job.skills.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {job.skills.slice(0, 8).map((skill) => (
            <span key={skill} className="text-xs bg-slate-700/60 text-slate-300 px-2 py-0.5 rounded border border-slate-600/30">
              {skill}
            </span>
          ))}
        </div>
      )}

      {/* ── Expanded Details ──────────────────────────────────────── */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-slate-700/50 space-y-2 fade-in-up">
          {job.llm_summary && (
            <p className="text-sm text-slate-300 leading-relaxed">{job.llm_summary}</p>
          )}
          {job.description && (
            <p className="text-xs text-slate-400 leading-relaxed line-clamp-6">
              {job.description}
            </p>
          )}
          {job.notes && (
            <p className="text-xs text-yellow-400 italic">Notes: {job.notes}</p>
          )}
        </div>
      )}
    </div>
  );
}
