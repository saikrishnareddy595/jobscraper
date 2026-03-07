"""
linkedin_search.py — LinkedIn recruiter search via LinkedIn's Guest API.

Strategy:
  1. Use LinkedIn's `jobs-guest/jobs/api/seeMoreJobPostings/search` to find
     the target job postings for the company.
  2. Extract the Job IDs.
  3. Fetch the full Job Details using `jobs-guest/jobs/api/jobPosting/<JOB_ID>`.
  4. Parse the HTML for the "Meet the Hiring Team" or recruiter section.
"""

import logging
import random
import time
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)
_ua = UserAgent()

_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
_DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id}"

def _random_delay(base: float = 1.0, jitter: float = 1.0) -> None:
    time.sleep(base + random.uniform(0, jitter))

def search_recruiters(
    company: str,
    job_title: str,
    location: str = "",
    *,
    session: Optional[requests.Session] = None,
) -> List[Dict[str, Any]]:
    """
    Public interface for the search layer.
    Replaces DDG logic with direct LinkedIn Guest API calls.
    Returns: [{'name', 'linkedin_url', 'headline', 'snippet', 'raw_query'}, ...]
    """
    if not session:
        session = requests.Session()

    candidates: List[Dict[str, Any]] = []
    seen_urls: set = set()

    # 1. Search for the job posting on LinkedIn Guest API
    # Often, the hiring manager/recruiter attaches to their own posting.
    query = f"{job_title} {company}"
    
    headers = {
        "User-Agent": _ua.random,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    params = {
        "keywords": query,
        "location": location or "United States",
        "f_TPR": "r2592000", # Last 30 days to ensure we find the company's job
        "start": 0
    }

    try:
        resp = session.get(_SEARCH_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        job_cards = soup.find_all('li')
        job_ids = []
        
        for job in job_cards:
            urn_div = job.find('div', {'data-entity-urn': True})
            if urn_div:
                job_id = urn_div['data-entity-urn'].split(':')[-1]
                job_ids.append(job_id)

    except Exception as exc:
        logger.warning(f"Guest API search failed for '{query}': {exc}")
        return candidates

    # 2. Extract recruiter from the Job Details Endpoint
    for job_id in job_ids[:3]:  # Only check top 3 to avoid spamming
        _random_delay()
        try:
            detail_resp = session.get(_DETAIL_URL.format(id=job_id), headers=headers, timeout=10)
            if detail_resp.status_code != 200:
                continue
                
            det_soup = BeautifulSoup(detail_resp.text, 'html.parser')
            
            # Check for "Meet the hiring team" block
            # Class names change often: 'message-the-recruiter', 'base-message-card'
            recruiter_cards = det_soup.select(".message-the-recruiter, .base-message-card, .job-details-jobs-unified-top-card__hiring-team")
            
            for card in recruiter_cards:
                # Attempt to extract recruiter anchor
                r_link = card.find('a', href=True)
                if not r_link or '/in/' not in r_link.get('href', ''):
                    continue
                    
                url = r_link['href']
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # Cleanup URL
                if "?" in url:
                    url = url.split("?")[0]
                if not url.startswith("http"):
                    continue
                    
                # Extract text
                name_el = card.find(['h3', 'strong', 'span'], class_=lambda x: x and ('name' in x or 'title' in x))
                title_el = card.find(['h4', 'span', 'p'], class_=lambda x: x and ('headline' in x or 'subtitle' in x))
                
                name = name_el.get_text(strip=True) if name_el else url.split("/in/")[-1].replace('-', ' ').title()
                headline = title_el.get_text(strip=True) if title_el else "Recruiter"
                
                # The "snippet" is the full job description to provide context for the outreach LLM
                snippet_el = det_soup.select_one(".show-more-less-html__markup")
                snippet = snippet_el.get_text(separator=" ", strip=True)[:500] if snippet_el else ""
                
                candidates.append({
                    "name": name,
                    "linkedin_url": url,
                    "headline": headline,
                    "snippet": snippet,
                    "raw_query": query
                })
                
        except Exception as exc:
            logger.debug(f"Guest API detail parse err for {job_id}: {exc}")

    logger.info(
        "LinkedIn Guest Search for '%s' @ '%s': %d candidates found via Job Details",
        job_title, company, len(candidates),
    )
    return candidates
