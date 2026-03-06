"""
recruiter_parser.py — Normalises raw search candidates into structured recruiter dicts.

Responsibilities:
  • Parse recruiter title / company from the LinkedIn headline snippet.
  • Extract email addresses if they appear in the snippet text.
  • Detect seniority level.
  • Return a clean, typed recruiter dict suitable for scoring and storage.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Title patterns we recognise as recruiter roles ────────────────────────────
# Order matters: more specific patterns first.
_TITLE_PATTERNS: List[tuple] = [
    (r"(?:vp|vice president).{0,20}talent",          "VP of Talent Acquisition"),
    (r"head of.{0,20}(?:talent|recruit)",             "Head of Talent Acquisition"),
    (r"director.{0,20}(?:talent|recruit)",            "Director of Talent Acquisition"),
    (r"engineering manager",                          "Engineering Manager"),
    (r"hiring manager",                               "Hiring Manager"),
    (r"senior.{0,15}technical recruiter",             "Senior Technical Recruiter"),
    (r"technical recruiter",                          "Technical Recruiter"),
    (r"senior.{0,15}recruiter",                       "Senior Recruiter"),
    (r"talent acquisition.{0,15}(?:partner|lead)",   "Talent Acquisition Partner"),
    (r"talent acquisition",                           "Talent Acquisition"),
    (r"talent partner",                               "Talent Partner"),
    (r"staffing.{0,15}(?:manager|recruiter)",         "Staffing Manager"),
    (r"recruiting.{0,15}(?:manager|lead)",            "Recruiting Manager"),
    (r"recruiter",                                    "Recruiter"),
    (r"people.{0,15}(?:partner|ops)",                 "People Partner"),
]

# Seniority tier (used in scoring)
_SENIORITY_MAP: Dict[str, int] = {
    "VP of Talent Acquisition":   5,
    "Head of Talent Acquisition": 5,
    "Director of Talent Acquisition": 4,
    "Engineering Manager":        4,
    "Hiring Manager":             4,
    "Senior Technical Recruiter": 3,
    "Senior Recruiter":           3,
    "Talent Acquisition Partner": 3,
    "Technical Recruiter":        2,
    "Recruiting Manager":         2,
    "Staffing Manager":           2,
    "Talent Partner":             2,
    "Talent Acquisition":         1,
    "Recruiter":                  1,
    "People Partner":             1,
}

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

_AT_COMPANY_RE = re.compile(
    r"(?:@|at)\s+([A-Z][A-Za-z0-9&\s\-\.]{1,40})"
)

# ── Known domain overrides for large companies ─────────────────────────────────
# Maps normalised company name → corporate email domain
_COMPANY_DOMAIN_MAP: Dict[str, str] = {
    "google":         "google.com",
    "alphabet":       "google.com",
    "amazon":         "amazon.com",
    "aws":            "amazon.com",
    "microsoft":      "microsoft.com",
    "meta":           "meta.com",
    "facebook":       "meta.com",
    "apple":          "apple.com",
    "nvidia":         "nvidia.com",
    "snowflake":      "snowflake.com",
    "databricks":     "databricks.com",
    "stripe":         "stripe.com",
    "netflix":        "netflix.com",
    "openai":         "openai.com",
    "anthropic":      "anthropic.com",
    "uber":           "uber.com",
    "airbnb":         "airbnb.com",
    "linkedin":       "linkedin.com",
    "salesforce":     "salesforce.com",
    "oracle":         "oracle.com",
    "ibm":            "ibm.com",
    "palantir":       "palantir.com",
    "cohere":         "cohere.com",
    "scale ai":       "scale.com",
    "hugging face":   "huggingface.co",
    "ziprecruiter":   "ziprecruiter.com",
}


def _detect_title(text: str) -> str:
    """Return the best-matching canonical title or empty string."""
    t = text.lower()
    for pattern, canonical in _TITLE_PATTERNS:
        if re.search(pattern, t):
            return canonical
    return ""


def _extract_company_from_headline(headline: str, expected_company: str) -> str:
    """
    Attempt to extract the current company from a LinkedIn headline string
    like "Senior Recruiter at Snowflake | Talent Partner | …"
    Falls back to the expected company if nothing is found.
    """
    # Try 'at Company' pattern
    m = _AT_COMPANY_RE.search(headline)
    if m:
        return m.group(1).strip().rstrip("|").strip()

    # Try pipe-separated parts — pick part that contains expected company
    parts = [p.strip() for p in headline.split("|")]
    exp_lower = expected_company.lower()
    for part in parts:
        if exp_lower in part.lower():
            return part.split("·")[0].strip()

    return expected_company  # fallback


def _extract_email(text: str) -> Optional[str]:
    m = _EMAIL_RE.search(text)
    return m.group(0) if m else None


def _company_to_domain(company: str) -> str:
    """
    Guess the corporate email domain for a company name.

    Resolution order:
      1. Known domain override map  (e.g. "Meta" → "meta.com")
      2. Fallback: lowercase(company).replace spaces with nothing + ".com"
         e.g. "Acme Corp" → "acmecorp.com"  (best-effort)
    """
    key = company.strip().lower()
    if key in _COMPANY_DOMAIN_MAP:
        return _COMPANY_DOMAIN_MAP[key]
    # Strip common suffixes then build domain
    for suffix in [" inc", " llc", " ltd", " corp", " group", " co", " technologies", " tech"]:
        if key.endswith(suffix):
            key = key[: -len(suffix)].strip()
    domain = re.sub(r"[^a-z0-9]", "", key) + ".com"
    return domain


def _guess_emails(name: str, company: str) -> List[str]:
    """
    Generate common corporate email format guesses for a recruiter.

    Returns a list of candidate addresses, best-guess first:
      firstname.lastname@domain.com
      f.lastname@domain.com
      firstname@domain.com
      flastname@domain.com

    Returns [] if name has fewer than 2 parts.
    """
    parts = [p.lower() for p in name.split() if p.isalpha()]
    if len(parts) < 2:
        return []

    first, last = parts[0], parts[-1]
    domain      = _company_to_domain(company)

    return [
        f"{first}.{last}@{domain}",
        f"{first[0]}.{last}@{domain}",
        f"{first}@{domain}",
        f"{first}{last}@{domain}",
    ]


def _extract_location(text: str) -> str:
    """
    Heuristically extract a US location mention from snippet text.
    e.g. "San Francisco Bay Area" / "New York, NY" / "Remote"
    """
    # Simple pattern: City, ST  or  City Area  or  Remote
    m = re.search(
        r"\b(Remote|[A-Z][a-zA-Z\s]+(?:Area|, [A-Z]{2}|, [A-Z][a-z]+))\b",
        text,
    )
    return m.group(1).strip() if m else ""


def parse_candidate(
    raw: Dict[str, Any],
    expected_company: str,
) -> Optional[Dict[str, Any]]:
    """
    Convert a raw search candidate dict into a structured recruiter dict.

    Returns None if the candidate doesn't look like a recruiter at all
    (title detection fails and no recruiter keyword in text).
    """
    headline = raw.get("headline", "")
    snippet  = raw.get("snippet", "")
    combined = f"{headline} {snippet}"

    title = _detect_title(combined)
    if not title:
        # No recognisable recruiter title — skip
        logger.debug("Skipping non-recruiter candidate: %s", headline[:80])
        return None

    company   = _extract_company_from_headline(headline, expected_company)
    email         = _extract_email(combined)
    email_is_ai   = False
    guessed_emails: List[str] = []

    if not email:
        # Real email not found — generate AI-guessed formats
        guessed = _guess_emails(raw.get("name", ""), company)
        if guessed:
            email       = guessed[0]   # best guess as primary
            email_is_ai = True
            guessed_emails = guessed

    location  = _extract_location(combined)
    seniority = _SENIORITY_MAP.get(title, 1)

    return {
        "name":             raw.get("name", "").strip(),
        "title":            title,
        "company":          company,
        "linkedin_url":     raw.get("linkedin_url", ""),
        "email":            email or "",
        "email_is_ai_guess": email_is_ai,
        "guessed_emails":   guessed_emails,   # all format variants
        "location":         location,
        "seniority":        seniority,
        "source":           "linkedin_search",
        # Raw headline preserved for debugging / re-scoring
        "_headline":        headline,
        "_snippet":         snippet,
    }


def parse_candidates(
    raw_list: List[Dict[str, Any]],
    expected_company: str,
) -> List[Dict[str, Any]]:
    """Parse a list of raw candidates and return only valid recruiter dicts."""
    parsed: List[Dict[str, Any]] = []
    for raw in raw_list:
        result = parse_candidate(raw, expected_company)
        if result:
            parsed.append(result)
    logger.info(
        "Parser: %d raw candidates → %d parsed recruiters",
        len(raw_list), len(parsed),
    )
    return parsed
