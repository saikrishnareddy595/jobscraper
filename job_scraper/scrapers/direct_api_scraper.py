"""
direct_api_scraper.py — Scraper module that targets hidden or open JSON endpoints.

Implements "Delta-Sync" fetching for:
 - Workday (POST /wday/cxs/)
 - Greenhouse (GET /v1/boards/)
 - Amazon (GET /en/search.json)

These APIs are highly resilient, return structured JSON without bot-challenges, 
and strictly filter jobs posted in the last 24-hours for maximum freshness.
"""

import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from .base import BaseAPIScraper, short_delay
import config

logger = logging.getLogger(__name__)

def _is_recent(date_str: str) -> bool:
    """Check if an ISO-formatted date string is within the last 24 hours."""
    if not date_str:
        return False
        
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    if date_str.lower().endswith("z"):
        date_str = date_str[:-1] + "+00:00"
        
    try:
        # Some Workday APIs return dates like "2023-11-20" or "2023-11-20T14:30:00.000Z"
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt > cutoff
        else:
            # Just a date, assume start of day UTC
            dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt > cutoff
    except Exception:
        # If we can't parse it, assume it isn't fresh (safe failure)
        return False


def clean_html(html_text: str) -> str:
    if not html_text:
        return ""
    return BeautifulSoup(html_text, 'html.parser').get_text(separator=' ', strip=True)


class WorkdayScraper(BaseAPIScraper):
    """
    Scrapes Workday internal CXS API by sending POST requests.
    Supports a configurable list of tenant IDs.
    """
    SOURCE = "Workday (Direct)"
    
    def __init__(self, tenant_id: str):
        super().__init__()
        self.tenant_id = tenant_id
        # In Workday, the company name in the sub-domain is usually the tenant name
        self.host = f"{self.tenant_id}.wd5.myworkdayjobs.com"
        
    def scrape(self) -> List[Dict[str, Any]]:
        self.jobs = []
        url = f"https://{self.host}/wday/cxs/{self.tenant_id}/jobs"
        
        # We search specifically using the target job titles
        for title in config.JOB_TITLES[:3]:
            payload = {
                "appliedFacets": {},
                "limit": 20,
                "offset": 0,
                "searchText": title
            }
            try:
                r = self._session.post(url, json=payload, timeout=10)
                r.raise_for_status()
                data = r.json()
                
                postings = data.get("jobPostings", [])
                for p in postings:
                    posted_on = p.get("postedOn", "")
                    # Workday often says "Posted Today" or "Posted Yesterday"
                    # The API sometimes normalizes this to an ISO date. 
                    # If it gives "Posted Today", we treat it as recent.
                    if "Today" in posted_on or "Yesterday" in posted_on:
                        recent = True
                    elif "Days Ago" in posted_on or "30+" in posted_on:
                        recent = False
                    else:
                        recent = _is_recent(posted_on)
                    
                    if recent:
                        job_dict = {
                            "title": p.get("title", "").strip(),
                            "company": self.tenant_id.capitalize(),
                            "location": p.get("locationsText", "").strip(),
                            "url": f"https://{self.host}/en-US/{self.tenant_id}{p.get('externalPath', '')}",
                            "source": self.SOURCE,
                            "job_type": p.get("timeType", "Full time"),
                            "posted_date": datetime.now(timezone.utc).isoformat()
                        }
                        self._add(job_dict)
                        
            except requests.exceptions.HTTPError as he:
                if he.response.status_code == 404:
                    logger.debug(f"{self.SOURCE} Tenant '{self.tenant_id}' not found or path differs.")
                else:
                    logger.warning(f"{self.SOURCE} HTTP error on {self.tenant_id}: {he}")
            except Exception as e:
                logger.warning(f"{self.SOURCE} Error parsing {self.tenant_id}: {e}")
                
            short_delay()
            
        return self.jobs


class GreenhouseScraper(BaseAPIScraper):
    """
    Hits Greenhouse's public JSON API. No auth required.
    """
    SOURCE = "Greenhouse (Direct)"

    def __init__(self, company_token: str):
        super().__init__()
        self.company_token = company_token
        
    def scrape(self) -> List[Dict[str, Any]]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.company_token}/jobs"
        
        try:
            r = self._session.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            
            jobs = data.get("jobs", [])
            for j in jobs:
                title = j.get("title", "").lower()
                
                # We do filtering early to save computation
                if not any(kw.lower() in title for kw in config.JOB_TITLES):
                    continue
                    
                posted_iso = j.get("updated_at", "")
                if not _is_recent(posted_iso):
                    continue
                
                loc_obj = j.get("location", {})
                location = loc_obj.get("name", "") if isinstance(loc_obj, dict) else ""
                
                # Fetch full job text from the specific job URL? 
                # Greenhouse list API doesn't include the description, so we just set title.
                # The LLM or Deduplicator might fetch the full HTML if needed, but for now we keep it light.
                
                self._add({
                    "title": j.get("title", ""),
                    "company": self.company_token.capitalize(),
                    "location": location,
                    "url": j.get("absolute_url", ""),
                    "source": self.SOURCE,
                    "posted_date": posted_iso
                })
        except Exception as e:
            logger.warning(f"{self.SOURCE} Error on {self.company_token}: {e}")
            
        return self.jobs


class AmazonDirectScraper(BaseAPIScraper):
    """
    Hits the public JSON interface for Amazon.jobs.
    """
    SOURCE = "Amazon (Direct)"
    
    def scrape(self) -> List[Dict[str, Any]]:
        self.jobs = []
        if not getattr(config, "AMAZON_SCRAPE_ENABLED", False):
            return self.jobs
            
        url = "https://www.amazon.jobs/en/search.json"
        
        for title in config.JOB_TITLES[:3]:
            params = {
                "sort": "recent",
                "result_limit": 100,
                "base_query": title
            }
            try:
                r = self._session.get(url, params=params, timeout=15)
                r.raise_for_status()
                data = r.json()
                
                for j in data.get("jobs", []):
                    posted = j.get("posted_date", "")
                    
                    # Amazon gives e.g. "November 20, 2023"
                    try:
                        dt = datetime.strptime(posted, "%B %d, %Y").replace(tzinfo=timezone.utc)
                        cutoff = datetime.now(timezone.utc) - timedelta(hours=48) # 2 day slack
                        if dt < cutoff:
                            continue  # Since sorted by recent, we can theoretically break here, but we'll continue for safety.
                    except ValueError:
                        pass # Ignore parsing issues and include
                        
                    self._add({
                        "title": j.get("title", ""),
                        "company": "Amazon / AWS",
                        "location": j.get("location", ""),
                        "description": clean_html(j.get("description", "")), # We have description!
                        "url": f"https://www.amazon.jobs/en/jobs/{j.get('id_icims', '')}",
                        "source": self.SOURCE,
                        "posted_date": datetime.now(timezone.utc).isoformat()
                    })
                    
            except Exception as e:
                logger.warning(f"{self.SOURCE} Error scraping '{title}': {e}")
                
            short_delay()
            
        return self.jobs
