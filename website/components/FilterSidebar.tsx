"use client";

import { Filters, JobType, RoleCategory } from "@/lib/types";

interface Props {
  filters: Filters;
  sources: string[];
  onChange: (f: Filters) => void;
}

const ROLES: { value: RoleCategory; label: string }[] = [
  { value: "all",           label: "All Roles" },
  { value: "data_engineer", label: "Data Engineer" },
  { value: "ai_engineer",   label: "AI Engineer" },
  { value: "ml_engineer",   label: "ML Engineer" },
  { value: "nlp_engineer",  label: "NLP Engineer" },
  { value: "cv_engineer",   label: "CV Engineer" },
  { value: "data_scientist",label: "Data Scientist" },
];

const JOB_TYPES: { value: JobType; label: string }[] = [
  { value: "full_time",        label: "Full-Time" },
  { value: "contract",         label: "Contract" },
  { value: "contract_to_hire", label: "Contract-to-Hire" },
  { value: "part_time",        label: "Part-Time" },
];

const SORT_OPTIONS = [
  { value: "score",  label: "Score" },
  { value: "date",   label: "Date Posted" },
  { value: "salary", label: "Salary" },
];

const VISA_OPTIONS: { value: Filters["visaFilter"]; label: string }[] = [
  { value: "all",            label: "All" },
  { value: "sponsors",       label: "Sponsors H1B" },
  { value: "no_sponsorship", label: "No Sponsorship" },
];

const DEFAULT_FILTERS: Filters = {
  role: "all",
  jobTypes: [],
  sources: [],
  minScore: 0,
  remoteOnly: false,
  easyApplyOnly: false,
  visaFilter: "all",
  search: "",
  sortBy: "score",
};

export default function FilterSidebar({ filters, sources, onChange }: Props) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });

  const toggleJobType = (t: JobType) => {
    const next = filters.jobTypes.includes(t)
      ? filters.jobTypes.filter((x) => x !== t)
      : [...filters.jobTypes, t];
    set({ jobTypes: next });
  };

  const toggleSource = (s: string) => {
    // Fixed: checked = sources list includes this source (empty = all selected = no restriction)
    const next = filters.sources.includes(s)
      ? filters.sources.filter((x) => x !== s)
      : [...filters.sources, s];
    set({ sources: next });
  };

  const selectAllSources = () => set({ sources: [] });
  const clearAllSources  = () => set({ sources: sources });

  const activeFilters = [
    filters.role !== "all",
    filters.jobTypes.length > 0,
    filters.sources.length > 0,
    filters.minScore > 0,
    filters.remoteOnly,
    filters.easyApplyOnly,
    filters.visaFilter !== "all",
    !!filters.search,
  ].filter(Boolean).length;

  return (
    <aside className="w-64 flex-shrink-0 glass border border-slate-700/50 rounded-2xl p-4 space-y-5 h-fit sticky top-24">

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold text-slate-300 uppercase tracking-widest">Filters</h2>
        {activeFilters > 0 && (
          <span className="text-[10px] bg-sky-500/20 text-sky-400 border border-sky-500/30 px-2 py-0.5 rounded-full font-semibold">
            {activeFilters} active
          </span>
        )}
      </div>

      {/* Search */}
      <div>
        <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Search</label>
        <input
          type="text"
          value={filters.search}
          onChange={(e) => set({ search: e.target.value })}
          placeholder="Title, company…"
          className="w-full glass border border-slate-600/50 rounded-xl px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500/60 transition-colors"
        />
      </div>

      {/* Sort */}
      <div>
        <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Sort By</label>
        <select
          value={filters.sortBy}
          onChange={(e) => set({ sortBy: e.target.value as Filters["sortBy"] })}
          className="w-full glass border border-slate-600/50 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500/60 transition-colors"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Role */}
      <div>
        <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Role Category</label>
        <div className="space-y-0.5">
          {ROLES.map((r) => (
            <button
              key={r.value}
              onClick={() => set({ role: r.value })}
              className={`w-full text-left px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                filters.role === r.value
                  ? "bg-gradient-to-r from-sky-600 to-indigo-600 text-white shadow-md shadow-blue-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/60"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Min Score */}
      <div>
        <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
          Min Score: <span className="text-sky-400 font-bold">{filters.minScore}</span>
        </label>
        <input
          type="range"
          min={0} max={100}
          value={filters.minScore}
          onChange={(e) => set({ minScore: Number(e.target.value) })}
          className="w-full accent-sky-500"
        />
        <div className="flex justify-between text-[10px] text-slate-600 mt-0.5">
          <span>0</span><span>50</span><span>100</span>
        </div>
      </div>

      {/* Job Type */}
      <div>
        <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Job Type</label>
        <div className="space-y-1">
          {JOB_TYPES.map((t) => (
            <label key={t.value} className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                checked={filters.jobTypes.includes(t.value)}
                onChange={() => toggleJobType(t.value)}
                className="accent-sky-500"
              />
              <span className="text-xs text-slate-400 group-hover:text-slate-200 transition-colors">{t.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Visa Sponsorship */}
      <div>
        <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Visa Sponsorship</label>
        <div className="space-y-0.5">
          {VISA_OPTIONS.map((o) => (
            <button
              key={o.value}
              onClick={() => set({ visaFilter: o.value })}
              className={`w-full text-left px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                filters.visaFilter === o.value
                  ? "bg-gradient-to-r from-sky-600 to-indigo-600 text-white"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/60"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {/* Toggles */}
      <div className="space-y-2">
        <label className="flex items-center gap-2 cursor-pointer group">
          <input
            type="checkbox"
            checked={filters.remoteOnly}
            onChange={(e) => set({ remoteOnly: e.target.checked })}
            className="accent-sky-500"
          />
          <span className="text-xs text-slate-400 group-hover:text-slate-200 transition-colors">Remote Only</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer group">
          <input
            type="checkbox"
            checked={filters.easyApplyOnly}
            onChange={(e) => set({ easyApplyOnly: e.target.checked })}
            className="accent-sky-500"
          />
          <span className="text-xs text-slate-400 group-hover:text-slate-200 transition-colors">⚡ Easy Apply Only</span>
        </label>
      </div>

      {/* Sources */}
      {sources.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Sources</label>
            <div className="flex gap-2">
              <button onClick={selectAllSources} className="text-[10px] text-sky-500 hover:text-sky-400 transition-colors">All</button>
              <span className="text-slate-600">·</span>
              <button onClick={clearAllSources} className="text-[10px] text-slate-500 hover:text-slate-400 transition-colors">None</button>
            </div>
          </div>
          <div className="space-y-1 max-h-44 overflow-y-auto scrollbar-thin pr-1">
            {sources.map((s) => (
              <label key={s} className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="checkbox"
                  // Fix: empty sources list = "all selected" (no restriction)
                  // checked = either all are selected (empty array) OR this source is in the list
                  checked={filters.sources.length === 0 || filters.sources.includes(s)}
                  onChange={() => toggleSource(s)}
                  className="accent-sky-500"
                />
                <span className="text-xs text-slate-500 group-hover:text-slate-300 transition-colors">{s}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Reset */}
      <button
        onClick={() => onChange(DEFAULT_FILTERS)}
        className="w-full text-xs text-slate-500 hover:text-red-400 py-1.5 glass border border-slate-700/40 rounded-lg transition-colors hover:border-red-700/40"
      >
        Reset All Filters
      </button>
    </aside>
  );
}
