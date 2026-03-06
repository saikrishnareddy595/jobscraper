"""
linkedin_search.py — LinkedIn recruiter search via DuckDuckGo HTML queries.

Strategy:
  • Build site:linkedin.com/in/ queries for recruiter/TA roles at the company.
  • Execute via DuckDuckGo (no API key, no rate-limit surprises from Google).
  • Parse result snippets to extract candidate profile URLs + headline text.
  • Retry with exponential back-off on blocks / failures.

Why DuckDuckGo?
  LinkedIn blocks direct scraping. Using a public search engine as the
  intermediary is the only broadly viable approach without credentials.
  We scrape nothing directly from LinkedIn; we only read the search-engine
  snippet that linkedin.com already published publicly.
"""

import logging
import random
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

_ua = UserAgent()

# ── Recruiter title patterns that we search for ────────────────────────────────
_RECRUITER_QUERY_TERMS = [
    "technical recruiter",
    "talent acquisition",
    "senior recruiter",
    "recruiting manager",
    "data engineering recruiter",
]

# DuckDuckGo HTML endpoint (undocumented but stable)
_DDG_URL = "https://html.duckduckgo.com/html/"

# Maximum results to parse per query — keeps runtime bounded
_MAX_RESULTS_PER_QUERY = 5

# Retry settings
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.5   # seconds


def _random_delay(base: float = 2.0, jitter: float = 2.0) -> None:
    time.sleep(base + random.uniform(0, jitter))


def _ddg_search(query: str, session: requests.Session) -> List[Dict[str, str]]:
    """
    Execute one DuckDuckGo HTML query and return a list of
    {'url': ..., 'title': ..., 'snippet': ...} dicts.
    """
    results: List[Dict[str, str]] = []

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = session.post(
                _DDG_URL,
                data={"q": query, "b": "", "kl": "us-en"},
                headers={
                    "User-Agent": _ua.random,
                    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://duckduckgo.com/",
                    "Origin": "https://duckduckgo.com",
                },
                timeout=20,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            for result in soup.select("div.result__body")[:_MAX_RESULTS_PER_QUERY]:
                a_tag    = result.select_one("a.result__a")
                snippet  = result.select_one("a.result__snippet")
                if not a_tag:
                    continue
                url  = a_tag.get("href", "")
                title_text   = a_tag.get_text(separator=" ", strip=True)
                snippet_text = snippet.get_text(separator=" ", strip=True) if snippet else ""
                results.append({
                    "url":     url,
                    "title":   title_text,
                    "snippet": snippet_text,
                })

            logger.debug(
                "DDG query '%s': %d results (attempt %d)",
                query[:60], len(results), attempt,
            )
            return results

        except requests.HTTPError as exc:
            wait = _BACKOFF_BASE ** attempt
            logger.warning(
                "DDG HTTP %s for query '%s' (attempt %d/%d) — retrying in %.1fs",
                exc.response.status_code if exc.response else "?",
                query[:60], attempt, _MAX_RETRIES, wait,
            )
            time.sleep(wait)

        except Exception as exc:
            wait = _BACKOFF_BASE ** attempt
            logger.warning(
                "DDG search error '%s' (attempt %d/%d): %s — retrying in %.1fs",
                query[:60], attempt, _MAX_RETRIES, exc, wait,
            )
            time.sleep(wait)

    logger.error("DDG search exhausted retries for query: %s", query[:60])
    return []


def _is_linkedin_profile(url: str) -> bool:
    """Return True if the URL looks like a real LinkedIn /in/ profile page."""
    return bool(re.search(r"linkedin\.com/in/[\w\-]+", url))


def _build_queries(company: str, job_title: str) -> List[str]:
    """
    Build search queries that are likely to surface relevant recruiter profiles.
    We combine company + recruiter persona + role context.
    """
    company_q = f'"{company}"'
    role_hint  = "data engineering" if "engineer" in job_title.lower() else job_title.split()[0]

    queries: List[str] = []
    for term in _RECRUITER_QUERY_TERMS:
        queries.append(
            f'site:linkedin.com/in/ "{term}" {company_q}'
        )
    # Add a role-specific query
    queries.append(
        f'site:linkedin.com/in/ "recruiter" {company_q} "{role_hint}"'
    )
    return queries


def search_recruiters(
    company: str,
    job_title: str,
    location: str = "",
    *,
    session: Optional[requests.Session] = None,
) -> List[Dict[str, Any]]:
    """
    Public interface for the search layer.

    Returns a list of raw recruiter candidates:
        [{'name': str, 'linkedin_url': str, 'headline': str, 'snippet': str}, ...]

    Each candidate is extracted from the DuckDuckGo snippet — no LinkedIn
    page is directly fetched, so blocking risk is minimised.
    """
    if not session:
        session = requests.Session()

    queries   = _build_queries(company, job_title)
    seen_urls: set          = set()
    candidates: List[Dict]  = []

    for query in queries:
        raw_results = _ddg_search(query, session)
        for r in raw_results:
            url = r["url"]
            if not _is_linkedin_profile(url):
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Try to extract first/last name from the URL slug
            # e.g. linkedin.com/in/sarah-johnson-recruiter-123 → "Sarah Johnson"
            slug_match = re.search(r"linkedin\.com/in/([\w\-]+)", url)
            slug       = slug_match.group(1) if slug_match else ""
            name_parts = [p.capitalize() for p in slug.split("-") if p.isalpha()]
            # Heuristic: keep first two alpha parts as name, drop common suffixes
            _SUFFIXES = {"recruiter", "talent", "hiring", "hr", "people"}
            name_parts = [p for p in name_parts if p.lower() not in _SUFFIXES]
            guessed_name = " ".join(name_parts[:2]) if name_parts else ""

            candidates.append({
                "name":         guessed_name or r["title"].split("|")[0].strip(),
                "linkedin_url": url,
                "headline":     r["title"],
                "snippet":      r["snippet"],
                "raw_query":    query,
            })

        if candidates:
            # Found results from this query — add polite delay before next
            _random_delay(base=1.5, jitter=1.5)

    logger.info(
        "LinkedIn search for '%s' @ '%s': %d candidates found",
        job_title, company, len(candidates),
    )
    return candidates
