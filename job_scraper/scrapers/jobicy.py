"""Jobicy scraper — free API for remote jobs."""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from scrapers.base import BaseAPIScraper, short_delay
import config

logger = logging.getLogger(__name__)

class JobicyScraper(BaseAPIScraper):
    SOURCE = "Jobicy"
    _URL   = "https://jobicy.com/api/v2/remote-jobs"
    _TAGS  = ["data-engineer", "machine-learning", "ai", "etl", "mlops"]

    def scrape(self) -> List[Dict[str, Any]]:
        for tag in self._TAGS:
            try:
                r = self._session.get(self._URL, params={"tag": tag, "count": 50, "geo": "usa"}, timeout=15)
                r.raise_for_status()
                for item in r.json().get("jobs", []):
                    job = self._parse(item)
                    if job:
                        self._add(job)
                short_delay()
            except Exception as exc:
                logger.error("Jobicy tag '%s': %s", tag, exc)
        logger.info("Jobicy: %d jobs", len(self.jobs))
        return self.jobs

    def _fetch_title(self, title): pass

    def _parse(self, item: dict) -> Dict[str, Any]:
        title = item.get("jobTitle", "")
        if not title:
            return {}
        pub = item.get("pubDate", "")
        try:
            posted = datetime.strptime(pub, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            posted = datetime.now(timezone.utc)
        from scrapers.base import parse_salary
        return {
            "title": title, "company": item.get("companyName",""),
            "location": item.get("jobGeo","Remote"),
            "salary": parse_salary(item.get("annualSalaryMin","") or ""),
            "url": item.get("url",""),
            "source": self.SOURCE, "posted_date": posted,
            "easy_apply": True, "applicants": None,
            "description": (item.get("jobDescription","") or "")[:500],
        }
