"use client";

import { useState, useMemo } from "react";
import { LinkedInPost } from "@/lib/types";

interface Props {
  posts: LinkedInPost[];
}

function scoreColor(score: number): string {
  if (score >= 80) return "text-green-400";
  if (score >= 60) return "text-yellow-400";
  return "text-slate-400";
}

const ROLE_COLORS: Record<string, string> = {
  data_engineer: "bg-blue-900/60 text-blue-300 border border-blue-700/40",
  ai_engineer:   "bg-violet-900/60 text-violet-300 border border-violet-700/40",
  ml_engineer:   "bg-indigo-900/60 text-indigo-300 border border-indigo-700/40",
  nlp_engineer:  "bg-teal-900/60 text-teal-300 border border-teal-700/40",
  cv_engineer:   "bg-cyan-900/60 text-cyan-300 border border-cyan-700/40",
  data_scientist:"bg-pink-900/60 text-pink-300 border border-pink-700/40",
  other:         "bg-slate-700/60 text-slate-300 border border-slate-600/40",
};

/** Safe date → "Xd ago" or "Today" */
function safeDaysAgo(dateStr: string | undefined | null): string {
  if (!dateStr) return "Unknown";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "Unknown";
  const days = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  return days <= 0 ? "Today" : `${days}d ago`;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="ml-1 text-xs px-1.5 py-0.5 rounded glass border border-slate-600/40 text-slate-400 hover:text-slate-200 transition-colors"
      title="Copy email"
    >
      {copied ? "✓ Copied" : "Copy"}
    </button>
  );
}

type SortKey = "score" | "date" | "email";

export default function LinkedInPosts({ posts }: Props) {
  const [emailOnly, setEmailOnly] = useState(false);
  const [minScore,  setMinScore]  = useState(0);
  const [search,    setSearch]    = useState("");
  const [sortBy,    setSortBy]    = useState<SortKey>("score");

  const withEmail = posts.filter((p) => p.contact_email).length;

  const filtered = useMemo(() => {
    let list = posts.filter((p) => {
      if (emailOnly && !p.contact_email) return false;
      if (p.score < minScore) return false;
      if (search) {
        const q   = search.toLowerCase();
        const hay = `${p.author_name} ${p.extracted_title ?? ""} ${p.extracted_company ?? ""} ${p.post_text}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    list = [...list].sort((a, b) => {
      if (sortBy === "date") {
        const da = a.posted_date ? new Date(a.posted_date).getTime() : 0;
        const db = b.posted_date ? new Date(b.posted_date).getTime() : 0;
        return db - da;
      }
      if (sortBy === "email") {
        return (b.contact_email ? 1 : 0) - (a.contact_email ? 1 : 0);
      }
      return b.score - a.score;
    });

    return list;
  }, [posts, emailOnly, minScore, search, sortBy]);

  if (posts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
        <div className="w-16 h-16 rounded-2xl glass border border-slate-700/50 flex items-center justify-center text-3xl">📭</div>
        <div>
          <p className="text-slate-300 font-semibold">No LinkedIn recruiter posts found yet</p>
          <p className="text-slate-500 text-sm mt-1">Configure LINKEDIN_EMAIL + LINKEDIN_PASSWORD to start collecting recruiter posts.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter/Sort bar */}
      <div className="glass border border-slate-700/50 rounded-2xl p-4 flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search recruiter, title, company…"
            className="w-full glass border border-slate-600/50 rounded-xl px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500/60 transition-colors"
          />
        </div>

        {/* Sort */}
        <div className="flex items-center gap-1 glass border border-slate-700/40 rounded-xl p-1">
          {(["score","date","email"] as SortKey[]).map((k) => (
            <button
              key={k}
              onClick={() => setSortBy(k)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all capitalize ${
                sortBy === k
                  ? "bg-gradient-to-r from-sky-600 to-indigo-600 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {k === "email" ? "Has Email" : k}
            </button>
          ))}
        </div>

        {/* Email only toggle */}
        <label className="flex items-center gap-2 cursor-pointer whitespace-nowrap">
          <input
            type="checkbox"
            checked={emailOnly}
            onChange={(e) => setEmailOnly(e.target.checked)}
            className="accent-amber-400"
          />
          <span className="text-sm text-slate-300">
            Emails only
            {withEmail > 0 && (
              <span className="ml-1.5 bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs px-1.5 py-0.5 rounded-full">
                {withEmail}
              </span>
            )}
          </span>
        </label>

        {/* Min score */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 whitespace-nowrap">Min: <span className="text-sky-400 font-bold">{minScore}</span></span>
          <input
            type="range" min={0} max={100} value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-24 accent-sky-500"
          />
        </div>

        <span className="text-xs text-slate-500 ml-auto">
          {filtered.length} / {posts.length}
        </span>
      </div>

      {/* Posts grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((post) => (
          <div
            key={post.id}
            className={`glass border rounded-xl p-4 hover:border-slate-500/70 transition-all flex flex-col gap-2 hover:-translate-y-0.5 ${
              post.contact_email ? "border-amber-700/50" : "border-slate-700/50"
            }`}
          >
            {/* Email badge */}
            {post.contact_email && (
              <div className="flex items-center gap-1 bg-amber-900/30 border border-amber-700/40 rounded-lg px-2 py-1.5">
                <span className="text-amber-400 text-xs font-semibold">📧</span>
                <a
                  href={`mailto:${post.contact_email}`}
                  className="text-amber-300 text-xs font-mono hover:underline truncate flex-1"
                >
                  {post.contact_email}
                </a>
                <CopyButton text={post.contact_email} />
              </div>
            )}

            {/* Author */}
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <a
                  href={post.author_profile_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-sky-400 hover:underline text-sm"
                >
                  {post.author_name}
                </a>
                <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{post.author_headline}</p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className={`text-sm font-bold ${scoreColor(post.score)}`}>{post.score}</span>
                <span className="text-xs text-slate-500">{safeDaysAgo(post.posted_date)}</span>
                <a
                  href={post.post_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2 py-1 rounded-lg text-xs glass border border-slate-700/50 hover:border-sky-700/50 text-slate-300 hover:text-sky-300 transition-colors"
                >
                  View →
                </a>
              </div>
            </div>

            {/* Tags */}
            <div className="flex flex-wrap gap-1.5">
              {post.extracted_title && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700/60 text-slate-200 border border-slate-600/40">
                  {post.extracted_title}
                </span>
              )}
              {post.extracted_company && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700/60 text-slate-400 border border-slate-600/40">
                  {post.extracted_company}
                </span>
              )}
              <span className={`text-xs px-2 py-0.5 rounded-full ${ROLE_COLORS[post.role_category] || ROLE_COLORS.other}`}>
                {post.role_category.replace(/_/g, " ")}
              </span>
            </div>

            {/* Post text */}
            <p className="text-sm text-slate-300 leading-relaxed line-clamp-4 flex-1">{post.post_text}</p>

            {/* Contact links */}
            <div className="flex flex-wrap gap-2 text-xs">
              {post.contact_name && post.contact_name !== post.author_name && (
                <span className="text-slate-400">
                  Contact: <span className="text-slate-200">{post.contact_name}</span>
                </span>
              )}
              {post.contact_linkedin && (
                <a
                  href={post.contact_linkedin}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sky-400 hover:underline"
                >
                  LinkedIn →
                </a>
              )}
            </div>

            {/* Applied/Saved */}
            {(post.applied || post.saved) && (
              <div className="flex gap-2">
                {post.applied && (
                  <span className="text-xs bg-blue-900/60 text-blue-300 px-2 py-0.5 rounded-full border border-blue-700/40">Applied ✓</span>
                )}
                {post.saved && (
                  <span className="text-xs bg-pink-900/60 text-pink-300 px-2 py-0.5 rounded-full border border-pink-700/40">Saved ★</span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          No posts match your current filters.
        </div>
      )}
    </div>
  );
}
