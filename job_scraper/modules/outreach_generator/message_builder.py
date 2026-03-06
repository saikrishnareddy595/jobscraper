"""
message_builder.py — Constructs tailored outreach texts using templates + candidate data.
"""

import logging
from typing import Dict, Any, Optional
import config
from .template_selector import get_template, get_keys_required
from .subject_builder import generate_subject

logger = logging.getLogger(__name__)

def build_message(
    job: Dict[str, Any],
    recruiter: Dict[str, Any],
    candidate: Dict[str, Any],
    fit_analysis: Dict[str, Any],
    message_type: str = "linkedin_dm_standard",
    tone: str = "professional, confident"
) -> Dict[str, str]:
    """Generates the subject and body of an outreach message."""
    
    # 1. Base details extraction
    first_name = recruiter.get("name", "there").split()[0]
    if first_name.lower() in ["talent", "recruiting", "human", "hr"]:
        first_name = "there" # basic guard
        
    company = job.get("company", "").strip() or recruiter.get("company", "").strip()
    job_title = job.get("title", "").strip()
    
    skills = ", ".join(fit_analysis.get("matched_skills", []))
    if not skills:
        skills = "Data Engineering, Python, and SQL" # fallback
        
    yoe = candidate.get("years_experience", 0)
    if yoe <= 0:
        yoe = 3 # fallback guessing
        
    reasoning = "The role's tech stack matches my expertise closely"
    if fit_analysis.get("top_reasons"):
        reasoning = fit_analysis["top_reasons"][0]

    # Combine data dictionary
    data = {
        "first_name": first_name,
        "job_title": job_title,
        "company": company,
        "skills": skills,
        "yoe": str(yoe),
        "reasoning": reasoning,
        "candidate_name": candidate.get("name", "Sai Krishna Reddy")
    }

    # 2. Fill Template directly for baseline
    raw_template = get_template(message_type)
    # Safely format ignoring missing keys
    try:
        body = raw_template.format(**data)
    except KeyError as e:
        logger.warning(f"Message builder template formatting missed key: {e}")
        # manual replacement fallback
        body = raw_template
        for k, v in data.items():
            body = body.replace("{" + k + "}", v)
            
    # 3. Apply LLM refinement if available
    if config.LLM_ENABLED:
        body = _llm_refine(body, tone, message_type)
        
    # 4. Generate subject
    subject = generate_subject(job, candidate, message_type)
    
    return {
        "subject": subject,
        "body": body.strip()
    }

def _llm_refine(draft: str, tone: str, message_type: str) -> str:
    """Passes draft to LLM to sound more natural + polite."""
    from .tone_rules import get_tone_instruction
    tone_instr = get_tone_instruction(tone)
    
    prompt = f"""Rewrite natural outreach message for a job application.
    
DRAFT:
{draft}

MESSAGE TYPE: {message_type}
TONE: {tone_instr}

RULES:
- Ensure the message is smooth, human-sounding, and polite.
- Fix grammar or weird spacing.
- Keep the length constraints (linkedin_dm_short should be < 300 chars if possible).
- Print ONLY the rewritten message text, no JSON, no conversational pleasantries.
"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.NVIDIA_API_KEY, base_url=config.NVIDIA_BASE_URL)
        resp = client.chat.completions.create(
            model=config.NVIDIA_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning(f"LLM outreach refinement failed, keeping draft. Err: {exc}")
        return draft
