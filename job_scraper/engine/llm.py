"""
NVIDIA NIM LLM client — relevance scoring, skill extraction,
semantic deduplication, and LinkedIn post parsing.

Uses the OpenAI-compatible NVIDIA NIM API:
  Base URL : https://integrate.api.nvidia.com/v1
  Chat model: nvidia/llama-3.1-8b-instruct
  Embed model: nvidia/nv-embedqa-e5-v5
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import config

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None and config.LLM_ENABLED:
        try:
            from openai import OpenAI
            _client = OpenAI(
                api_key=config.NVIDIA_API_KEY,
                base_url=config.NVIDIA_BASE_URL,
            )
        except Exception as exc:
            logger.error("NVIDIA NIM client init failed: %s", exc)
    return _client


# ── Score a single job ────────────────────────────────────────────────────────
def llm_score_job(job: Dict[str, Any]) -> Tuple[Optional[int], Optional[str], Optional[str], List[str]]:
    """
    Returns (llm_score 0-100, reason, 2-line summary, skills list).
    Returns (None, None, None, []) if LLM unavailable.
    """
    client = _get_client()
    if not client:
        return None, None, None, []

    title    = job.get("title", "")
    company  = job.get("company", "")
    location = job.get("location", "")
    salary   = job.get("salary")
    job_type = job.get("job_type", "")

    # Sanitize description to prevent prompt injection: strip control characters
    # and any text that tries to override instructions
    raw_desc = (job.get("description") or "")[:800]
    desc = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw_desc)  # strip control chars

    prompt = f"""You are a job relevance evaluator for a Data Engineer / AI Engineer job seeker.

JOB:
Title: {title}
Company: {company}
Location: {location}
Type: {job_type}
Salary: {salary if salary else 'not listed'}
Description: {desc}

Respond ONLY with valid JSON (no markdown):
{{
  "score": <integer 0-100 relevance score>,
  "reason": "<one sentence why>",
  "summary": "<2-sentence plain-English summary of the role>",
  "skills": ["skill1", "skill2", "skill3"]
}}

Score guide:
90-100: Perfect match (data/AI engineering, great comp, modern stack)
70-89: Strong match
50-69: Good match
30-49: Partial match
0-29: Poor match or unrelated"""

    try:
        resp = client.chat.completions.create(
            model=config.NVIDIA_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content.strip()
        # strip markdown fences if present
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        data = json.loads(raw)
        return (
            int(data.get("score", 50)),
            data.get("reason", ""),
            data.get("summary", ""),
            data.get("skills", []),
        )
    except Exception as exc:
        logger.debug("LLM score failed for '%s': %s", title, exc)
        return None, None, None, []


# ── Batch score jobs ──────────────────────────────────────────────────────────
def llm_score_batch(jobs: List[Dict[str, Any]], max_jobs: int = 150) -> List[Dict[str, Any]]:
    """Enrich up to max_jobs with LLM scores (to stay within free-tier limits)."""
    if not config.LLM_ENABLED:
        return jobs
    scored = 0
    for job in jobs:
        if scored >= max_jobs:
            break
        score, reason, summary, skills = llm_score_job(job)
        if score is not None:
            job["llm_score"]   = score
            job["llm_reason"]  = reason
            job["llm_summary"] = summary
            job["skills"]      = skills
            scored += 1
    logger.info("LLM: enriched %d/%d jobs", scored, len(jobs))
    return jobs


# ── Embeddings for semantic dedup ─────────────────────────────────────────────
def get_embedding(text: str) -> Optional[List[float]]:
    client = _get_client()
    if not client:
        return None
    try:
        resp = client.embeddings.create(
            model=config.NVIDIA_EMBED_MODEL,
            input=text,
            encoding_format="float",
        )
        return resp.data[0].embedding
    except Exception as exc:
        logger.debug("Embedding failed: %s", exc)
        return None


def cosine_similarity(a: List[float], b: List[float]) -> float:
    import math
    dot  = sum(x * y for x, y in zip(a, b))
    na   = math.sqrt(sum(x * x for x in a))
    nb   = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


# ── Parse a raw LinkedIn post ─────────────────────────────────────────────────
def parse_linkedin_post(post_text: str, author_name: str = "") -> Dict[str, Any]:
    """
    Use LLM to extract structured job info from an unstructured LinkedIn post.
    Returns dict with extracted fields.
    """
    client = _get_client()
    if not client:
        return {}

    prompt = f"""Extract job opportunity details from this LinkedIn post.

POST (author: {author_name}):
{post_text[:1500]}

Respond ONLY with valid JSON (no markdown). Use null for missing fields:
{{
  "is_job_posting": <true if this post is about a job opening, false otherwise>,
  "job_title": "<extracted job title or null>",
  "company": "<company name or null>",
  "contact_name": "<person to reach out to or null>",
  "contact_email": "<email address found in post or null>",
  "contact_linkedin": "<LinkedIn profile URL mentioned or null>",
  "role_category": "<one of: data_engineer, ai_engineer, ml_engineer, nlp_engineer, cv_engineer, data_scientist, other>",
  "score": <integer 0-100 relevance for a data/AI engineer job seeker>
}}"""

    try:
        resp = client.chat.completions.create(
            model=config.NVIDIA_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        return json.loads(raw)
    except Exception as exc:
        logger.debug("LinkedIn post parse failed: %s", exc)
        return {"is_job_posting": True, "score": 30}
