"""
outreach_engine.py — Orchestrator for the automated recruiter outreach generator.
"""

import logging
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import config

from .fit_analyzer import analyze_job_fit
from .message_builder import build_message
from .validators import validate_message
from .outreach_storage import OutreachStorage

logger = logging.getLogger(__name__)

# Core message types
MESSAGE_TYPES = [
    "linkedin_dm_short",
    "linkedin_dm_standard",
    "recruiter_email",
    "follow_up_message"
]

class OutreachEngine:
    def __init__(self, override_candidate_profile: Optional[Dict] = None):
        self._storage = OutreachStorage()
        if override_candidate_profile:
            self._candidate = override_candidate_profile
        else:
            from engine.resume import parse_resume
            self._candidate = dict(parse_resume())
            if not self._candidate.get("preferred_locations"):
                self._candidate["preferred_locations"] = ["Remote", "Hybrid"]

    def generate_for_job_and_recruiters(self, 
        job: Dict[str, Any], 
        recruiters: List[Dict[str, Any]], 
        force: bool = False,
        tone: str = "professional, confident"
    ) -> List[Dict[str, Any]]:
        """
        Main interface to generate outreach for a given job and its discovered recruiters.
        """
        results = []
        job_id = job.get("url", "") or job.get("job_url", "")
        if not job_id:
            return results

        for rec in recruiters:
            rec_id = rec.get("linkedin_url", "") or rec.get("fingerprint", "") or str(rec.get("id"))
            if not rec_id:
                continue
                
            # If recruiter name isn't there, we can generate a referral style
            # but usually we want to skip or just do generic.
            
            fit_analysis = analyze_job_fit(job, self._candidate)
            
            for mtype in MESSAGE_TYPES:
                # Deduplication check
                if not force:
                    existing = self._storage.get_messages(job_id, rec_id)
                    if any(e.get("message_type") == mtype for e in existing):
                        continue
                        
                draft = build_message(job, rec, self._candidate, fit_analysis, mtype, tone)
                
                if validate_message(
                        draft["body"], mtype, 
                        company=job.get("company", ""), 
                        job_title=job.get("title", "")
                ):
                    msg = {
                        "job_id": job_id,
                        "recruiter_id": rec_id,
                        "message_type": mtype,
                        "tone": tone,
                        "subject": draft["subject"],
                        "body": draft["body"],
                        "fit_score": fit_analysis["fit_score"]
                    }
                    if self._storage.store_message(msg, force=force):
                        results.append(msg)
                        
        if results:
            logger.info(f"Outreach Engine generated {len(results)} messages for job: {job.get('title')}")
            
        return results

    def run_batch(self, jobs: List[Dict[str, Any]], recruiter_map: Dict[str, List[Dict[str, Any]]], max_workers: int = 2) -> int:
        """
        Process outreach in batch.
        """
        count = 0
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Build tasks
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = []
            for job in jobs:
                url = job.get("url", "")
                recs = recruiter_map.get(url, [])
                if recs:
                    futures.append(pool.submit(self.generate_for_job_and_recruiters, job, recs))
                    
            for future in as_completed(futures):
                try:
                    msgs = future.result()
                    count += len(msgs)
                except Exception as e:
                    logger.error(f"Outreach batch failed: {e}")
                    
        return count

    def close(self):
        self._storage.close()
