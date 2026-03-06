"""
fit_analyzer.py — Computes relevance signals between a job, recruiter, and candidate.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Basic skill list to extract from JD if not already present
_KNOWN_SKILLS = [
    "python", "sql", "spark", "kafka", "airflow", "dbt", "snowflake",
    "databricks", "bigquery", "redshift", "aws", "gcp", "azure",
    "docker", "kubernetes", "llm", "scala", "java", "go", "terraform",
    "pyspark", "hadoop"
]

def analyze_job_fit(job: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes a fit analysis mapping candidate skills to job requirements.
    """
    candidate_skills = [s.lower() for s in candidate.get("skills", [])]
    jd_text = ((job.get("description") or "") + " " + (job.get("title") or "")).lower()
    
    job_skills_required = []
    reqs = job.get("requirements")
    if isinstance(reqs, list):
        job_skills_required = [r.lower() for r in reqs]
    else:
        for skill in _KNOWN_SKILLS:
            if skill in jd_text:
                job_skills_required.append(skill)
                
    matched_skills = [s for s in job_skills_required if s in candidate_skills]
    missing_skills = [s for s in job_skills_required if s not in candidate_skills]
    
    if not matched_skills and candidate_skills:
        top_db = ["python", "sql", "spark", "snowflake", "airflow", "aws"]
        matched_skills = [s for s in candidate_skills if s in top_db][:3]
    
    loc = job.get("location", "").lower()
    pref_locs = [l.lower() for l in candidate.get("preferred_locations", ["remote", "hybrid"])]
    
    location_fit = "Moderate"
    if "remote" in loc or "hybrid" in loc or any(p in loc for p in pref_locs if p):
        location_fit = "Strong"
    
    title = job.get("title", "").lower()
    cand_yoe = candidate.get("years_experience", 0)
    
    if any(x in title for x in ["senior", "lead", "staff", "principal"]):
        seniority_fit = "Strong" if cand_yoe >= 5 else "Stretch"
    else:
        seniority_fit = "Strong" if cand_yoe >= 2 else "Entry"
        
    base_score = 50
    if len(job_skills_required) > 0:
        match_ratio = len(matched_skills) / len(job_skills_required)
        base_score += int(match_ratio * 30)
    else:
        base_score += 20
        
    if location_fit == "Strong": base_score += 10
    if seniority_fit == "Strong": base_score += 10
        
    fit_score = min(100, max(0, base_score))
    
    top_reasons = []
    if matched_skills:
        ms_display = [s.title() if s not in ["sql", "aws", "gcp", "dbt"] else s.upper() for s in matched_skills[:3]]
        top_reasons.append(f"Strong match on {', '.join(ms_display)}")
    if location_fit == "Strong":
        top_reasons.append("Location and work arrangement aligns")
    
    return {
        "fit_score": fit_score,
        "matched_skills": [s.title() if s not in ["sql", "aws", "gcp", "dbt"] else s.upper() for s in matched_skills],
        "missing_skills": missing_skills,
        "location_fit": location_fit,
        "seniority_fit": seniority_fit,
        "top_reasons": top_reasons
    }
