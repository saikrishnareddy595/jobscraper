"""
Central configuration for the Job Scraping System.
All user-facing settings live here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Role Categories ────────────────────────────────────────────────────────────
ROLE_CATEGORIES = {
    "data_engineer": [
        "Data Engineer",
        "Data Engineering",
        "ETL Engineer",
        "Pipeline Engineer",
        "Analytics Engineer",
        "Data Platform Engineer",
        "Data Infrastructure Engineer",
        "Big Data Engineer",
    ],
    "ai_engineer": [
        "AI Engineer",
        "Artificial Intelligence Engineer",
        "LLM Engineer",
        "Generative AI Engineer",
        "Prompt Engineer",
        "AI/ML Engineer",
    ],
    "ml_engineer": [
        "Machine Learning Engineer",
        "ML Engineer",
        "MLOps Engineer",
        "ML Platform Engineer",
        "Applied ML Engineer",
        "Deep Learning Engineer",
    ],
    "nlp_engineer": [
        "NLP Engineer",
        "Natural Language Processing Engineer",
        "Conversational AI Engineer",
        "Speech Engineer",
    ],
    "cv_engineer": [
        "Computer Vision Engineer",
        "CV Engineer",
        "Vision AI Engineer",
    ],
    "data_scientist": [
        "Data Scientist",
        "Applied Scientist",
        "Research Scientist",
        "ML Scientist",
    ],
}

# Flat list of all job titles (used by Dice, Jooble, etc.)
JOB_TITLES: list = []
for titles in ROLE_CATEGORIES.values():
    JOB_TITLES.extend(titles)

# Reduced list for JobSpy (LinkedIn) — each title takes ~1 min, run in parallel.
# Keep one representative per role cluster to avoid duplicate results and stay
# well within the 60-min workflow timeout.
JOBSPY_TITLES: list = [
    # Data Engineering
    "Data Engineer",
    "ETL Engineer",
    "Analytics Engineer",
    # AI / Generative AI
    "AI Engineer",
    "LLM Engineer",
    "Generative AI Engineer",
    # ML / MLOps
    "Machine Learning Engineer",
    "MLOps Engineer",
    # NLP / CV
    "NLP Engineer",
    "Computer Vision Engineer",
    # Data Science
    "Data Scientist",
]

# ── Search Parameters ──────────────────────────────────────────────────────────
LOCATIONS = ["United States", "Remote USA", "Remote"]

MIN_SALARY      = 80_000   # USD / year
MAX_JOB_AGE_HOURS = 168
MAX_APPLICANTS  = 200      # filter out saturated postings

EASY_APPLY_ONLY = False    # include all application types

# Job types to include
JOB_TYPES = ["full_time", "contract", "contract_to_hire", "part_time"]

WORK_TYPES = ["on-site", "remote", "hybrid"]

# ── Keywords ───────────────────────────────────────────────────────────────────
INCLUDE_KEYWORDS = [
    "data pipeline", "ETL", "Spark", "Kafka", "Airflow", "dbt", "SQL",
    "Python", "cloud", "AWS", "GCP", "Azure", "data warehouse", "Snowflake",
    "Databricks", "BigQuery", "Redshift", "Flink", "Beam", "Hive",
    "TensorFlow", "PyTorch", "scikit-learn", "LLM", "GPT", "transformer",
    "MLflow", "Kubeflow", "Ray", "Kubernetes", "Docker",
    "machine learning", "deep learning", "neural network",
]

EXCLUDE_KEYWORDS = [
    "unpaid", "10+ years", "15+ years", "principal engineer",
    "staff engineer", "VP of", "Vice President",
]

# ── Dream Companies ────────────────────────────────────────────────────────────
DREAM_COMPANIES = [
    "Google", "DeepMind", "Amazon", "AWS", "Microsoft", "Azure",
    "Meta", "Facebook", "Apple", "OpenAI", "Anthropic", "NVIDIA",
    "Databricks", "Snowflake", "Palantir", "Scale AI", "Cohere",
    "Hugging Face", "Netflix", "Uber", "Airbnb", "Stripe",
]

# ── Scoring ────────────────────────────────────────────────────────────────────
ALERT_SCORE_THRESHOLD = 50   # jobs at or above this score go to email/sheets

# ── Gmail / Alerts ─────────────────────────────────────────────────────────────
GMAIL_ADDRESS       = os.getenv("GMAIL_ADDRESS", "reddamgufus21188@gmail.com")
GMAIL_APP_PASSWORD  = os.getenv("GMAIL_APP_PASSWORD", "")
ALERT_RECIPIENT     = "reddamgufus21188@gmail.com"

# ── Google Sheets ──────────────────────────────────────────────────────────────
GOOGLE_SHEET_NAME              = "Data Engineer Job Search 2025"
GOOGLE_SERVICE_ACCOUNT_JSON    = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

# ── Supabase ───────────────────────────────────────────────────────────────────
SUPABASE_URL         = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# ── NVIDIA NIM ─────────────────────────────────────────────────────────────────
NVIDIA_API_KEY       = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL      = "https://ai.api.nvidia.com/v1"
NVIDIA_CHAT_MODEL    = "nvidia/llama-3.1-8b-instruct"
NVIDIA_EMBED_MODEL   = "nvidia/nv-embedqa-e5-v5"
LLM_ENABLED          = bool(NVIDIA_API_KEY)   # auto-disable if no key

# ── Optional API Keys ──────────────────────────────────────────────────────────
ADZUNA_APP_ID   = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY  = os.getenv("ADZUNA_APP_KEY", "")
JOOBLE_API_KEY  = os.getenv("JOOBLE_API_KEY", "")
USAJOBS_API_KEY = os.getenv("USAJOBS_API_KEY", "")    # free at usajobs.gov

# ── LinkedIn (for posts scraping) ──────────────────────────────────────────────
LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# ── Resume (Phase 2 — cover letter + skill gap analysis) ──────────────────────
# Set to the absolute path of your resume file (.pdf or .txt)
RESUME_PATH = os.getenv("RESUME_PATH", "")

# ── Phase 2 Feature Flags ──────────────────────────────────────────────────────
ENABLE_HN_SCRAPER        = True   # Hacker News Who's Hiring thread
ENABLE_SKILL_GAP         = True   # Run skill gap analysis after each run
ENABLE_COVER_LETTER      = False  # Auto-generate cover letters (requires LLM)

# ── Database (SQLite fallback when Supabase not configured) ────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")

# ── Scraper Behaviour ──────────────────────────────────────────────────────────
REQUEST_DELAY_MIN  = 1.5   # seconds between requests
REQUEST_DELAY_MAX  = 3.5
HEADLESS_BROWSER   = True
PLAYWRIGHT_TIMEOUT = 30_000   # ms
MAX_WORKERS        = 8        # parallel scraper threads

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
