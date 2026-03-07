"""
SQLite storage handler.
"""

import logging
import sqlite3
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

import config

logger = logging.getLogger(__name__)


_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
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
    easy_apply      INTEGER DEFAULT 0,
    applicants      INTEGER,
    description     TEXT,
    job_type        TEXT DEFAULT 'full_time',
    role_category   TEXT DEFAULT 'data_engineer',
    skills          TEXT, -- JSON string
    scraped_at      TEXT,
    notified        INTEGER DEFAULT 0,
    applied         INTEGER DEFAULT 0,
    saved           INTEGER DEFAULT 0,
    notes           TEXT
);
CREATE INDEX IF NOT EXISTS idx_score      ON jobs(score);
CREATE INDEX IF NOT EXISTS idx_scraped_at ON jobs(scraped_at);
CREATE INDEX IF NOT EXISTS idx_notified   ON jobs(notified);

CREATE TABLE IF NOT EXISTS linkedin_posts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
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
    is_job_posting      INTEGER DEFAULT 1,
    score               INTEGER DEFAULT 0,
    role_category       TEXT
);

CREATE TABLE IF NOT EXISTS recruiters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint     TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    title           TEXT,
    company         TEXT,
    linkedin_url    TEXT,
    email           TEXT,
    location        TEXT,
    source          TEXT DEFAULT 'linkedin_search',
    job_url         TEXT,
    confidence_score INTEGER DEFAULT 0,
    created_at      TEXT,
    updated_at      TEXT
);
"""


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        self._conn = None
        self._init_db()

    def _connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        conn = self._connect()
        conn.executescript(_CREATE_SQL)
        conn.commit()
        logger.debug("Database initialised at %s", self.db_path)

    def upsert_jobs(self, jobs: List[Dict[str, Any]]) -> int:
        """
        Insert or update jobs. Updates scores and metadata but
        preserves 'notified', 'applied', 'saved', and 'notes'.
        """
        conn = self._connect()
        for job in jobs:
            try:
                posted = job.get("posted_date")
                if isinstance(posted, datetime):
                    posted = posted.isoformat()

                easy = job.get("easy_apply")
                easy_int = 1 if easy is True else (0 if easy is False else None)

                skills_json = json.dumps(job.get("skills", []))

                # Use ON CONFLICT to update metadata but preserve user state
                conn.execute(
                    """
                    INSERT INTO jobs (
                        title, company, location, salary, url, source, score,
                        llm_score, llm_reason, llm_summary, posted_date,
                        easy_apply, applicants, description, job_type,
                        role_category, skills, scraped_at, notified
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
                    ON CONFLICT(url) DO UPDATE SET
                        score         = excluded.score,
                        llm_score     = excluded.llm_score,
                        llm_reason    = excluded.llm_reason,
                        llm_summary   = excluded.llm_summary,
                        skills        = excluded.skills,
                        salary        = excluded.salary,
                        applicants    = excluded.applicants,
                        description   = excluded.description,
                        role_category = excluded.role_category,
                        job_type      = excluded.job_type,
                        scraped_at    = excluded.scraped_at
                    """,
                    (
                        self._str(job.get("title", "")),
                        self._str(job.get("company", "")),
                        self._str(job.get("location", "")),
                        job.get("salary"),
                        job.get("url", ""),
                        self._str(job.get("source", "")),
                        job.get("score", 0),
                        job.get("llm_score"),
                        job.get("llm_reason"),
                        job.get("llm_summary"),
                        posted,
                        easy_int,
                        job.get("applicants"),
                        job.get("description", ""),
                        self._str(job.get("job_type", "full_time")),
                        self._str(job.get("role_category", "data_engineer")),
                        skills_json,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            except Exception as exc:
                logger.warning("DB upsert error for '%s': %s", job.get("title"), exc)

        conn.commit()
        return len(jobs)

    def upsert_posts(self, posts: List[Dict[str, Any]]) -> int:
        conn = self._connect()
        for p in posts:
            posted = p.get("posted_date")
            if isinstance(posted, datetime):
                posted = posted.isoformat()
            try:
                conn.execute(
                    """
                    INSERT INTO linkedin_posts (
                        post_text, author_name, author_headline, author_profile_url,
                        extracted_title, extracted_company, contact_email,
                        contact_linkedin, contact_name, post_url,
                        posted_date, scraped_at, is_job_posting, score, role_category
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(post_url) DO UPDATE SET
                        score           = excluded.score,
                        extracted_title = excluded.extracted_title,
                        extracted_company = excluded.extracted_company,
                        post_text       = excluded.post_text
                    """,
                    (
                        self._str(p.get("post_text", "")),
                        self._str(p.get("author_name", "")),
                        self._str(p.get("author_headline", "")),
                        self._str(p.get("author_profile_url", "")),
                        self._str(p.get("extracted_title", "")),
                        self._str(p.get("extracted_company", "")),
                        self._str(p.get("contact_email", "")),
                        self._str(p.get("contact_linkedin", "")),
                        self._str(p.get("contact_name", "")),
                        p.get("post_url", ""),
                        posted,
                        datetime.now(timezone.utc).isoformat(),
                        1 if p.get("is_job_posting") else 0,
                        p.get("score", 0),
                        self._str(p.get("role_category", ""))
                    )
                )
            except Exception as exc:
                logger.warning("DB upsert error for post '%s': %s", p.get("post_url"), exc)
        conn.commit()
        return len(posts)

    def upsert_recruiters(self, recruiters: List[Dict[str, Any]]) -> int:
        conn = self._connect()
        now = datetime.now(timezone.utc).isoformat()
        count = 0
        for r in recruiters:
            fingerprint = r.get("fingerprint")
            if not fingerprint:
                continue
            try:
                conn.execute(
                    """
                    INSERT INTO recruiters (
                        fingerprint, name, title, company, linkedin_url,
                        email, location, source, job_url, confidence_score,
                        created_at, updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(fingerprint) DO UPDATE SET
                        confidence_score = MAX(recruiters.confidence_score, excluded.confidence_score),
                        updated_at       = excluded.updated_at
                    """,
                    (
                        fingerprint,
                        self._str(r.get("name", "")),
                        self._str(r.get("title", "")),
                        self._str(r.get("company", "")),
                        self._str(r.get("linkedin_url", "")),
                        self._str(r.get("email", "")),
                        self._str(r.get("location", "")),
                        self._str(r.get("source", "linkedin_search")),
                        self._str(r.get("job_url", "")),
                        r.get("confidence_score", 0),
                        now,
                        now
                    )
                )
                count += 1
            except Exception as exc:
                logger.warning("DB upsert error for recruiter '%s': %s", fingerprint, exc)
        conn.commit()
        return count

    def get_unnotified(self, min_score: int = 0) -> List[Dict[str, Any]]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM jobs WHERE notified=0 AND score >= ? ORDER BY score DESC",
            (min_score,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def mark_notified(self, ids: List[int]):
        if not ids:
            return
        conn = self._connect()
        placeholders = ",".join("?" * len(ids))
        conn.execute(f"UPDATE jobs SET notified=1 WHERE id IN ({placeholders})", ids)
        conn.commit()

    @staticmethod
    def _str(val: Any) -> str:
        if val is None: return ""
        if isinstance(val, list): return ", ".join(str(v) for v in val)
        return str(val)

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:

        d = dict(row)
        if d.get("skills"):
            try:
                d["skills"] = json.loads(d["skills"])
            except:
                d["skills"] = []
        return d

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
