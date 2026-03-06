"""
recruiter_scoring.py — Multi-factor confidence scoring for recruiter candidates.

Scoring matrix (max = 100):

  +40  Same company as job posting  (exact or fuzzy match)
  +20  Recruiter / TA title detected
  +15  Technical / Engineering recruiter (more specific)
  +10  Hiring Manager or Engineering Manager
  +20  Location match (city or state overlap)
  +10  Has an email address (rare but very high signal)
  +5   Seniority bonus (senior / director / VP)
  −10  Company mismatch (different company clearly detected)

The score is capped at 100 and floored at 0.

Design notes:
  • Fuzzy company matching handles "AWS" ≡ "Amazon Web Services" etc.
  • Location matching is forgiving (state-level is sufficient).
  • A job record may have no location — skip location check gracefully.
"""

import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ── Alias map for common company abbreviations ────────────────────────────────
_COMPANY_ALIASES: Dict[str, str] = {
    "aws":         "amazon",
    "amazon web services": "amazon",
    "gcp":         "google",
    "google cloud": "google",
    "microsoft azure": "microsoft",
    "azure":       "microsoft",
    "meta":        "facebook",
    "alphabet":    "google",
    "waymo":       "google",
    "deepmind":    "google",
}


def _normalise_company(name: str) -> str:
    """Lowercase, strip punctuation, resolve known aliases."""
    clean = re.sub(r"[^\w\s]", "", name.lower()).strip()
    return _COMPANY_ALIASES.get(clean, clean)


def _company_match_score(job_company: str, recruiter_company: str) -> int:
    """
    Return:
      +40  if companies match (exact or alias-based fuzzy)
      −10  if companies clearly differ (recruiter_company is non-empty and different)
        0  if recruiter_company is empty / unknown
    """
    if not recruiter_company:
        return 0

    jc = _normalise_company(job_company)
    rc = _normalise_company(recruiter_company)

    if not jc or not rc:
        return 0

    # Exact match
    if jc == rc:
        return 40

    # Substring match (e.g. "snowflake computing" ≡ "snowflake")
    if jc in rc or rc in jc:
        return 35

    # Token overlap — share at least one significant word
    jc_words = set(jc.split())
    rc_words = set(rc.split())
    common   = jc_words & rc_words - {"inc", "llc", "ltd", "corp", "group", "company"}
    if common:
        return 20

    # Clearly a different company
    return -10


def _title_score(title: str) -> int:
    """
    Score the recruiter's title:
      +15  technical / engineering recruiter (domain-specific)
      +10  hiring manager or engineering manager
      +20  generic TA / recruiter (baseline)
    """
    t = title.lower()
    if "technical" in t or "engineering" in t:
        return 20 + 15   # base recruiter + technical bonus = 35 total, capped later
    if "hiring manager" in t or "engineering manager" in t:
        return 20 + 10
    if "talent acquisition" in t or "recruiter" in t or "talent partner" in t or "staffing" in t:
        return 20
    return 0


def _location_score(job_location: str, recruiter_location: str) -> int:
    """
    +20 if city-level match, +10 if state-level match, 0 otherwise.
    Treat 'Remote' as a wildcard match.
    """
    if not job_location or not recruiter_location:
        return 0

    jl = job_location.lower()
    rl = recruiter_location.lower()

    if "remote" in jl or "remote" in rl:
        return 10   # Remote roles can have recruiters anywhere

    # Exact city/area match
    if jl == rl:
        return 20

    # Try token overlap (state abbreviation, city name)
    jl_tokens = set(re.split(r"[\s,]+", jl))
    rl_tokens  = set(re.split(r"[\s,]+", rl))
    if jl_tokens & rl_tokens:
        return 20

    # State abbreviation match (two-letter token)
    jl_states = {t for t in jl_tokens if len(t) == 2}
    rl_states  = {t for t in rl_tokens  if len(t) == 2}
    if jl_states & rl_states:
        return 10

    return 0


def _seniority_bonus(seniority: int) -> int:
    """Seniority tiers 4–5 get a bonus — they own headcount decisions."""
    if seniority >= 4:
        return 5
    return 0


def score_recruiter(
    recruiter: Dict[str, Any],
    job: Dict[str, Any],
) -> int:
    """
    Compute a 0–100 confidence score for how likely this recruiter is
    associated with the given job.
    """
    points = 0

    job_company  = job.get("company", "")
    job_location = job.get("location", "")

    rec_company  = recruiter.get("company", "")
    rec_title    = recruiter.get("title", "")
    rec_location = recruiter.get("location", "")
    rec_seniority = recruiter.get("seniority", 1)
    has_email    = bool(recruiter.get("email", "").strip())

    # 1. Company match
    points += _company_match_score(job_company, rec_company)

    # 2. Title match
    points += _title_score(rec_title)

    # 3. Location match
    points += _location_score(job_location, rec_location)

    # 4. Has email — very high confidence signal
    if has_email:
        points += 10

    # 5. Seniority bonus
    points += _seniority_bonus(rec_seniority)

    score = max(0, min(100, points))
    logger.debug(
        "Scored '%s' @ '%s' for job '%s' @ '%s': %d",
        recruiter.get("name"), rec_company,
        job.get("title"), job_company, score,
    )
    return score
