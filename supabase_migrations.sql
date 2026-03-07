-- =============================================================
-- Supabase schema migrations for jobscraper
-- Run these in your Supabase SQL Editor (Dashboard → SQL Editor)
-- =============================================================

-- ── jobs table ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.jobs (
    id              BIGSERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    company         TEXT,
    location        TEXT,
    salary          INTEGER,
    url             TEXT UNIQUE NOT NULL,
    source          TEXT,
    score           INTEGER DEFAULT 0,
    llm_score       INTEGER,
    llm_reason      TEXT,
    llm_summary     TEXT,
    posted_date     TEXT,
    easy_apply      BOOLEAN,
    applicants      INTEGER,
    description     TEXT,
    job_type        TEXT DEFAULT 'full_time',
    role_category   TEXT DEFAULT 'data_engineer',
    skills          TEXT,
    scraped_at      TEXT,
    notified        BOOLEAN DEFAULT FALSE,
    applied         BOOLEAN DEFAULT FALSE,
    saved           BOOLEAN DEFAULT FALSE,
    notes           TEXT
);

-- ── recruiters table ──────────────────────────────────────────────────────────
-- REQUIRED: The recruiter discovery module writes to this table.
-- If it doesn't exist you'll see: "Could not find the table 'public.recruiters'"
CREATE TABLE IF NOT EXISTS public.recruiters (
    id               BIGSERIAL PRIMARY KEY,
    fingerprint      TEXT UNIQUE NOT NULL,
    name             TEXT NOT NULL,
    title            TEXT,
    company          TEXT,
    linkedin_url     TEXT,
    email            TEXT,
    location         TEXT,
    source           TEXT DEFAULT 'linkedin_search',
    job_url          TEXT,
    confidence_score INTEGER DEFAULT 0,
    created_at       TEXT,
    updated_at       TEXT
);

-- ── linkedin_posts table ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.linkedin_posts (
    id                  BIGSERIAL PRIMARY KEY,
    post_text           TEXT,
    author_name         TEXT,
    author_headline     TEXT,
    author_profile_url  TEXT,
    extracted_title     TEXT,
    extracted_company   TEXT,
    contact_email       TEXT,
    contact_linkedin    TEXT,
    contact_name        TEXT,
    post_url            TEXT UNIQUE,
    posted_date         TEXT,
    scraped_at          TEXT,
    is_job_posting      BOOLEAN DEFAULT TRUE,
    score               INTEGER DEFAULT 0,
    role_category       TEXT
);

-- ── Row Level Security ─────────────────────────────────────────────────────────
-- Disable RLS on all tables so the anon key can read jobs from the website.
-- The service key bypasses RLS anyway; this allows the anon key too.
ALTER TABLE public.jobs            DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.recruiters      DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.linkedin_posts  DISABLE ROW LEVEL SECURITY;

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_jobs_score       ON public.jobs(score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at  ON public.jobs(scraped_at);
CREATE INDEX IF NOT EXISTS idx_jobs_url         ON public.jobs(url);
CREATE INDEX IF NOT EXISTS idx_recruiters_fp    ON public.recruiters(fingerprint);
