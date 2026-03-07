"""
Deduplicator — removes duplicate jobs across multiple sources.

Two-pass strategy:
  1. Exact hash dedup: MD5 of (title + company + location)
  2. Semantic dedup: cosine similarity of NVIDIA NIM embeddings (if available)
     catches "Sr. Data Engineer" == "Senior Data Engineer @ Amazon" etc.
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional

import config

logger = logging.getLogger(__name__)

_SIM_THRESHOLD = 0.97  # cosine similarity above this = duplicate


class Deduplicator:
    def __init__(self):
        self._seen: Dict[str, Dict] = {}  # hash → job
        self._embeddings: List       = []  # list of (embedding, job)

    # ── Main entry ────────────────────────────────────────────────────────────
    def deduplicate(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Pass 1: exact hash dedup
        for job in jobs:
            key = self._make_key(job)
            if key not in self._seen:
                self._seen[key] = job
            else:
                existing = self._seen[key]
                # Prefer richer record: fill in any None fields from the new job
                for field in ("salary", "easy_apply", "description", "applicants", "llm_score", "skills"):
                    if self._seen[key].get(field) is None and job.get(field) is not None:
                        self._seen[key][field] = job[field]

        after_exact = list(self._seen.values())
        logger.info("Dedup pass-1 (exact): %d → %d", len(jobs), len(after_exact))

        # Pass 2: semantic dedup (only if LLM enabled and count manageable)
        if config.LLM_ENABLED and len(after_exact) <= 500:
            after_semantic = self._semantic_dedup(after_exact)
            logger.info("Dedup pass-2 (semantic): %d → %d", len(after_exact), len(after_semantic))
            return after_semantic

        return after_exact

    # ── Semantic dedup via NVIDIA NIM embeddings ──────────────────────────────
    def _semantic_dedup(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        from engine.llm import get_embedding, cosine_similarity

        unique:  List[Dict]        = []
        embeds:  List[List[float]] = []

        for job in jobs:
            text = f"{job.get('title','')} {job.get('company','')} {job.get('location','')}"
            emb  = get_embedding(text)
            if emb is None:
                # LLM unavailable for this job — keep it
                unique.append(job)
                embeds.append([])
                continue

            is_dup = False
            for prev_emb, prev_job in zip(embeds, unique):
                if not prev_emb:
                    continue
                sim = cosine_similarity(emb, prev_emb)
                if sim >= _SIM_THRESHOLD:
                    is_dup = True
                    # Merge: prefer the record with more data
                    if (job.get("salary") is not None and
                            prev_job.get("salary") is None):
                        prev_job.update({k: v for k, v in job.items() if v is not None})
                    break

            if not is_dup:
                unique.append(job)
                embeds.append(emb)

        return unique

    # ── Key ───────────────────────────────────────────────────────────────────
    @staticmethod
    def _make_key(job: Dict[str, Any]) -> str:
        def _to_str(val: Any) -> str:
            if val is None:
                return ""
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val)

        raw = "|".join([
            _to_str(job.get("title")).lower().strip(),
            _to_str(job.get("company")).lower().strip(),
            _to_str(job.get("location")).lower().strip(),
        ])
        return hashlib.md5(raw.encode()).hexdigest()

