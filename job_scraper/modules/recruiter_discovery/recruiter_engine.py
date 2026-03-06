"""
recruiter_engine.py — Orchestrator for the Recruiter Discovery pipeline.

Pipeline for a single job:
  1. Extract signals (company, title, location) from the job dict.
  2. Search LinkedIn (via DuckDuckGo) for recruiter profiles.
  3. Parse raw search results into structured recruiter dicts.
  4. Score each recruiter by relevance to this specific job.
  5. Persist to SQLite + Supabase.

Async batch execution:
  run_for_jobs(jobs, max_workers)   →  ThreadPoolExecutor per job

Interface:
  from modules.recruiter_discovery.recruiter_engine import RecruiterEngine

  engine = RecruiterEngine()
  recruiters = engine.discover_recruiters(job)   # synchronous, single job
  engine.run_for_jobs(jobs)                      # async batch
"""

import logging
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import requests

from .linkedin_search    import search_recruiters
from .recruiter_parser   import parse_candidates
from .recruiter_scoring  import score_recruiter
from .recruiter_storage  import RecruiterStorage

logger = logging.getLogger(__name__)

# Minimum confidence score to consider a recruiter worth saving
_MIN_CONFIDENCE = 30

# Maximum recruiters kept per job (top N after scoring)
_MAX_RECRUITERS_PER_JOB = 5

# Default parallelism for batch runs
_DEFAULT_WORKERS = 4


class RecruiterEngine:
    """
    Main entry-point for the recruiter discovery module.

    Thread-safety:
      • Each call to discover_recruiters() creates its own requests.Session
        so multiple workers don't share connection state.
      • RecruiterStorage uses SQLite with check_same_thread=False and
        commits after every write — safe under the GIL with low contention.
    """

    def __init__(self, storage: Optional[RecruiterStorage] = None):
        self._storage = storage or RecruiterStorage()

    # ── Single-job discovery ───────────────────────────────────────────────────

    def discover_recruiters(self, job: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify the most relevant recruiters for a single job posting.

        Args:
            job: Standard job dict from the scraping pipeline.

        Returns:
            List of recruiter dicts (sorted by confidence_score DESC),
            filtered to >= _MIN_CONFIDENCE. Empty list on any failure.
        """
        company   = (job.get("company")  or "").strip()
        title     = (job.get("title")    or "").strip()
        location  = (job.get("location") or "").strip()
        job_url   = (job.get("url")      or "").strip()

        if not company:
            logger.debug("Skipping recruiter discovery — no company for: %s", title)
            return []

        logger.info(
            "Recruiter discovery: '%s' @ '%s' (%s)",
            title, company, location or "unknown location",
        )

        session = requests.Session()

        try:
            # Step 2: Search
            raw_candidates = search_recruiters(
                company=company,
                job_title=title,
                location=location,
                session=session,
            )
        except Exception as exc:
            logger.error(
                "LinkedIn search failed for '%s' @ '%s': %s",
                title, company, exc,
            )
            return []

        if not raw_candidates:
            logger.info("No recruiter candidates found for '%s' @ '%s'", title, company)
            return []

        # Step 3: Parse
        parsed = parse_candidates(raw_candidates, expected_company=company)

        # Step 4: Score
        scored: List[Dict[str, Any]] = []
        for rec in parsed:
            score = score_recruiter(rec, job)
            if score >= _MIN_CONFIDENCE:
                rec["confidence_score"] = score
                scored.append(rec)

        # Sort and cap
        scored.sort(key=lambda r: r["confidence_score"], reverse=True)
        scored = scored[:_MAX_RECRUITERS_PER_JOB]

        # Step 5: Persist
        if scored and job_url:
            try:
                saved = self._storage.save_recruiters_for_job(job, scored)
                logger.info(
                    "Saved %d recruiters for '%s' @ '%s'",
                    saved, title, company,
                )
            except Exception as exc:
                logger.error("Recruiter storage failed for job '%s': %s", job_url, exc)

        return scored

    # ── Batch / async ─────────────────────────────────────────────────────────

    def run_for_jobs(
        self,
        jobs: List[Dict[str, Any]],
        max_workers: int = _DEFAULT_WORKERS,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run recruiter discovery asynchronously for a list of jobs.

        Uses a thread pool so scraping performance is not blocked.
        The main pipeline can call this in fire-and-forget mode by
        not awaiting the result, or use the returned dict for reporting.

        Args:
            jobs:        List of job dicts from the pipeline.
            max_workers: Thread pool size (keep low to avoid rate-limiting).

        Returns:
            Dict mapping job_url → list of recruiter dicts found.
        """
        results: Dict[str, List[Dict[str, Any]]] = {}

        if not jobs:
            return results

        logger.info(
            "RecruiterEngine.run_for_jobs: %d jobs, %d workers",
            len(jobs), max_workers,
        )

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_job: Dict[Future, Dict[str, Any]] = {
                pool.submit(self._safe_discover, job): job
                for job in jobs
            }

            for future in as_completed(future_to_job):
                job = future_to_job[future]
                url = job.get("url", "")
                try:
                    recruiters = future.result()
                    results[url] = recruiters
                    logger.info(
                        "  ✓ %-40s → %d recruiter(s)",
                        (f"{job.get('title','?')} @ {job.get('company','?')}")[:40],
                        len(recruiters),
                    )
                except Exception as exc:
                    logger.error(
                        "  ✗ RecruiterEngine job '%s' raised: %s",
                        job.get("title"), exc,
                    )
                    results[url] = []

        total = sum(len(v) for v in results.values())
        logger.info(
            "RecruiterEngine.run_for_jobs complete: %d total recruiters across %d jobs",
            total, len(jobs),
        )
        return results

    def _safe_discover(self, job: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Wrapper that guarantees no exception propagates to the thread pool."""
        try:
            return self.discover_recruiters(job)
        except Exception as exc:
            logger.error(
                "Unhandled exception in discover_recruiters for '%s': %s",
                job.get("title"), exc, exc_info=True,
            )
            return []

    # ── Query helpers ─────────────────────────────────────────────────────────

    def get_recruiters_for_job(self, job_url: str) -> List[Dict[str, Any]]:
        """Retrieve previously discovered recruiters for a job URL."""
        return self._storage.get_recruiters_for_job(job_url)

    def close(self) -> None:
        """Release resources (call at pipeline shutdown)."""
        self._storage.close()
