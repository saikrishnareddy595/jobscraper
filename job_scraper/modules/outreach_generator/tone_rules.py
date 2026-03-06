"""
tone_rules.py — Defines constraints and instructions for tone variation during generation.
"""

TONE_PROMPTS = {
    "professional": "Keep it strictly professional and fact-based. Avoid informal slang.",
    "confident": "Use strong, confident language. Highlight direct applicability and readiness.",
    "warm": "Use a warm, conversational, and energetic tone. Show enthusiasm for the role and company.",
    "concise": "Make it extremely brief and high-impact. Cut out any unnecessary transitional phrases."
}

def get_tone_instruction(tone: str) -> str:
    parts = []
    for t in tone.split(","):
        t = t.strip().lower()
        if t in TONE_PROMPTS:
            parts.append(TONE_PROMPTS[t])
    return " ".join(parts) if parts else TONE_PROMPTS["professional"]
