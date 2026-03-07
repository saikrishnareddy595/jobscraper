"""
resume.py — Resume parser and cover letter generator.

Features:
  1. Parse a resume PDF or plain text → structured JSON (name, skills, experience)
  2. Generate a bespoke cover letter for a given job using NVIDIA NIM LLM
  3. Skill gap detection: compare resume skills vs. job requirements

Setup:
  - Set RESUME_PATH in config.py to your resume file path (PDF or .txt)
  - pip install pdfminer.six  (already in requirements if you add it)
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import config

logger = logging.getLogger(__name__)


# ── Resume parsing ─────────────────────────────────────────────────────────────

def parse_resume(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse a resume file (PDF or .txt) and return a structured dict.
    Falls back to an empty profile if path not set or file not found.
    """
    path = path or getattr(config, "RESUME_PATH", "")
    if not path:
        logger.info("Resume: RESUME_PATH not set — using empty profile")
        return _empty_profile()

    # Resolve to absolute path and validate it stays within expected boundaries
    abs_path = os.path.abspath(path)
    allowed_dir = os.path.abspath(os.path.dirname(__file__) + "/../..")
    if not abs_path.startswith(allowed_dir) and not os.path.isabs(path):
        logger.warning("Resume: path '%s' is outside allowed directory — rejected", path)
        return _empty_profile()

    if not os.path.exists(abs_path):
        logger.info("Resume: no file at '%s' — using empty profile", abs_path)
        return _empty_profile()

    path = abs_path

    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            text = _read_pdf(path)
        else:
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        logger.info("Resume: read %d chars from %s", len(text), path)
        return _llm_parse(text) or _regex_parse(text)
    except Exception as exc:
        logger.error("Resume parse error: %s", exc)
        return _empty_profile()


def _read_pdf(path: str) -> str:
    """Extract text from PDF using pdfminer.six."""
    try:
        from pdfminer.high_level import extract_text
        return extract_text(path) or ""
    except ImportError:
        logger.warning("pdfminer.six not installed — run: pip install pdfminer.six")
        return ""


def _llm_parse(text: str) -> Optional[Dict[str, Any]]:
    """Use NVIDIA NIM LLM to extract structured resume data."""
    if not config.LLM_ENABLED:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.NVIDIA_API_KEY, base_url=config.NVIDIA_BASE_URL)
        prompt = f"""Extract structured information from this resume.

Respond ONLY with valid JSON (no markdown):
{{
  "name": "<full name>",
  "email": "<email>",
  "phone": "<phone>",
  "title": "<current or target job title>",
  "years_experience": <integer>,
  "skills": ["skill1", "skill2", ...],
  "companies": ["company1", ...],
  "education": "<highest degree + field>",
  "summary": "<2-sentence professional summary>"
}}

RESUME:
{text[:3000]}"""
        resp = client.chat.completions.create(
            model=config.NVIDIA_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        return json.loads(raw)
    except Exception as exc:
        logger.debug("LLM resume parse failed: %s", exc)
        return None


def _regex_parse(text: str) -> Dict[str, Any]:
    """Simple regex-based fallback resume parser."""
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    phones = re.findall(r"[\+]?[\d\s\-\(\)]{10,15}", text)

    # Extract skills by matching known tech keywords
    known_skills = [
        "Python", "SQL", "Spark", "Kafka", "Airflow", "dbt", "Snowflake",
        "Databricks", "BigQuery", "Redshift", "AWS", "GCP", "Azure",
        "Docker", "Kubernetes", "TensorFlow", "PyTorch", "scikit-learn",
        "MLflow", "Kubeflow", "Flink", "Beam", "Hive", "Hadoop",
        "Machine Learning", "Deep Learning", "LLM", "Transformers",
    ]
    found_skills = [s for s in known_skills if s.lower() in text.lower()]

    return {
        "name": "",
        "email": emails[0] if emails else "",
        "phone": phones[0].strip() if phones else "",
        "title": "Data Engineer",
        "years_experience": 0,
        "skills": found_skills,
        "companies": [],
        "education": "",
        "summary": "",
    }


def _empty_profile() -> Dict[str, Any]:
    return {
        "name": "", "email": "", "phone": "",
        "title": "Data Engineer", "years_experience": 0,
        "skills": [], "companies": [], "education": "", "summary": "",
    }


# ── Cover letter generation ────────────────────────────────────────────────────

def generate_cover_letter(job: Dict[str, Any], resume: Dict[str, Any]) -> str:
    """
    Generate a tailored cover letter for a job using the parsed resume profile.
    Returns plain text cover letter, or empty string if LLM not available.
    """
    if not config.LLM_ENABLED:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.NVIDIA_API_KEY, base_url=config.NVIDIA_BASE_URL)

        name    = resume.get("name", "the applicant")
        skills  = ", ".join(resume.get("skills", [])[:12])
        summary = resume.get("summary", "")
        exp     = resume.get("years_experience", 0)

        prompt = f"""Write a concise, professional cover letter (3 short paragraphs, no fluff).

APPLICANT:
Name: {name}
Title: {resume.get('title', 'Data Engineer')}
Experience: {exp} years
Top Skills: {skills}
Summary: {summary}

JOB:
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Description excerpt: {(job.get('description') or '')[:600]}

Rules:
- Start with "Dear Hiring Manager,"
- Mention the company name and role title
- Link 2-3 of the applicant's skills to the job requirements
- End with a call to action
- Keep it under 200 words
- Return ONLY the letter text, no subject line, no JSON"""

        resp = client.chat.completions.create(
            model=config.NVIDIA_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=400,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Cover letter generation failed: %s", exc)
        return ""


# ── Skill gap analysis ─────────────────────────────────────────────────────────

def skill_gap_analysis(jobs: List[Dict[str, Any]], resume: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare resume skills against job requirements across all scraped jobs.
    Returns a dict with:
      - top_demanded:   [(skill, count)] — most required skills across all JDs
      - you_have:       [skill]          — skills matching resume
      - you_are_missing:[skill]          — high-demand skills not on resume
    """
    from collections import Counter

    resume_skills_lower = {s.lower() for s in resume.get("skills", [])}

    # Count skill mentions across all job descriptions
    skill_counts: Counter = Counter()
    known_skills = [
        "python", "sql", "spark", "kafka", "airflow", "dbt", "snowflake",
        "databricks", "bigquery", "redshift", "aws", "gcp", "azure",
        "docker", "kubernetes", "tensorflow", "pytorch", "scikit-learn",
        "mlflow", "flink", "hadoop", "llm", "transformers", "ray",
        "scala", "java", "go", "rust", "git", "terraform", "fastapi",
    ]

    for job in jobs:
        desc = ((job.get("description") or "") + " " + (job.get("title") or "")).lower()
        for skill in known_skills:
            if skill in desc:
                skill_counts[skill] += 1

    top_demanded = skill_counts.most_common(20)
    you_have     = [s for s, _ in top_demanded if s.lower() in resume_skills_lower]
    you_missing  = [s for s, _ in top_demanded if s.lower() not in resume_skills_lower]

    logger.info(
        "Skill gap: top demanded=%d | you have=%d | gaps=%d",
        len(top_demanded), len(you_have), len(you_missing),
    )
    return {
        "top_demanded": top_demanded,
        "you_have": you_have,
        "you_are_missing": you_missing[:10],
    }
