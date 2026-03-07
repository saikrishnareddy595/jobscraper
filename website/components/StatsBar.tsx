"use client";

import { Job, LinkedInPost } from "@/lib/types";

interface Props {
  jobs: Job[];
  posts: LinkedInPost[];
}

export default function StatsBar({ jobs, posts }: Props) {
  const total       = jobs.length;
  const avgScore    = total ? Math.round(jobs.reduce((s, j) => s + j.score, 0) / total) : 0;
  const highScore   = jobs.filter((j) => j.score >= 80).length;
  const fullTime    = jobs.filter((j) => j.job_type === "full_time").length;
  const contracts   = jobs.filter((j) => j.job_type.includes("contract")).length;
  const remote      = jobs.filter((j) => j.location?.toLowerCase().includes("remote")).length;
  const applied     = jobs.filter((j) => j.applied).length;
  const saved       = jobs.filter((j) => j.saved).length;
  const withSalary  = jobs.filter((j) => j.salary).length;
  const sponsoring  = jobs.filter((j) => j.visa_sponsorship === true).length;
  const avgSalary   = withSalary
    ? Math.round(jobs.filter((j) => j.salary).reduce((s, j) => s + (j.salary ?? 0), 0) / withSalary / 1000)
    : 0;
  const postsEmails = posts.filter((p) => p.contact_email).length;

  const stats = [
    { label: "Total Jobs",  value: total,                   color: "text-blue-400",    icon: "◈" },
    { label: "Avg Score",   value: avgScore,                color: "text-green-400",   icon: "◎" },
    { label: "Score 80+",   value: highScore,               color: "text-yellow-400",  icon: "★" },
    { label: "Remote",      value: remote,                  color: "text-sky-400",     icon: "⌂" },
    { label: "Full-Time",   value: fullTime,                color: "text-purple-400",  icon: "◉" },
    { label: "Contract",    value: contracts,               color: "text-orange-400",  icon: "◐" },
    { label: "Avg Salary",  value: withSalary ? `$${avgSalary}k` : "—", color: "text-emerald-400", icon: "$" },
    { label: "Visa Spon.",  value: sponsoring,              color: "text-teal-400",    icon: "✓" },
    { label: "Applied",     value: applied,                 color: "text-indigo-400",  icon: "✈" },
    { label: "Saved",       value: saved,                   color: "text-pink-400",    icon: "♥" },
    { label: "Recruiters",  value: posts.length,            color: "text-violet-400",  icon: "◈" },
    { label: "Emails",      value: postsEmails,             color: "text-amber-400",   icon: "@" },
  ];

  return (
    <div className="grid grid-cols-4 sm:grid-cols-6 lg:grid-cols-12 gap-2">
      {stats.map((s) => (
        <div
          key={s.label}
          className="glass border border-slate-700/40 rounded-xl p-3 text-center hover:border-slate-600/60 transition-colors"
        >
          <div className={`text-[10px] mb-1 opacity-50 ${s.color}`}>{s.icon}</div>
          <div className={`text-xl font-bold leading-none ${s.color}`}>{s.value}</div>
          <div className="text-[10px] text-slate-500 mt-1 leading-tight">{s.label}</div>
        </div>
      ))}
    </div>
  );
}
