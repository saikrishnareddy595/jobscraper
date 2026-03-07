"""
Central configuration for the Job Scraping System.
All user-facing settings live here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Role Categories ────────────────────────────────────────────────────────────
# Only Data Engineering roles are targeted — all ML/AI/NLP/CV/DS categories removed.
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
        "Data Architect",
        "Data Integration Engineer",
        "Data Warehouse Engineer",
        "Cloud Data Engineer",
        "Senior Data Engineer",
        "Staff Data Engineer",
        "Lead Data Engineer",
    ],
}

# Flat list of all job titles (used by Dice, Jooble, etc.)
JOB_TITLES: list = []
for titles in ROLE_CATEGORIES.values():
    JOB_TITLES.extend(titles)

# Reduced list for JobSpy (LinkedIn) — each title takes ~1 min, run in parallel.
# Data Engineering titles only.
JOBSPY_TITLES: list = [
    "Data Engineer",
    "ETL Engineer",
    "Analytics Engineer",
    "Data Platform Engineer",
    "Data Infrastructure Engineer",
    "Big Data Engineer",
    "Data Warehouse Engineer",
    "Cloud Data Engineer",
]

# ── Search Parameters ──────────────────────────────────────────────────────────
LOCATIONS = ["United States", "Remote USA", "Remote"]

MIN_SALARY        = 80_000   # USD / year
MAX_JOB_AGE_HOURS = 24       # delta-sync jobs from the past 24 hours
MAX_APPLICANTS    = 100      # filter out saturated postings

EASY_APPLY_ONLY = False    # include all application types

# Job types to include
JOB_TYPES = ["full_time", "contract", "contract_to_hire", "part_time"]

WORK_TYPES = ["on-site", "remote", "hybrid"]

# ── Keywords ───────────────────────────────────────────────────────────────────
INCLUDE_KEYWORDS = [
    "data pipeline", "ETL", "Spark", "Kafka", "Airflow", "dbt", "SQL",
    "Python", "cloud", "AWS", "GCP", "Azure", "data warehouse", "Snowflake",
    "Databricks", "BigQuery", "Redshift", "Flink", "Beam", "Hive",
    "Kubernetes", "Docker", "data lake", "data lakehouse", "Delta Lake",
    "data modeling", "data orchestration", "data integration",
]

EXCLUDE_KEYWORDS = [
    # Seniority / role type
    "unpaid", "10+ years", "15+ years", "VP of", "Vice President",
    # ML / AI / Data Science titles to exclude from results
    "machine learning engineer", "ml engineer", "mlops engineer",
    "ml platform engineer", "applied ml engineer", "deep learning engineer",
    "ai engineer", "artificial intelligence engineer", "llm engineer",
    "generative ai engineer", "prompt engineer", "ai/ml engineer",
    "nlp engineer", "natural language processing", "conversational ai",
    "computer vision engineer", "vision ai engineer",
    "data scientist", "applied scientist", "research scientist", "ml scientist",
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
GMAIL_ADDRESS       = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD  = os.getenv("GMAIL_APP_PASSWORD", "")
ALERT_RECIPIENT     = os.getenv("ALERT_RECIPIENT", os.getenv("GMAIL_ADDRESS", ""))

# ── Google Sheets ──────────────────────────────────────────────────────────────
GOOGLE_SHEET_NAME              = "Data Engineering Job Search 2025"
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

# ── Direct API Scrape Targets (Delta-Sync) ──────────────────────────────────────
WORKDAY_COMPANIES = ["nvidia", "adobe", "capitalone", "dell", "salesforce"]
GREENHOUSE_COMPANIES = ["airbnb", "stripe", "doordash", "figma", "reddit", "lyft"]
AMAZON_SCRAPE_ENABLED = True


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

# ── Recruiter Discovery ────────────────────────────────────────────────────────
# Set to True to run recruiter discovery after each scrape cycle.
# Discovery runs asynchronously so it does NOT block the main pipeline.
ENABLE_RECRUITER_DISCOVERY = True

# Minimum confidence score (0–100) to persist a recruiter link
RECRUITER_MIN_CONFIDENCE = 30

# Thread-pool workers for async recruiter discovery
# Lower = fewer simultaneous DuckDuckGo requests (less chance of blocking)
RECRUITER_WORKERS = 3

# Maximum number of jobs to run recruiter discovery on per pipeline run.
# Top-scored jobs are prioritised. Set to 0 to disable the cap.
RECRUITER_MAX_JOBS = 50

# ── Outreach Generator ────────────────────────────────────────────────────────
# Set to True to automatically generate personalized outreach messages
# for discovered recruiters.
ENABLE_OUTREACH_GENERATOR = True
OUTREACH_TONE = "professional, confident"


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
