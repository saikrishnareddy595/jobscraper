"""
Filter — removes jobs that don't meet search criteria.

Rules enforced:
  1. Salary < MIN_SALARY (if known)
  2. Contains EXCLUDE_KEYWORDS in title or description
  3. Posted more than MAX_JOB_AGE_HOURS ago
  4. Applicants > MAX_APPLICANTS (if known and EASY_APPLY_ONLY = False still filters saturated)
  5. Easy-apply only mode (if EASY_APPLY_ONLY = True)
  6. Location is outside USA / Remote (non-US country explicitly detected)
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import config

logger = logging.getLogger(__name__)

_EXCLUDE_LOWER = [kw.lower() for kw in config.EXCLUDE_KEYWORDS]

# ── USA / Remote location filter ───────────────────────────────────────────────
# Patterns that confirm the job IS in the USA or remote-friendly for US workers.
_USA_OK_RE = re.compile(
    r"\b(usa?|united states?|remote|anywhere|worldwide|north america|global)\b",
    re.IGNORECASE,
)

# Explicit non-US country signals — reject when detected (and no US signal present).
_NON_USA_RE = re.compile(
    r"\b("
    r"uk|united kingdom|england|scotland|wales|ireland|northern ireland"
    r"|germany|deutschland|france|spain|portugal|italy|netherlands|belgium"
    r"|sweden|norway|denmark|finland|switzerland|austria|poland|czech"
    r"|romania|hungary|ukraine|russia|turkey"
    r"|india|pakistan|bangladesh|sri lanka|nepal"
    r"|australia|new zealand"
    r"|canada|mexico|brazil|argentina|colombia|chile|peru"
    r"|singapore|malaysia|philippines|indonesia|vietnam|thailand|japan|china|taiwan|korea|hong kong"
    r"|south africa|nigeria|kenya|ghana|egypt|israel|uae|dubai|saudi"
    r")\b",
    re.IGNORECASE,
)


def _is_us_or_remote(location: str) -> bool:
    """Return True if the location is USA, Remote, or unknown (empty / None).
    Returns False only when a clearly non-US country is detected without any US signal.
    """
    if not location:
        return True  # unknown location — pass through, other filters may handle it
    loc = location.strip()
    if _USA_OK_RE.search(loc):
        return True
    if _NON_USA_RE.search(loc):
        return False
    return True  # ambiguous — pass through

# ── Visa sponsorship keywords ───────────────────────────────────────────────────────
# Positive signals: job description explicitly mentions visa sponsorship
_VISA_POSITIVE_KW = [
    "h1b", "h-1b", "h1-b", "h 1b",
    "f1", "f-1", "opt", "cpt", "stem opt",
    "visa sponsor", "sponsorship available", "we sponsor",
    "will sponsor", "sponsor work visa", "visa support",
    "work authorization", "work authorisation",
]

# Negative signals: job description explicitly says NO sponsorship
_VISA_NEGATIVE_KW = [
    "no sponsorship", "no visa", "cannot sponsor", "will not sponsor",
    "sponsorship not available", "must be authorized",
    "must be authorised", "citizens and permanent residents",
    "us citizen", "green card", "gc only", "no h1", "no h-1",
]

# ── Role-category allow / deny lists ──────────────────────────────────────────
# A job title must contain at least one of these phrases to be considered DE.
_DE_TITLE_KEYWORDS = [
    "data engineer", "etl engineer", "pipeline engineer", "analytics engineer",
    "data platform engineer", "data infrastructure engineer", "big data engineer",
    "data architect", "data integration engineer", "data warehouse engineer",
    "cloud data engineer",
]

# Titles that explicitly identify a non-DE role — reject immediately.
_NON_DE_TITLE_KEYWORDS = [
    "machine learning engineer", "ml engineer", "mlops engineer",
    "ml platform engineer", "applied ml engineer", "deep learning engineer",
    "ai engineer", "artificial intelligence engineer", "llm engineer",
    "generative ai engineer", "prompt engineer", "ai/ml engineer",
    "nlp engineer", "natural language processing engineer",
    "conversational ai engineer", "computer vision engineer", "vision ai engineer",
    "data scientist", "applied scientist", "research scientist", "ml scientist",
]


def _assign_role_category(job: Dict[str, Any]) -> str:
    """Detect which role category a job belongs to from its title."""
    title_lower = (job.get("title") or "").lower()
    for category, titles in config.ROLE_CATEGORIES.items():
        for t in titles:
            if t.lower() in title_lower:
                return category
    # fallback: check common patterns
    if any(kw in title_lower for kw in ["data engineer", "etl", "pipeline"]):
        return "data_engineer"
    return "data_engineer"  # default — only DE is in scope now


def _detect_job_type(job: Dict[str, Any]) -> str:
    """Detect job type from existing field or description text."""
    existing = (job.get("job_type") or "").lower().replace(" ", "_")
    if existing in ("full_time", "contract", "contract_to_hire", "part_time"):
        return existing
    # Parse from description / title
    text = " ".join([
        job.get("title", ""),
        job.get("description", ""),
    ]).lower()
    if "contract to hire" in text or "contract-to-hire" in text or "c2h" in text:
        return "contract_to_hire"
    if any(kw in text for kw in ["contract", "contractor", "1099", "corp to corp", "c2c"]):
        return "contract"
    if "part time" in text or "part-time" in text:
        return "part_time"
    return "full_time"


def _detect_visa_sponsorship(job: Dict[str, Any]) -> Optional[bool]:
    """
    Scan job title + description for visa sponsorship signals.

    Returns:
      True  — description positively mentions H1B/F1/OPT sponsorship
      False — description explicitly says NO sponsorship
      None  — no clear signal either way (label: 'Unknown')
    """
    text = " ".join([
        job.get("title", ""),
        job.get("description", ""),
    ]).lower()

    neg_hit = any(kw in text for kw in _VISA_NEGATIVE_KW)
    pos_hit = any(kw in text for kw in _VISA_POSITIVE_KW)

    if neg_hit and not pos_hit:
        return False
    if pos_hit:
        return True
    return None  # ambiguous — no explicit mention


class Filter:
    def filter(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        passed = []
        removed = 0
        cutoff = datetime.now(timezone.utc) - timedelta(hours=config.MAX_JOB_AGE_HOURS)

        for job in jobs:
            # Enrich with role category + job type + visa sponsorship before filtering
            job["role_category"]    = _assign_role_category(job)
            job["job_type"]         = _detect_job_type(job)
            job["visa_sponsorship"] = _detect_visa_sponsorship(job)

            reason = self._reject_reason(job, cutoff)
            if reason:
                logger.debug(
                    "Filtered '%s' @ %s — %s",
                    job.get("title"), job.get("company"), reason
                )
                removed += 1
            else:
                passed.append(job)

        logger.info("Filter: %d → %d jobs (%d removed)", len(jobs), len(passed), removed)
        return passed

    def _reject_reason(self, job: Dict[str, Any], cutoff: datetime) -> str:
        title_lower = (job.get("title") or "").lower()

        # 0a) Hard reject: title contains a non-DE role keyword
        for kw in _NON_DE_TITLE_KEYWORDS:
            if kw in title_lower:
                return f"non-DE role title: {kw}"

        # 0b) Hard reject: title has no DE keyword at all (pure irrelevant role)
        if not any(kw in title_lower for kw in _DE_TITLE_KEYWORDS):
            return "title does not match any data engineering pattern"

        # 0c) Location must be USA or Remote
        location = job.get("location") or ""
        if not _is_us_or_remote(location):
            return f"non-US location: {location}"

        # 1) Salary check (only when explicitly known)
        salary = job.get("salary")
        if salary is not None:
            try:
                if float(salary) < config.MIN_SALARY:
                    return f"salary {salary} < {config.MIN_SALARY}"
            except (ValueError, TypeError):
                pass

        # 2) Exclude keyword check
        combined = " ".join([
            job.get("title", ""), job.get("description", "")
        ]).lower()
        for kw in _EXCLUDE_LOWER:
            if kw in combined:
                return f"excluded keyword: {kw}"

        # 3) Age check
        posted = job.get("posted_date")
        if posted:
            if isinstance(posted, str):
                try:
                    posted = datetime.fromisoformat(posted).replace(tzinfo=timezone.utc)
                except ValueError:
                    posted = None
            if posted and posted < cutoff:
                return f"too old: {posted.isoformat()}"

        # 4) Applicants cap (only reject if way over — already saturated)
        applicants = job.get("applicants")
        if applicants is not None:
            try:
                if int(applicants) > config.MAX_APPLICANTS:
                    return f"too many applicants: {applicants}"
            except (ValueError, TypeError):
                pass

        # 5) Easy-apply-only mode
        if config.EASY_APPLY_ONLY and job.get("easy_apply") is False:
            return "easy_apply_only mode"

        return None
