"""
template_selector.py — Base outreach templates and retrieval logic.
"""

from typing import Dict

# Using new style formatting with slots
TEMPLATES = {
    "linkedin_dm_short": [
        "Hi {first_name}, I saw the {job_title} opening at {company}. My background in {skills} closely aligns with the role, and I'd love to connect and learn if you're still actively interviewing. Thanks, {candidate_name}."
    ],
    "linkedin_dm_standard": [
        "Hi {first_name},\n\nI came across the {job_title} opening at {company} and it looks closely aligned with my background in {skills}.\n\nI have about {yoe} years of experience building scalable data workflows and wanted to reach out to see if the team is still actively hiring. {reasoning}. Happy to share my background if helpful.\n\nBest,\n{candidate_name}"
    ],
    "recruiter_email": [
        "Hi {first_name},\n\nI am writing to express my interest in the {job_title} position at {company}. Based on the requirements, my experience with {skills} makes me a strong fit for your team.\n\nI have {yoe} years of hands-on experience and {reasoning}. I have attached my resume for your convenience.\n\nI would welcome the opportunity to discuss how my background aligns with your needs.\n\nBest regards,\n{candidate_name}"
    ],
    "follow_up_message": [
        "Hi {first_name}, just bringing this to the top of your inbox. I remain very interested in the {job_title} role at {company} and would love to connect briefly if you have time this week.\n\nBest,\n{candidate_name}"
    ],
    "referral_request_message": [
        "Hi {first_name}, I'm reaching out because I'm very interested in the {job_title} role at {company}. Given your experience there, I'd love to ask a quick question about the team culture if you're open to it. My background is in {skills}. Thanks!\n\nBest,\n{candidate_name}"
    ]
}

def get_template(message_type: str) -> str:
    """Return the primary template for a given message type."""
    options = TEMPLATES.get(message_type)
    if not options:
        return TEMPLATES["linkedin_dm_standard"][0]
    return options[0]

def get_keys_required(message_type: str) -> list:
    import re
    template = get_template(message_type)
    return re.findall(r"\{(\w+)\}", template)
