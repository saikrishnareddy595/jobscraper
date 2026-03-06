"""
subject_builder.py — Constructs appropriate outreach subject lines.
"""

from typing import Dict, Any

def generate_subject(job: Dict[str, Any], candidate: Dict[str, Any], message_type: str) -> str:
    """Builds a subject line based on role and message type."""
    if "email" not in message_type and "referral" not in message_type:
        return "" # Linkedin doesn't use subjects normally unless it's inmail, but even so keep empty for short DMs.
        
    job_title = job.get("title", "Role").strip()
    company = job.get("company", "Your Team").strip()
    
    if message_type == "recruiter_email":
        return f"Interest in {job_title} role at {company}"
    elif message_type == "follow_up_message":
        return f"Following up: {job_title} at {company}"
    elif message_type == "referral_request_message":
        return f"Connecting regarding {company} & {job_title} role"
        
    return f"Connecting about {job_title}"
