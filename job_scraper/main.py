"""
main.py — Orchestrator for the automated job scraping system.

Pipeline:
  1. Run all scrapers in parallel (ThreadPoolExecutor)
     - JobSpy: one task per title (LinkedIn/Indeed/Google per title)
     - All other scrapers: one task each
  2. Deduplicate (exact hash + NVIDIA NIM semantic embeddings)
  3. Filter  (salary, keywords, age, applicants, job_type)
  4. Score   (multi-factor heuristic)
  5. LLM enrich (NVIDIA NIM — score, summary, skill extraction)
  6. Save to SQLite (local) + Supabase (persistent across runs)
  7. Sync high-score jobs to Google Sheets
  8. Send Gmail HTML digest alert
  9. Scrape LinkedIn posts (separate stream → Supabase)

Run once : python main.py
Schedule : GitHub Actions every 6 hours
"""

import logging
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(__file__))

import config

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "scraper.log"),
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("main")

# ── Scraper imports ────────────────────────────────────────────────────────────
from scrapers.jobspy_scraper import JobSpyScraper
from scrapers.dice           import DiceScraper
from scrapers.arbeitnow      import ArbeitnowScraper
from scrapers.adzuna         import AdzunaScraper
from scrapers.remotive       import RemotiveScraper
from scrapers.himalayas      import HimalayasScraper
from scrapers.jobicy         import JobicyScraper
from scrapers.jooble         import JoobleScraper
from scrapers.workingnomads  import WorkingNomadsScraper
from scrapers.weworkremotely import WeWorkRemotelyScraper
from scrapers.usajobs        import USAJobsScraper
from scrapers.staffing_scrapers import BeaconHillScraper
from scrapers.linkedin_posts import LinkedInPostsScraper
from scrapers.hackernews     import HackerNewsHiringScraper

from engine.deduplicator import Deduplicator
from engine.scorer       import Scorer
from engine.filter       import Filter
from engine.llm          import llm_score_batch
from engine.resume       import parse_resume, skill_gap_analysis

from modules.recruiter_discovery.recruiter_engine import RecruiterEngine
from modules.outreach_generator.outreach_engine import OutreachEngine

from storage.db              import Database
from storage.supabase_client import SupabaseClient
from output.sheets           import SheetsSync
from output.notifier         import Notifier
from output.excel_export     import ExcelExporter


def _run_scraper(name: str, scraper_instance) -> Tuple[str, List[Dict[str, Any]]]:
    """Thread-safe wrapper: runs scraper.scrape() and returns (name, jobs)."""
    try:
        jobs = scraper_instance.scrape()
        logger.info("  ✓ %-25s %d jobs", name, len(jobs))
        return name, jobs
    except Exception as exc:
        logger.error("  ✗ %-25s FAILED: %s", name, exc)
        return name, []


def _build_tasks() -> List[Tuple[str, object]]:
    """
    Build the full list of (label, scraper_instance) tasks.
    """
    tasks: List[Tuple[str, object]] = []

    # ── JobSpy — one task per title (runs in parallel) ─────────────────────────
    for title in config.JOBSPY_TITLES:
        label = f"JobSpy:{title}"
        tasks.append((label, JobSpyScraper(title)))

    # ── Reliable free-API scrapers ─────────────────────────────────────────────
    tasks += [
        ("Dice",           DiceScraper()),
        ("Arbeitnow",      ArbeitnowScraper()),
        ("Remotive",       RemotiveScraper()),
        ("Himalayas",      HimalayasScraper()),
        ("Jobicy",         JobicyScraper()),
        ("WorkingNomads",  WorkingNomadsScraper()),
        ("Adzuna",         AdzunaScraper()),
        ("WeWorkRemotely", WeWorkRemotelyScraper()),
        ("Jooble",         JoobleScraper()),
        ("BeaconHill",     BeaconHillScraper()),
    ]

    # ── Phase 2: Hacker News Who’s Hiring ───────────────────────────────────
    if config.ENABLE_HN_SCRAPER:
        tasks.append(("HackerNews", HackerNewsHiringScraper()))

    return tasks


def run() -> None:
    t0 = time.time()
    logger.info("=" * 65)
    logger.info("Job Scraper starting — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("LLM enabled: %s | Supabase: %s", config.LLM_ENABLED, bool(config.SUPABASE_URL))
    logger.info("=" * 65)

    supabase = SupabaseClient()

    # ── Step 1: Parallel scraping ──────────────────────────────────────────────
    tasks = _build_tasks()
    all_jobs: List[Dict[str, Any]] = []
    per_source: Dict[str, int]     = defaultdict(int)

    logger.info("Running %d tasks with %d workers …", len(tasks), config.MAX_WORKERS)
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as pool:
        futures = {
            pool.submit(_run_scraper, name, inst): name
            for name, inst in tasks
        }
        for fut in as_completed(futures):
            name, jobs = fut.result()
            # Group all JobSpy sub-tasks under "JobSpy" in the summary
            summary_key = "JobSpy" if name.startswith("JobSpy:") else name
            per_source[summary_key] += len(jobs)
            all_jobs.extend(jobs)

    logger.info("Total raw jobs collected: %d", len(all_jobs))

    # ── Step 2: Deduplicate ────────────────────────────────────────────────────
    unique_jobs = Deduplicator().deduplicate(all_jobs)

    # ── Step 3: Filter ────────────────────────────────────────────────────────
    filtered_jobs = Filter().filter(unique_jobs)

    # ── Step 4: Heuristic Score ───────────────────────────────────────────────
    scored_jobs = Scorer().score_all(filtered_jobs)

    # ── Step 5: LLM Enrichment (NVIDIA NIM) ──────────────────────────────────
    if config.LLM_ENABLED:
        scored_jobs = llm_score_batch(scored_jobs, max_jobs=500)

    # ── Step 6: Recruiter Discovery (async, non-blocking) ───────────────────
    recruiter_counts: dict = {}
    recruiter_engine = RecruiterEngine()
    if config.ENABLE_RECRUITER_DISCOVERY and scored_jobs:
        # Prioritise top-scoring jobs so the best opportunities get coverage first
        cap = config.RECRUITER_MAX_JOBS or len(scored_jobs)
        discovery_jobs = scored_jobs[:cap]
        logger.info(
            "Recruiter discovery: running on top %d jobs (%d workers) …",
            len(discovery_jobs), config.RECRUITER_WORKERS,
        )
        try:
            recruiter_counts = recruiter_engine.run_for_jobs(
                discovery_jobs, max_workers=config.RECRUITER_WORKERS
            )
        except Exception as exc:
            logger.error("Recruiter discovery failed: %s", exc)
    else:
        logger.info("Recruiter discovery disabled or no jobs to process")

    # ── Step 6.5: Outreach Generator ──────────────────────────────────────────
    outreach_counts = 0
    outreach_engine = OutreachEngine()
    if getattr(config, "ENABLE_OUTREACH_GENERATOR", False) and recruiter_counts:
        logger.info(f"Outreach generation: running on discovered recruiters (tone='{getattr(config, 'OUTREACH_TONE', 'professional')}')")
        try:
            outreach_counts = outreach_engine.run_batch(
                discovery_jobs, recruiter_counts, max_workers=config.RECRUITER_WORKERS
            )
        except Exception as exc:
            logger.error(f"Outreach generation failed: {exc}")

    # ── Step 7: Save ──────────────────────────────────────────────────────────
    db        = Database()
    new_count = db.upsert_jobs(scored_jobs)
    logger.info("SQLite: %d new jobs saved", new_count)

    supabase.upsert_jobs(scored_jobs)

    # ── Step 7: Google Sheets ─────────────────────────────────────────────────
    high_score   = [j for j in scored_jobs if j.get("score", 0) >= config.ALERT_SCORE_THRESHOLD]
    rows_written = SheetsSync().sync(high_score)
    logger.info("Google Sheets: %d rows written", rows_written)

    # ── Step 8: Gmail digest ──────────────────────────────────────────────────
    unnotified = db.get_unnotified(min_score=config.ALERT_SCORE_THRESHOLD)
    if unnotified:
        sent = Notifier().send_digest(unnotified)
        if sent:
            db.mark_notified([j["id"] for j in unnotified])
    else:
        logger.info("No new jobs above threshold to notify about")

    # ── Step 9: LinkedIn Posts (separate stream) ───────────────────────────────
    posts: List[Dict[str, Any]] = []
    if config.LINKEDIN_EMAIL:
        logger.info("Scraping LinkedIn posts …")
        posts = LinkedInPostsScraper().scrape()
        supabase.upsert_posts(posts)
        logger.info("LinkedIn Posts: %d posts pushed to Supabase", len(posts))

    # ── Step 10: Excel Export ─────────────────────────────────────────────────
    excel_path: str = ""
    try:
        excel_path = ExcelExporter().export(scored_jobs, recruiter_counts) or ""
        if excel_path:
            logger.info("Excel export: %s", excel_path)
    except Exception as exc:
        logger.error("Excel export failed: %s", exc)

    db.close()
    recruiter_engine.close()
    outreach_engine.close()

    # ── Phase 2 Step 13: Skill Gap Analysis ───────────────────────────────
    gap_report: Dict[str, Any] = {}
    if config.ENABLE_SKILL_GAP:
        resume = parse_resume()
        gap_report = skill_gap_analysis(scored_jobs, resume)
        logger.info(
            "Skill Gap: top demands=%s | missing=%s",
            [s for s, _ in gap_report.get("top_demanded", [])[:5]],
            gap_report.get("you_are_missing", [])[:5],
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print(f"\n{'='*65}")
    print("  JOB SCRAPER SUMMARY")
    print(f"{'='*65}")
    print(f"  {'Source':<22} {'Jobs':>6}")
    print(f"  {'-'*22} {'-'*6}")
    for name, count in sorted(per_source.items()):
        print(f"  {name:<22} {count:>6}")
    print(f"  {'-'*22} {'-'*6}")
    print(f"  {'TOTAL RAW':<22} {len(all_jobs):>6}")
    print(f"  {'After dedup':<22} {len(unique_jobs):>6}")
    print(f"  {'After filter':<22} {len(filtered_jobs):>6}")
    print(f"  {'New in SQLite':<22} {new_count:>6}")
    print(f"  {'Sheets rows':<22} {rows_written:>6}")
    total_recruiters = sum(len(v) for v in recruiter_counts.values())
    print(f"  {'Recruiters found':<22} {total_recruiters:>6}")
    print(f"  {'Outreach msgs gen':<22} {outreach_counts:>6}")
    print(f"  {'LinkedIn Posts':<22} {len(posts):>6}")
    if excel_path:
        print(f"  {'Excel Export':<22} {os.path.basename(excel_path)}")
    print()
    print(f"  TOP 10 JOBS:")
    print(f"  {'Sc':>3} {'LLM':>3}  {'Title':<35} {'Company':<20} {'Type':<10}")
    print(f"  {'--':>3} {'---':>3}  {'-'*35} {'-'*20} {'-'*10}")
    for job in scored_jobs[:10]:
        print(
            f"  {job.get('score',0):>3} "
            f"{str(job.get('llm_score') or ''):>3}  "
            f"{(job.get('title') or '')[:34]:<35} "
            f"{(job.get('company') or '')[:19]:<20} "
            f"{job.get('job_type',''):<10}"
        )
    print(f"{'='*65}")
    print(f"  Completed in {elapsed:.1f}s")
    print(f"{'='*65}\n")

    # Print skill gap summary if available
    if gap_report and gap_report.get("you_are_missing"):
        print(f"\n{'='*65}")
        print("  SKILL GAP ANALYSIS")
        print(f"{'='*65}")
        print(f"  Top demanded: {', '.join(s for s, _ in gap_report.get('top_demanded', [])[:8])}")
        print(f"  You have:     {', '.join(gap_report.get('you_have', [])[:8])}")
        gap_skills = gap_report.get('you_are_missing', [])
        print(f"  Missing:      {', '.join(gap_skills[:8])}")
        print(f"{'='*65}\n")


if __name__ == "__main__":
    run()
