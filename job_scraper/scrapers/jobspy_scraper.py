"""
JobSpy scraper — uses python-jobspy to reliably scrape LinkedIn, Indeed,
Glassdoor, ZipRecruiter, and Google Jobs simultaneously.

python-jobspy handles anti-bot measures internally so each site returns
real results instead of 0.
"""

import logging
import random
import re
import time
from datetime import date, datetime, timezone
from typing import Any, Dict, List

import config

logger = logging.getLogger(__name__)

_SITE_LABEL = {
    "linkedin":      "LinkedIn",
    "indeed":        "Indeed",
    "glassdoor":     "Glassdoor",
    "zip_recruiter": "ZipRecruiter",
    "google":        "Google",
}


class JobSpyScraper:
    """One instance per search title — designed to run as a parallel task."""
    SOURCE = "JobSpy"

    def __init__(self, title: str):
        self.title = title
        self.jobs: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    def scrape(self) -> List[Dict[str, Any]]:
        try:
            from jobspy import scrape_jobs
        except ImportError:
            logger.error("python-jobspy not installed.")
            return []

        seen_urls: set = set()
        try:
            batch = self._scrape_title(scrape_jobs, self.title, seen_urls)
            self.jobs.extend(batch)
        except Exception as exc:
            logger.error("JobSpy '%s' failed: %s", self.title, exc, exc_info=True)

        return self.jobs

    # ------------------------------------------------------------------
    def _scrape_title(
        self, scrape_jobs, title: str, seen_urls: set
    ) -> List[Dict[str, Any]]:
        import pandas as pd

        try:
            df = scrape_jobs(
                site_name=["linkedin", "google", "indeed"],
                search_term=title,
                location="United States",
                results_wanted=50,
                hours_old=config.MAX_JOB_AGE_HOURS,
                country_indeed="USA",
                linkedin_fetch_description=True,
                verbose=0,
            )
        except Exception as exc:
            logger.warning("scrape_jobs() call failed for '%s': %s", title, exc)
            return []

        if df is None or df.empty:
            logger.info("JobSpy '%s': no results returned", title)
            return []

        logger.info("JobSpy '%s': %d raw rows", title, len(df))

        results: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            try:
                job = self._row_to_job(row)
                if not job:
                    continue
                url = job.get("url", "")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                results.append(job)
            except Exception as exc:
                logger.debug("JobSpy row parse error: %s", exc)

        logger.info("JobSpy '%s': %d usable jobs", title, len(results))
        return results

    # ------------------------------------------------------------------
    def _row_to_job(self, row) -> Dict[str, Any]:
        import pandas as pd

        def safe_str(val, default: str = "") -> str:
            if val is None:
                return default
            if isinstance(val, float) and pd.isna(val):
                return default
            s = str(val).strip()
            return default if s == "nan" else s

        def safe_bool(val):
            if val is None:
                return None
            if isinstance(val, float) and pd.isna(val):
                return None
            try:
                return bool(val)
            except Exception:
                return None

        def is_missing(val) -> bool:
            if val is None:
                return True
            try:
                import pandas as _pd
                return bool(_pd.isna(val))
            except Exception:
                return False

        def clean_val(val: Any) -> str:
            if val is None:
                return ""
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return safe_str(val)

        job_title = clean_val(row.get("title"))
        if not job_title:
            return {}

        site     = safe_str(row.get("site")).lower()
        source   = _SITE_LABEL.get(site, site.title() if site else self.SOURCE)
        company  = clean_val(row.get("company"))
        location = clean_val(row.get("location"))
        url      = safe_str(row.get("job_url"))
        desc     = safe_str(row.get("description"))[:500]

        # ── Salary ────────────────────────────────────────────────────

        salary   = None
        interval = safe_str(row.get("interval")).lower()
        min_amt  = row.get("min_amount")
        max_amt  = row.get("max_amount")
        vals = []
        if not is_missing(min_amt):
            vals.append(float(min_amt))
        if not is_missing(max_amt):
            vals.append(float(max_amt))
        if vals:
            avg = sum(vals) / len(vals)
            if "hour" in interval:
                avg *= 2080
            elif "month" in interval:
                avg *= 12
            elif "week" in interval:
                avg *= 52
            elif "day" in interval:
                avg *= 260
            salary = int(avg)

        # ── Date posted ───────────────────────────────────────────────
        date_posted = row.get("date_posted")
        posted_date = datetime.now(timezone.utc)
        if not is_missing(date_posted):
            try:
                if hasattr(date_posted, "to_pydatetime"):
                    dt = date_posted.to_pydatetime()
                    posted_date = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
                elif isinstance(date_posted, datetime):
                    posted_date = (
                        date_posted.replace(tzinfo=timezone.utc)
                        if date_posted.tzinfo is None
                        else date_posted
                    )
                elif isinstance(date_posted, date):
                    posted_date = datetime(
                        date_posted.year, date_posted.month, date_posted.day,
                        tzinfo=timezone.utc,
                    )
                elif isinstance(date_posted, str):
                    posted_date = datetime.fromisoformat(date_posted).replace(
                        tzinfo=timezone.utc
                    )
            except Exception as exc:
                logger.debug("Date parse error (%s): %s", date_posted, exc)

        # ── Easy Apply (LinkedIn only) ────────────────────────────────
        easy_apply = safe_bool(row.get("is_easy_apply"))

        # ── Applicants (LinkedIn only — string like "42" or "Over 200") ──
        applicants = None
        num_app = row.get("num_applicants")
        if not is_missing(num_app):
            num_app_str = str(num_app).strip().lower()
            m = re.search(r"\d+", num_app_str)
            if m:
                parsed = int(m.group())
                # "Over 200" / "200+" means at least that many — treat as 2× to avoid
                # under-filtering saturated postings
                if "over" in num_app_str or "+" in num_app_str:
                    parsed = parsed * 2
                applicants = parsed

        return {
            "title":       job_title,
            "company":     company,
            "location":    location,
            "salary":      salary,
            "url":         url,
            "source":      source,
            "posted_date": posted_date,
            "easy_apply":  easy_apply,
            "applicants":  applicants,
            "description": desc,
        }
