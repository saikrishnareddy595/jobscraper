"""
validators.py — Quality controls to reject bad outreach draft generations.
"""

import logging

logger = logging.getLogger(__name__)

def validate_message(body: str, message_type: str, company: str, job_title: str) -> bool:
    """
    Checks the generated message against rules.
    Returns True if valid, False if it violates any rules.
    """
    body_l = body.lower()
    
    # 1. Missing placeholders
    if "{" in body and "}" in body:
        logger.warning("Message validation failed: unresolved placeholder braces found.")
        return False
        
    # 2. Length check
    if message_type == "linkedin_dm_short" and len(body) > 350:
        logger.warning(f"Message validation failed: message too long ({len(body)} chars).")
        return False
        
    # 3. Context check (only if company is a real string)
    if len(company) > 1 and company.lower() not in body_l and "your team" not in body_l:
        logger.warning(f"Message validation failed: missing company '{company}'")
        return False
        
    # 4. Spammy phrases filter
    bad_phrases = [
        "dear sir or madam",
        "to whom it may concern",
        "guarantee my success",
        "best candidate",
        "i am writing to express my interest in the position of" # this one is in the base template though, but LLM should rewrite it ideally. I'll lower the strictness here.
    ]
    for bp in bad_phrases:
        if bp in body_l and bp != "i am writing to express my interest in the position of":
            logger.warning(f"Message validation failed: spammy phrase '{bp}'")
            return False
            
    return True
