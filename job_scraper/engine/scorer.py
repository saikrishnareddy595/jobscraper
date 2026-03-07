"""
Scorer — assigns a relevance score (0–100) to each job.

Scoring breakdown (max raw = ~125, capped at 100):

  Title relevance (0–20)
    +20  Title contains a core keyword (data engineer, etl, pipeline engineer…)
    +10  Title contains a tech keyword only (spark, kafka, python…)

  Description keywords (0–15)
    +3 per INCLUDE_KEYWORD found in description, capped at 15

  Freshness (0–25)
    +25  Posted ≤ 12 hours ago
    +20  Posted ≤ 24 hours ago
    +10  Posted ≤ 48 hours ago
    +5   Posted ≤ 72 hours ago

  Applicants (0–20)
    +20  Fewer than 25 applicants
    +15  Fewer than 50 applicants
    +10  Fewer than 100 applicants
    +10  No applicant data (partial credit)
    +0   100 or more applicants

  Easy Apply    +15
  Remote/Hybrid +10

  Salary bonus (0–10)
    +10  Salary ≥ $150,000
    +5   Salary ≥ $100,000

  Dream company +15
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import config

logger = logging.getLogger(__name__)

# ── Keyword sets ──────────────────────────────────────────────────────────────
_CORE_TITLE_KW = {
    "data engineer",
    "etl engineer",
    "pipeline engineer",
    "analytics engineer",
    "ml engineer",
    "machine learning engineer",
    "data pipeline",
    "etl developer",
}

_TECH_TITLE_KW = {
    "spark",
    "kafka",
    "airflow",
    "dbt",
    "snowflake",
    "databricks",
    "bigquery",
    "redshift",
    "flink",
    "beam",
    "hive",
    "hadoop",
    "aws",
    "gcp",
    "azure",
    "python",
    "sql",
}

_DREAM_LOWER = {c.lower() for c in config.DREAM_COMPANIES}
_INCLUDE_LOWER = [kw.lower() for kw in config.INCLUDE_KEYWORDS]


class Scorer:
    def score(self, job: Dict[str, Any]) -> int:
        def _to_str(val: Any) -> str:
            if val is None: return ""
            if isinstance(val, list): return ", ".join(str(v) for v in val)
            return str(val)

        points = 0

        # ── 1. Title relevance ────────────────────────────────────────
        title_lower = _to_str(job.get("title")).lower()
        if any(kw in title_lower for kw in _CORE_TITLE_KW):
            points += 20
        elif any(kw in title_lower for kw in _TECH_TITLE_KW):
            points += 10

        # ── 2. Description keyword richness ───────────────────────────
        desc_lower = _to_str(job.get("description")).lower()
        kw_hits = sum(1 for kw in _INCLUDE_LOWER if kw in desc_lower)
        points += min(kw_hits * 3, 15)

        # ── 3. Freshness ──────────────────────────────────────────────
        posted = job.get("posted_date")
        if posted:
            if isinstance(posted, str):
                try:
                    posted = datetime.fromisoformat(posted).replace(tzinfo=timezone.utc)
                except ValueError:
                    posted = None
            if posted:
                age = datetime.now(timezone.utc) - posted
                if age <= timedelta(hours=12):
                    points += 25
                elif age <= timedelta(hours=24):
                    points += 20
                elif age <= timedelta(hours=48):
                    points += 10
                elif age <= timedelta(hours=72):
                    points += 5

        # ── 4. Applicants ─────────────────────────────────────────────
        applicants = job.get("applicants")
        if applicants is not None:
            try:
                n = int(applicants)
                if n < 25:
                    points += 20
                elif n < 50:
                    points += 15
                elif n < 100:
                    points += 10
                # >= 100 → 0
            except (ValueError, TypeError):
                points += 10  # parse failed — partial credit
        else:
            points += 10  # no data — partial credit

        # ── 5. Easy Apply ─────────────────────────────────────────────
        if job.get("easy_apply") is True:
            points += 15

        # ── 6. Remote / Hybrid ────────────────────────────────────────
        location_lower = _to_str(job.get("location")).lower()
        if "remote" in location_lower or "hybrid" in location_lower:
            points += 10


        # ── 7. Salary bonus ───────────────────────────────────────────
        salary = job.get("salary")
        if salary is not None:
            try:
                sal = float(salary)
                if sal >= 150_000:
                    points += 10
                elif sal >= 100_000:
                    points += 5
            except (ValueError, TypeError):
                pass

        # ── 8. Dream company ──────────────────────────────────────────
        # Word-boundary check prevents "Amazon" from matching "AmazingCorp"
        import re as _re
        company_lower = _to_str(job.get("company")).lower()
        if any(_re.search(r'\b' + _re.escape(dream) + r'\b', company_lower) for dream in _DREAM_LOWER):
            points += 15

        return min(points, 100)

    def score_all(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for job in jobs:
            job["score"] = self.score(job)
        jobs.sort(key=lambda j: j["score"], reverse=True)
        return jobs
