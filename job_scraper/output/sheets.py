"""
Google Sheets sync — writes jobs with score >= threshold to
'Data Engineer Job Search 2025' spreadsheet using gspread.

Setup:
  1. Create a Google Cloud project
  2. Enable Google Sheets API + Google Drive API
  3. Create a Service Account → download JSON key → save as service_account.json
  4. Share the spreadsheet with the service account email
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Any

import config

logger = logging.getLogger(__name__)

_HEADERS = [
    "Title", "Company", "Location", "Salary", "Score",
    "Source", "Posted Date", "Easy Apply", "Applicants", "URL",
]


class SheetsSync:
    def __init__(self):
        self._gc = None
        self._sheet = None

    # ------------------------------------------------------------------
    def _connect(self):
        """Lazy-connect to Google Sheets."""
        if self._gc is not None:
            return True
        if not config.ENABLE_GOOGLE_SHEETS:
            logger.info("Google Sheets sync disabled (GOOGLE_SPREADSHEET_ID not set)")
            return False
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            sa_path = config.GOOGLE_SERVICE_ACCOUNT_JSON
            if not os.path.exists(sa_path):
                logger.warning(
                    "service_account.json not found at '%s' — Google Sheets sync disabled", sa_path
                )
                return False

            creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
            self._gc = gspread.authorize(creds)
            logger.info("Google Sheets: connected")
            return True
        except Exception as exc:
            logger.error("Google Sheets connect failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    def _get_worksheet(self):
        """Open or create the spreadsheet + worksheet."""
        if self._sheet is not None:
            return self._sheet
        try:
            try:
                spreadsheet = self._gc.open(config.GOOGLE_SHEET_NAME)
            except Exception:
                spreadsheet = self._gc.create(config.GOOGLE_SHEET_NAME)
                logger.info("Created new spreadsheet: %s", config.GOOGLE_SHEET_NAME)

            ws = spreadsheet.sheet1
            # Write headers if sheet is empty
            if ws.row_count == 0 or not ws.row_values(1):
                ws.update("A1", [_HEADERS])
                ws.format("A1:J1", {"textFormat": {"bold": True}})

            self._sheet = ws
            return ws
        except Exception as exc:
            logger.error("Google Sheets worksheet error: %s", exc)
            return None

    # ------------------------------------------------------------------
    def sync(self, jobs: List[Dict[str, Any]]) -> int:
        """
        Sync jobs to Google Sheets.
        Returns number of rows written.
        """
        if not self._connect():
            return 0

        ws = self._get_worksheet()
        if ws is None:
            return 0

        # Get existing URLs to avoid duplicates
        try:
            existing_urls = set(ws.col_values(10)[1:])  # column J = URL
        except Exception:
            existing_urls = set()

        new_rows = []
        for job in jobs:
            url = job.get("url", "")
            if url in existing_urls:
                continue

            salary = job.get("salary")
            salary_str = f"${salary:,}" if salary else "N/A"

            posted = job.get("posted_date") or job.get("scraped_at", "")
            if isinstance(posted, datetime):
                posted = posted.strftime("%Y-%m-%d %H:%M")

            easy = job.get("easy_apply")
            easy_str = "Yes" if easy else ("No" if easy is False else "Unknown")

            row = [
                self._str(job.get("title", "")),
                self._str(job.get("company", "")),
                self._str(job.get("location", "")),
                salary_str,
                job.get("score", 0),
                self._str(job.get("source", "")),
                str(posted),
                easy_str,
                str(job.get("applicants") or "N/A"),
                url,
            ]
            new_rows.append(row)
            existing_urls.add(url)

        if new_rows:
            try:
                ws.append_rows(new_rows, value_input_option="USER_ENTERED")
                logger.info("Google Sheets: appended %d new rows", len(new_rows))
            except Exception as exc:
                logger.error("Google Sheets append failed: %s", exc)
                return 0

        return len(new_rows)

    @staticmethod
    def _str(val: Any) -> str:
        if val is None: return ""
        if isinstance(val, list): return ", ".join(str(v) for v in val)
        return str(val)


