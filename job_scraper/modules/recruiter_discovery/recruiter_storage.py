"""
recruiter_storage.py — Persists recruiter data to SQLite and Supabase.

New tables created:

  recruiters        — canonical recruiter profile (de-duplicated)
  job_recruiters    — many-to-many link between jobs and recruiters

Deduplication strategy:
  • Primary key: linkedin_url  (most reliable identifier)
  • Fallback: MD5(lower(name) + "|" + lower(company))

On conflict the record is updated with the richer version
(e.g. email added after first discovery).
"""

import hashlib
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config

logger = logging.getLogger(__name__)

# ── DDL ───────────────────────────────────────────────────────────────────────
_CREATE_RECRUITERS_SQL = """
CREATE TABLE IF NOT EXISTS recruiters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint     TEXT    UNIQUE NOT NULL,   -- MD5 dedup key
    name            TEXT    NOT NULL,
    title           TEXT,
    company         TEXT,
    linkedin_url    TEXT,
    email           TEXT,
    location        TEXT,
    source          TEXT    DEFAULT 'linkedin_search',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rec_fingerprint ON recruiters(fingerprint);
CREATE INDEX IF NOT EXISTS idx_rec_company     ON recruiters(company);
CREATE INDEX IF NOT EXISTS idx_rec_linkedin    ON recruiters(linkedin_url);
"""

_CREATE_JOB_RECRUITERS_SQL = """
CREATE TABLE IF NOT EXISTS job_recruiters (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    job_url          TEXT    NOT NULL,         -- FK → jobs.url
    recruiter_id     INTEGER NOT NULL,         -- FK → recruiters.id
    confidence_score INTEGER NOT NULL DEFAULT 0,
    discovered_at    TEXT    NOT NULL,
    UNIQUE(job_url, recruiter_id)
);
CREATE INDEX IF NOT EXISTS idx_jr_job_url      ON job_recruiters(job_url);
CREATE INDEX IF NOT EXISTS idx_jr_recruiter_id ON job_recruiters(recruiter_id);
CREATE INDEX IF NOT EXISTS idx_jr_score        ON job_recruiters(confidence_score DESC);
"""


def _fingerprint(name: str, company: str, linkedin_url: str) -> str:
    """Stable dedup key — prefer linkedin_url, fall back to name+company."""
    if linkedin_url and linkedin_url.strip():
        raw = linkedin_url.strip().lower()
    else:
        raw = f"{name.strip().lower()}|{company.strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()


class RecruiterStorage:
    """
    Thin persistence layer for recruiters.

    Initialise once per pipeline run; it reuses the same SQLite connection
    that the main Database class would use (same file path from config).
    Supabase writes are fire-and-forget with no hard dependency.
    """

    def __init__(self, db_path: Optional[str] = None):
        self._db_path    = db_path or config.DB_PATH
        self._conn: Optional[sqlite3.Connection] = None
        self._supabase   = None   # lazily initialised
        self._init_db()
        self._init_supabase()

    # ── Initialisation ────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        conn = self._connect()
        conn.executescript(_CREATE_RECRUITERS_SQL)
        conn.executescript(_CREATE_JOB_RECRUITERS_SQL)
        conn.commit()
        logger.debug("RecruiterStorage: SQLite tables ready at %s", self._db_path)

    def _init_supabase(self) -> None:
        if not (config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY):
            return
        try:
            from supabase import create_client
            self._supabase = create_client(
                config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY
            )
            logger.debug("RecruiterStorage: Supabase client ready")
        except Exception as exc:
            logger.warning("RecruiterStorage: Supabase init failed: %s", exc)

    # ── Public API ────────────────────────────────────────────────────────────

    def upsert_recruiter(self, recruiter: Dict[str, Any]) -> int:
        """
        Insert or update a recruiter record.
        Returns the SQLite row-id of the recruiter.
        """
        fp  = _fingerprint(
            recruiter.get("name", ""),
            recruiter.get("company", ""),
            recruiter.get("linkedin_url", ""),
        )
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()

        try:
            conn.execute(
                """
                INSERT INTO recruiters
                    (fingerprint, name, title, company, linkedin_url,
                     email, location, source, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    name         = COALESCE(NULLIF(excluded.name,''),         recruiters.name),
                    title        = COALESCE(NULLIF(excluded.title,''),        recruiters.title),
                    company      = COALESCE(NULLIF(excluded.company,''),      recruiters.company),
                    linkedin_url = COALESCE(NULLIF(excluded.linkedin_url,''), recruiters.linkedin_url),
                    email        = COALESCE(NULLIF(excluded.email,''),        recruiters.email),
                    location     = COALESCE(NULLIF(excluded.location,''),     recruiters.location),
                    updated_at   = excluded.updated_at
                """,
                (
                    fp,
                    recruiter.get("name", ""),
                    recruiter.get("title", ""),
                    recruiter.get("company", ""),
                    recruiter.get("linkedin_url", ""),
                    recruiter.get("email", ""),
                    recruiter.get("location", ""),
                    recruiter.get("source", "linkedin_search"),
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id FROM recruiters WHERE fingerprint = ?", (fp,)
            ).fetchone()
            rec_id = row["id"] if row else -1
            logger.debug("Upserted recruiter '%s' (id=%d)", recruiter.get("name"), rec_id)
            return rec_id
        except Exception as exc:
            logger.warning("RecruiterStorage.upsert_recruiter error: %s", exc)
            return -1

    def link_job_recruiter(
        self,
        job_url: str,
        recruiter_id: int,
        confidence_score: int,
    ) -> None:
        """Create or update a job ↔ recruiter link."""
        if recruiter_id < 0:
            return
        now  = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO job_recruiters (job_url, recruiter_id, confidence_score, discovered_at)
                VALUES (?,?,?,?)
                ON CONFLICT(job_url, recruiter_id) DO UPDATE SET
                    confidence_score = MAX(excluded.confidence_score, job_recruiters.confidence_score),
                    discovered_at    = excluded.discovered_at
                """,
                (job_url, recruiter_id, confidence_score, now),
            )
            conn.commit()
        except Exception as exc:
            logger.warning("RecruiterStorage.link_job_recruiter error: %s", exc)

    def save_recruiters_for_job(
        self,
        job: Dict[str, Any],
        scored_recruiters: List[Dict[str, Any]],
    ) -> int:
        """
        Persist all scored recruiters for a job and create the link table entries.
        Returns count of recruiters saved.
        """
        job_url = job.get("url", "")
        saved   = 0
        for rec in scored_recruiters:
            rec_id = self.upsert_recruiter(rec)
            if rec_id >= 0:
                self.link_job_recruiter(job_url, rec_id, rec.get("confidence_score", 0))
                saved += 1

        # Async fire-and-forget to Supabase
        if self._supabase and scored_recruiters:
            self._sync_to_supabase(job_url, scored_recruiters)

        return saved

    def get_recruiters_for_job(self, job_url: str) -> List[Dict[str, Any]]:
        """Retrieve all recruiters linked to a job, ordered by confidence."""
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT r.*, jr.confidence_score
            FROM   recruiters r
            JOIN   job_recruiters jr ON jr.recruiter_id = r.id
            WHERE  jr.job_url = ?
            ORDER  BY jr.confidence_score DESC
            """,
            (job_url,),
        ).fetchall()
        return [dict(row) for row in rows]

    # ── Supabase mirror ───────────────────────────────────────────────────────

    def _sync_to_supabase(
        self,
        job_url: str,
        scored_recruiters: List[Dict[str, Any]],
    ) -> None:
        """Mirror recruiter data to Supabase (best-effort, non-blocking)."""
        try:
            rows = [
                {
                    "fingerprint":  _fingerprint(
                        r.get("name", ""), r.get("company", ""), r.get("linkedin_url", "")
                    ),
                    "name":          r.get("name", ""),
                    "title":         r.get("title", ""),
                    "company":       r.get("company", ""),
                    "linkedin_url":  r.get("linkedin_url", ""),
                    "email":         r.get("email", ""),
                    "location":      r.get("location", ""),
                    "source":        r.get("source", "linkedin_search"),
                    "job_url":       job_url,
                    "confidence_score": r.get("confidence_score", 0),
                }
                for r in scored_recruiters
            ]
            (
                self._supabase
                .table("recruiters")
                .upsert(rows, on_conflict="fingerprint")
                .execute()
            )
            logger.debug("Supabase: mirrored %d recruiters for %s", len(rows), job_url[:60])
        except Exception as exc:
            logger.warning("Supabase recruiter sync failed: %s", exc)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
