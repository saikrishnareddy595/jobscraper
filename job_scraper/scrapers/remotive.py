"""Remotive scraper — free public API for remote tech jobs."""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List
from scrapers.base import BaseAPIScraper, short_delay
import config

logger = logging.getLogger(__name__)

class RemotiveScraper(BaseAPIScraper):
    SOURCE = "Remotive"
    _URL   = "https://remotive.com/api/remote-jobs"
    _CATS  = ["software-dev", "data", "devops-sysadmin"]

    def scrape(self) -> List[Dict[str, Any]]:
        for cat in self._CATS:
            try:
                r = self._session.get(self._URL, params={"category": cat, "limit": 100}, timeout=15)
                r.raise_for_status()
                for item in r.json().get("jobs", []):
                    job = self._parse(item)
                    if job:
                        self._add(job)
                short_delay()
            except Exception as exc:
                logger.error("Remotive cat '%s': %s", cat, exc)
        logger.info("Remotive: %d jobs", len(self.jobs))
        return self.jobs

    def _fetch_title(self, title): pass  # not used

    # Accepted candidate_required_location patterns for Remotive (USA / remote / worldwide).
    _USA_LOC_RE = re.compile(
        r"\b(usa?|united states?|remote|anywhere|worldwide|north america|global)\b",
        re.IGNORECASE,
    )

    def _parse(self, item: dict) -> Dict[str, Any]:
        title = item.get("title", "")
        if not title:
            return {}
        # Drop listings explicitly restricted to non-US regions
        raw_loc = item.get("candidate_required_location", "") or ""
        if raw_loc and not self._USA_LOC_RE.search(raw_loc):
            return {}
        pub = item.get("publication_date", "")
        try:
            posted = datetime.fromisoformat(pub.rstrip("Z")).replace(tzinfo=timezone.utc)
        except Exception:
            posted = datetime.now(timezone.utc)
        sal = item.get("salary", "")
        from scrapers.base import parse_salary
        return {
            "title": title, "company": item.get("company_name",""),
            "location": raw_loc or "Remote",
            "salary": parse_salary(sal), "url": item.get("url",""),
            "source": self.SOURCE, "posted_date": posted,
            "easy_apply": True, "applicants": None,
            "description": (item.get("description","") or "")[:500],
        }
