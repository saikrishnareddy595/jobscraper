"use client";

import { useEffect, useState, useCallback } from "react";
import { Job, LinkedInPost, Filters } from "@/lib/types";
import StatsBar from "@/components/StatsBar";
import FilterSidebar from "@/components/FilterSidebar";
import JobsGrid from "@/components/JobsGrid";
import LinkedInPosts from "@/components/LinkedInPosts";
import AnalyticsPage from "@/components/AnalyticsPage";
import KanbanBoard from "@/components/KanbanBoard";
import WorkflowTrigger from "@/components/WorkflowTrigger";

type Tab = "jobs" | "posts" | "analytics" | "kanban" | "applied" | "saved";

const DEFAULT_FILTERS: Filters = {
  role: "all",
  jobTypes: [],
  sources: [],
  minScore: 0,
  remoteOnly: false,
  easyApplyOnly: false,
  search: "",
  sortBy: "score",
};

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "jobs",      label: "All Jobs",   icon: "◈" },
  { id: "posts",     label: "Recruiters", icon: "◉" },
  { id: "analytics", label: "Analytics",  icon: "◎" },
  { id: "kanban",    label: "Pipeline",   icon: "▤" },
  { id: "saved",     label: "Saved",      icon: "♥" },
  { id: "applied",   label: "Applied",    icon: "✓" },
];

export default function Home() {
  const [jobs, setJobs]               = useState<Job[]>([]);
  const [posts, setPosts]             = useState<LinkedInPost[]>([]);
  const [filters, setFilters]         = useState<Filters>(DEFAULT_FILTERS);
  const [activeTab, setActiveTab]     = useState<Tab>("jobs");
  const [loading, setLoading]         = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [jobsRes, postsRes] = await Promise.all([
        fetch("/api/jobs"),
        fetch("/api/posts"),
      ]);
      const jobsData: Job[]           = await jobsRes.json();
      const postsData: LinkedInPost[] = await postsRes.json();
      setJobs(Array.isArray(jobsData) ? jobsData : []);
      setPosts(Array.isArray(postsData) ? postsData : []);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Failed to fetch data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleApplied = (id: number, applied: boolean) =>
    setJobs((prev) => prev.map((j) => (j.id === id ? { ...j, applied } : j)));

  const handleSaved = (id: number, saved: boolean) =>
    setJobs((prev) => prev.map((j) => (j.id === id ? { ...j, saved } : j)));

  const appliedJobs    = jobs.filter((j) => j.applied);
  const savedJobs      = jobs.filter((j) => j.saved);
  const postsWithEmail = posts.filter((p) => p.contact_email).length;
  const sources        = Array.from(new Set(jobs.map((j) => j.source))).sort();

  const tabJobs =
    activeTab === "applied" ? appliedJobs :
    activeTab === "saved"   ? savedJobs   : jobs;

  const tabCount = (tab: Tab) => {
    if (tab === "jobs")    return jobs.length;
    if (tab === "posts")   return posts.length;
    if (tab === "saved")   return savedJobs.length;
    if (tab === "applied") return appliedJobs.length;
    return undefined;
  };

  const showSidebar = activeTab === "jobs" || activeTab === "applied" || activeTab === "saved";

  return (
    <>
      {/* Background orbs */}
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      <main className="relative min-h-screen z-10">
        {/* ── Premium header ──────────────────────────────────────────── */}
        <header className="sticky top-0 z-30 glass-strong border-b border-slate-700/50">
          <div className="max-w-screen-2xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between gap-4">

              {/* Brand */}
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
                  <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-lg font-bold tracking-tight leading-none">
                    <span className="gradient-text">Job</span>
                    <span className="text-white">Scraper</span>
                    <span className="ml-2 text-[10px] font-medium bg-sky-500/10 border border-sky-500/30 text-sky-400 px-2 py-0.5 rounded-full align-middle">
                      AI · Phase 2
                    </span>
                  </h1>
                  <p className="text-[11px] text-slate-500 mt-1">
                    {jobs.length} jobs &middot; {posts.length} recruiters
                    {postsWithEmail > 0 && (
                      <span className="text-amber-400"> &middot; {postsWithEmail} emails</span>
                    )}
                    {lastUpdated && <span> &middot; {lastUpdated}</span>}
                  </p>
                </div>
              </div>

              {/* Controls */}
              <div className="flex items-center gap-3 flex-shrink-0">
                <button
                  onClick={fetchData}
                  disabled={loading}
                  title="Refresh data"
                  className="flex items-center gap-2 px-3.5 py-2 rounded-xl glass border border-slate-700/50 hover:border-slate-600 text-slate-300 hover:text-white text-sm font-medium transition-all disabled:opacity-40"
                >
                  <svg
                    className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <span className="hidden sm:inline">Refresh</span>
                </button>

                {/* ★ GitHub Actions trigger button */}
                <div className="w-60">
                  <WorkflowTrigger />
                </div>
              </div>
            </div>
          </div>
        </header>

        <div className="max-w-screen-2xl mx-auto px-6 py-6 space-y-6">

          {/* Stats */}
          <StatsBar jobs={jobs} posts={posts} />

          {/* Tabs */}
          <div className="flex flex-wrap gap-1 glass border border-slate-700/50 p-1 rounded-2xl w-fit">
            {TABS.map((tab) => {
              const count   = tabCount(tab.id);
              const active  = activeTab === tab.id;
              const hasAlert = tab.id === "posts" && postsWithEmail > 0;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    relative px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200
                    ${active
                      ? "bg-gradient-to-r from-sky-600 to-indigo-600 text-white shadow-lg shadow-blue-500/20"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                    }
                  `}
                >
                  <span className="flex items-center gap-1.5">
                    <span className="text-[12px] opacity-70">{tab.icon}</span>
                    {tab.label}
                    {count !== undefined && count > 0 && (
                      <span className={`
                        text-[10px] px-1.5 py-0.5 rounded-full font-semibold
                        ${active
                          ? "bg-white/20 text-white"
                          : hasAlert
                            ? "bg-amber-500/20 text-amber-400 blink"
                            : "bg-slate-700 text-slate-400"
                        }
                      `}>
                        {count}
                      </span>
                    )}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Main content */}
          {activeTab === "posts" ? (
            <LinkedInPosts posts={posts} />
          ) : activeTab === "analytics" ? (
            <AnalyticsPage jobs={jobs} posts={posts} />
          ) : activeTab === "kanban" ? (
            <KanbanBoard jobs={jobs} onApplied={handleApplied} onSaved={handleSaved} />
          ) : (
            <div className="flex gap-6">
              {showSidebar && (
                <FilterSidebar filters={filters} sources={sources} onChange={setFilters} />
              )}
              <div className="flex-1 min-w-0">
                {loading && jobs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-24 text-slate-500 gap-4">
                    <div className="w-10 h-10 border-2 border-sky-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-sm">Loading jobs…</p>
                  </div>
                ) : (
                  <JobsGrid
                    jobs={tabJobs}
                    filters={
                      activeTab === "applied" || activeTab === "saved"
                        ? { ...filters, role: "all" }
                        : filters
                    }
                    onApplied={handleApplied}
                    onSaved={handleSaved}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
