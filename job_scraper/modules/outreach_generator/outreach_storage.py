"""
outreach_storage.py — Save generated outreach to SQLite and optionally Supabase.
"""

import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import config

logger = logging.getLogger(__name__)

_CREATE_OUTREACH_SQL = """
CREATE TABLE IF NOT EXISTS outreach_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          TEXT    NOT NULL,
    recruiter_id    TEXT    NOT NULL,
    message_type    TEXT    NOT NULL,
    tone            TEXT,
    subject         TEXT,
    body            TEXT    NOT NULL,
    fit_score       INTEGER,
    status          TEXT    DEFAULT 'generated',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    UNIQUE(job_id, recruiter_id, message_type)
);
CREATE INDEX IF NOT EXISTS idx_outreach_job ON outreach_messages(job_id);
"""

class OutreachStorage:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or config.DB_PATH
        self._conn = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        conn = self._connect()
        conn.executescript(_CREATE_OUTREACH_SQL)
        conn.commit()

    def store_message(self, msg: Dict[str, Any], force: bool = False):
        conn = self._connect()
        now = datetime.now(timezone.utc).isoformat()
        
        on_conflict = "UPDATE SET body=excluded.body, subject=excluded.subject, updated_at=excluded.updated_at" if force else "NOTHING"
        sql = f"""
            INSERT INTO outreach_messages 
            (job_id, recruiter_id, message_type, tone, subject, body, fit_score, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id, recruiter_id, message_type) DO {on_conflict}
        """
        try:
            conn.execute(sql, (
                msg.get("job_id"),
                msg.get("recruiter_id"),
                msg.get("message_type"),
                msg.get("tone"),
                msg.get("subject", ""),
                msg.get("body"),
                msg.get("fit_score", 0),
                now,
                now
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.warning(f"Error saving outreach message: {e}")
            return False

    def get_messages(self, job_id: str, recruiter_id: str):
        conn = self._connect()
        rows = conn.execute("SELECT * FROM outreach_messages WHERE job_id=? AND recruiter_id=?", (job_id, recruiter_id)).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
