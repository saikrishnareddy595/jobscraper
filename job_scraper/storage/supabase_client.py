"""
Supabase client — persists jobs and linkedin_posts across GitHub Actions runs.
Falls back gracefully if SUPABASE_URL / SUPABASE_SERVICE_KEY are not set.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config

logger = logging.getLogger(__name__)

# DDL run once on first connection to create tables if they don't exist.
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
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
    posted_date     TIMESTAMPTZ,
    easy_apply      BOOLEAN,
    applicants      INTEGER,
    description     TEXT,
    job_type        TEXT DEFAULT 'full_time',
    role_category   TEXT DEFAULT 'data_engineer',
    skills          TEXT[],
    scraped_at      TIMESTAMPTZ DEFAULT NOW(),
    notified        BOOLEAN DEFAULT FALSE,
    applied         BOOLEAN DEFAULT FALSE,
    saved           BOOLEAN DEFAULT FALSE,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS linkedin_posts (
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
    posted_date         TIMESTAMPTZ,
    scraped_at          TIMESTAMPTZ DEFAULT NOW(),
    is_job_posting      BOOLEAN DEFAULT TRUE,
    score               INTEGER DEFAULT 0,
    role_category       TEXT,
    applied             BOOLEAN DEFAULT FALSE,
    saved               BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_jobs_score       ON jobs(score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_posted      ON jobs(posted_date DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_role        ON jobs(role_category);
CREATE INDEX IF NOT EXISTS idx_jobs_type        ON jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_applied     ON jobs(applied);
CREATE INDEX IF NOT EXISTS idx_jobs_saved       ON jobs(saved);
CREATE INDEX IF NOT EXISTS idx_jobs_notified    ON jobs(notified);
CREATE INDEX IF NOT EXISTS idx_posts_posted     ON linkedin_posts(posted_date DESC);
CREATE INDEX IF NOT EXISTS idx_posts_role       ON linkedin_posts(role_category);

-- Phase 2: user feedback for scorer re-training
CREATE TABLE IF NOT EXISTS job_feedback (
    id           BIGSERIAL PRIMARY KEY,
    job_id       BIGINT NOT NULL,
    source_table TEXT NOT NULL DEFAULT 'jobs',
    liked        BOOLEAN NOT NULL,
    rated_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(job_id, source_table)
);
CREATE INDEX IF NOT EXISTS idx_feedback_job ON job_feedback(job_id);

-- Recruiter Discovery tables
CREATE TABLE IF NOT EXISTS recruiters (
    id              BIGSERIAL PRIMARY KEY,
    fingerprint     TEXT      UNIQUE NOT NULL,
    name            TEXT      NOT NULL,
    title           TEXT,
    company         TEXT,
    linkedin_url    TEXT,
    email           TEXT,
    location        TEXT,
    source          TEXT      DEFAULT 'linkedin_search',
    job_url         TEXT,
    confidence_score INTEGER  DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rec_fingerprint ON recruiters(fingerprint);
CREATE INDEX IF NOT EXISTS idx_rec_company     ON recruiters(company);
CREATE INDEX IF NOT EXISTS idx_rec_linkedin    ON recruiters(linkedin_url);
"""


class SupabaseClient:
    def __init__(self):
        self._client = None
        self._available = False
        if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
            try:
                from supabase import create_client
                self._client = create_client(
                    config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY
                )
                self._available = True
                logger.info("Supabase connected: %s", config.SUPABASE_URL)
            except Exception as exc:
                logger.warning("Supabase init failed (falling back to SQLite): %s", exc)
        else:
            logger.info("Supabase not configured — using SQLite only")

    @property
    def available(self) -> bool:
        return self._available

    # ── Jobs ──────────────────────────────────────────────────────────────────
    def upsert_jobs(self, jobs: List[Dict[str, Any]]) -> int:
        if not self._available or not jobs:
            return 0
        rows = [self._job_to_row(j) for j in jobs]
        try:
            self._client.table("jobs").upsert(rows, on_conflict="url").execute()
            logger.info("Supabase: upserted %d jobs", len(rows))
            return len(rows)
        except Exception as exc:
            logger.error("Supabase upsert_jobs failed: %s", exc)
            return 0

    def upsert_posts(self, posts: List[Dict[str, Any]]) -> int:
        if not self._available or not posts:
            return 0
        rows = [self._post_to_row(p) for p in posts]
        try:
            self._client.table("linkedin_posts").upsert(rows, on_conflict="post_url").execute()
            logger.info("Supabase: upserted %d linkedin posts", len(rows))
            return len(rows)
        except Exception as exc:
            logger.error("Supabase upsert_posts failed: %s", exc)
            return 0

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _job_to_row(self, j: Dict[str, Any]) -> Dict[str, Any]:
        posted = j.get("posted_date")
        if isinstance(posted, datetime):
            posted = posted.isoformat()
        return {
            "title":        self._str(j.get("title", "")),
            "company":      self._str(j.get("company", "")),
            "location":     self._str(j.get("location", "")),
            "salary":       j.get("salary"),
            "url":          j.get("url", ""),
            "source":       self._str(j.get("source", "")),
            "score":        j.get("score", 0),
            "llm_score":    j.get("llm_score"),
            "llm_reason":   j.get("llm_reason"),
            "llm_summary":  j.get("llm_summary"),
            "posted_date":  posted,
            "easy_apply":   j.get("easy_apply"),
            "applicants":   j.get("applicants"),
            "description":  j.get("description", ""),
            "job_type":     self._str(j.get("job_type", "full_time")),
            "role_category": self._str(j.get("role_category", "data_engineer")),
            "skills":       j.get("skills", []),
        }

    def _post_to_row(self, p: Dict[str, Any]) -> Dict[str, Any]:
        posted = p.get("posted_date")
        if isinstance(posted, datetime):
            posted = posted.isoformat()
        return {
            "post_text":           p.get("post_text", ""),
            "author_name":         self._str(p.get("author_name", "")),
            "author_headline":     self._str(p.get("author_headline", "")),
            "author_profile_url":  p.get("author_profile_url", ""),
            "extracted_title":     self._str(p.get("extracted_title", "")),
            "extracted_company":   self._str(p.get("extracted_company", "")),
            "contact_email":       p.get("contact_email", ""),
            "contact_linkedin":    p.get("contact_linkedin", ""),
            "contact_name":        self._str(p.get("contact_name", "")),
            "post_url":            p.get("post_url", ""),
            "posted_date":         posted,
            "is_job_posting":      p.get("is_job_posting", True),
            "score":               p.get("score", 0),
            "role_category":       self._str(p.get("role_category", "data_engineer")),
        }

    @staticmethod
    def _str(val: Any) -> str:
        if val is None: return ""
        if isinstance(val, list): return ", ".join(str(v) for v in val)
        return str(val)

