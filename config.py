"""
config.py
─────────────────────────────────────────────
Central configuration. All settings are read from environment variables
so they work both locally (.env file) and in GitHub Actions (secrets).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_SHEETS_CREDS = os.environ.get("GOOGLE_SHEETS_CREDS", "google_creds.json")
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]

# ─── Applicant Profile ────────────────────────────────────────────────────────
PROFILE = {
    "name":             os.environ.get("APPLICANT_NAME", "Karthik Mannem"),
    "degree":           os.environ.get("APPLICANT_DEGREE", "Master of Science in Computer Science"),
    "university":       os.environ.get("APPLICANT_UNIVERSITY", "California State University, Northridge"),
    "graduation":       os.environ.get("APPLICANT_GRADUATION", "May 2026"),
    "gpa":              os.environ.get("APPLICANT_GPA", "3.8"),
    "work_auth":        os.environ.get("APPLICANT_WORK_AUTH", "F-1 OPT"),
    "needs_sponsorship":os.environ.get("APPLICANT_NEEDS_SPONSORSHIP", "No"),
    "relocate":         os.environ.get("APPLICANT_RELOCATE", "Yes, anywhere in the United States"),
    "remote_pref":      os.environ.get("APPLICANT_REMOTE_PREF", "No preference"),
}

# ─── Application Rules ────────────────────────────────────────────────────────
MIN_MATCH_SCORE       = int(os.environ.get("MIN_MATCH_SCORE", "5"))
MAX_EXPERIENCE_YEARS  = int(os.environ.get("MAX_EXPERIENCE_YEARS", "4"))
DAILY_TARGET          = int(os.environ.get("DAILY_APPLICATION_TARGET", "100"))
RESUME_VERSION        = os.environ.get("RESUME_VERSION", "v1")
RESUME_FILE           = "resume.txt"

# ─── Target Job Roles ─────────────────────────────────────────────────────────
TARGET_ROLES = [
    # AI / ML (highest priority)
    "Machine Learning Engineer",
    "AI Engineer",
    "Applied Scientist",
    "Applied ML Engineer",
    "NLP Engineer",
    "Computer Vision Engineer",
    "Deep Learning Engineer",
    "Generative AI Engineer",
    "LLM Engineer",
    "MLOps Engineer",
    "AI Research Engineer",
    "ML Research Scientist",
    "Machine Learning Intern",
    "AI Engineer Intern",
    "Deep Learning Intern",
    "NLP Intern",
    "Computer Vision Intern",
    # Data
    "Data Scientist",
    "Junior Data Scientist",
    "Data Analyst",
    "Data Engineer",
    "Analytics Engineer",
    "Business Intelligence Analyst",
    "Quantitative Analyst",
    "Data Science Intern",
    "Data Analyst Intern",
    # Software Engineering
    "Software Engineer",
    "New Grad Software Engineer",
    "Junior Software Engineer",
    "Full Stack Developer",
    "Backend Engineer",
    "Frontend Engineer",
    "Python Developer",
    "Cloud Engineer",
    "DevOps Engineer",
    "Software Engineer Intern",
    "Full Stack Intern",
    "Backend Engineer Intern",
    # Other
    "Research Assistant",
    "Solutions Engineer",
    "AI Product Analyst",
    "Technical Marketing Engineer",
]

# ─── Target US Locations ──────────────────────────────────────────────────────
TARGET_LOCATIONS = [
    "San Francisco Bay Area CA",
    "San Jose CA",
    "Seattle WA",
    "New York NY",
    "Boston MA",
    "Austin TX",
    "Los Angeles CA",
    "San Diego CA",
    "Irvine CA",
    "Redmond WA",
    "Bellevue WA",
    "Menlo Park CA",
    "Mountain View CA",
    "Sunnyvale CA",
    "Santa Clara CA",
    "Dallas TX",
    "Houston TX",
    "Atlanta GA",
    "Chicago IL",
    "Raleigh NC",
    "Durham NC",
    "Phoenix AZ",
    "Denver CO",
    "Miami FL",
    "Pittsburgh PA",
    "Philadelphia PA",
    "Washington DC",
    "Minneapolis MN",
    "Portland OR",
    "Salt Lake City UT",
    "Nashville TN",
    "Charlotte NC",
    "Remote",
]

# ─── Job Sources ──────────────────────────────────────────────────────────────
JOB_SOURCES = [
    "LinkedIn",
    "Indeed",
    "Handshake",
    "Wellfound",
    "Simplify",
    "Glassdoor",
    "Greenhouse career pages",
    "Lever career pages",
    "Workday career pages",
]

# ─── Google Sheets Tab Names ──────────────────────────────────────────────────
SHEET_APPLIED   = "Applied Jobs"
SHEET_PENDING   = "Pending Review"
SHEET_PROGRESS  = "Daily Progress"
SHEET_INTERVIEWS= "Interview Tracker"
SHEET_FOLLOWUPS = "Follow-Up Tracker"
