"""
Arbeitnow scraper — completely free public job board API, no auth required.
API docs: https://www.arbeitnow.com/api/job-board-api
Returns real JSON results with no bot detection or CAPTCHA.
"""

import logging
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

import config

logger = logging.getLogger(__name__)


class ArbeitnowScraper:
    SOURCE = "Arbeitnow"

    _API_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
        self._seen_slugs: set = set()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
            }
        )

    # ------------------------------------------------------------------
    def scrape(self) -> List[Dict[str, Any]]:
        for title in config.JOB_TITLES[:3]:
            try:
                self._fetch_title(title)
                time.sleep(random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX))
            except Exception as exc:
                logger.error("Arbeitnow '%s' failed: %s", title, exc)
        logger.info("Arbeitnow: collected %d jobs", len(self.jobs))
        return self.jobs

    # ------------------------------------------------------------------
    def _fetch_title(self, title: str, pages: int = 4):
        for page in range(1, pages + 1):
            try:
                params = {"q": title, "page": page}
                resp = self._session.get(self._API_URL, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("data", [])

                if not items:
                    break  # no more pages

                for item in items:
                    job = self._parse_item(item)
                    slug = item.get("slug", "")
                    if job and slug not in self._seen_slugs:
                        self._seen_slugs.add(slug)
                        self.jobs.append(job)

                logger.debug("Arbeitnow '%s' page %d: %d items", title, page, len(items))
                time.sleep(random.uniform(1.0, 2.0))

            except Exception as exc:
                logger.warning("Arbeitnow '%s' page %d failed: %s", title, page, exc)

    # ------------------------------------------------------------------
    def _parse_item(self, item: dict) -> Dict[str, Any]:
        title = item.get("title", "")
        if not title:
            return {}

        # Arbeitnow is primarily a European job board — only keep truly remote jobs
        # so non-US office locations don't slip through.
        remote = item.get("remote", False)
        if not remote:
            return {}

        company  = item.get("company_name", "")
        location = item.get("location", "Remote")
        url      = item.get("url", "")
        tags     = item.get("tags", [])
        desc     = (item.get("description", "") or "")[:500]

        # Combine description with tags for keyword scoring
        full_desc = f"{desc} {' '.join(tags)}".strip()

        created_at = item.get("created_at", 0)
        try:
            posted_date = datetime.fromtimestamp(int(created_at), tz=timezone.utc)
        except Exception:
            posted_date = datetime.now(timezone.utc)

        if not location:
            location = "Remote"

        return {
            "title":       title,
            "company":     company,
            "location":    location if location else "Remote",
            "salary":      None,
            "url":         url,
            "source":      self.SOURCE,
            "posted_date": posted_date,
            "easy_apply":  None,
            "applicants":  None,
            "description": full_desc,
        }
