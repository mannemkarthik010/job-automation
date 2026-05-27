"""
sheets_logger.py
─────────────────────────────────────────────
Handles all Google Sheets read/write operations.
Only logs Applied and Pending Review jobs — skipped jobs are never written.
"""

import logging
import json
import os
from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

from config import (
    GOOGLE_SHEETS_CREDS,
    SPREADSHEET_ID,
    SHEET_APPLIED,
    SHEET_PENDING,
    SHEET_PROGRESS,
    SHEET_INTERVIEWS,
    SHEET_FOLLOWUPS,
    RESUME_VERSION,
)

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ─── Connection ───────────────────────────────────────────────────────────────

def _get_client() -> gspread.Client:
    creds_value = GOOGLE_SHEETS_CREDS

    # If it looks like JSON content, write to a temp file first
    if creds_value.strip().startswith("{"):
        import tempfile
        # Clean up any leading/trailing whitespace or newlines
        cleaned = creds_value.strip()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write(cleaned)
            tmp_path = f.name
        try:
            creds = Credentials.from_service_account_file(tmp_path, scopes=SCOPES)
        finally:
            os.unlink(tmp_path)
    else:
        # It's a file path — read and clean it
        with open(creds_value, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write(raw)
            tmp_path = f.name
        try:
            creds = Credentials.from_service_account_file(tmp_path, scopes=SCOPES)
        finally:
            os.unlink(tmp_path)

    return gspread.authorize(creds)


def _get_spreadsheet():
    return _get_client().open_by_key(SPREADSHEET_ID)


# ─── Sheet Setup ──────────────────────────────────────────────────────────────

def ensure_sheets_exist():
    """
    Create all required tabs if they don't already exist,
    and add header rows to new tabs.
    """
    ss = _get_spreadsheet()
    existing = [ws.title for ws in ss.worksheets()]

    tabs = {
        SHEET_APPLIED: [
            "Date Applied", "Company Name", "Job Title", "Location",
            "Job Link", "Source", "Job Type", "Required Skills",
            "Experience Required", "Resume Match Score", "Resume Version",
            "Cover Letter Used", "Confirmation Received", "Follow-Up Date",
            "Current Status", "Notes"
        ],
        SHEET_PENDING: [
            "Date Found", "Company Name", "Job Title", "Location",
            "Job Link", "Resume Match Score", "Reason for Review",
            "Question Asked", "Recommended Answer", "User Decision", "Status"
        ],
        SHEET_PROGRESS: [
            "Date", "Jobs Searched", "Jobs Applied", "Pending Review",
            "Silently Skipped", "Duplicates Found", "Top Companies",
            "Top Roles", "Top Locations", "Recommendations"
        ],
        SHEET_INTERVIEWS: [
            "Date", "Company Name", "Job Title", "Interview Type",
            "Interview Date", "Notes", "Status"
        ],
        SHEET_FOLLOWUPS: [
            "Follow-Up Date", "Company Name", "Job Title",
            "Date Applied", "Job Link", "Status"
        ],
    }

    for tab_name, headers in tabs.items():
        if tab_name not in existing:
            ws = ss.add_worksheet(title=tab_name, rows=1000, cols=len(headers))
            ws.append_row(headers, value_input_option="RAW")
            logger.info(f"Created sheet tab: {tab_name}")
        else:
            logger.debug(f"Sheet tab already exists: {tab_name}")


# ─── Duplicate Check ──────────────────────────────────────────────────────────

def is_duplicate(company: str, title: str) -> bool:
    """Return True if this company+title combo already exists in Applied Jobs."""
    try:
        ws = _get_spreadsheet().worksheet(SHEET_APPLIED)
        records = ws.get_all_records()
        for row in records:
            if (str(row.get("Company Name", "")).lower() == company.lower() and
                    str(row.get("Job Title", "")).lower() == title.lower()):
                return True
        return False
    except Exception as e:
        logger.error(f"Duplicate check failed: {e}")
        return False  # If check fails, don't block the application


# ─── Log Applied Job ──────────────────────────────────────────────────────────

def log_applied(job: dict, score: int, cover_letter_used: bool) -> bool:
    """Write one row to the Applied Jobs tab."""
    try:
        ws = _get_spreadsheet().worksheet(SHEET_APPLIED)
        followup_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),   # Date Applied
            job.get("company", ""),                       # Company Name
            job.get("title", ""),                         # Job Title
            job.get("location", ""),                      # Location
            job.get("link", ""),                          # Job Link
            job.get("source", ""),                        # Source
            job.get("job_type", ""),                      # Job Type
            job.get("skills", ""),                        # Required Skills
            job.get("experience", ""),                    # Experience Required
            score,                                        # Resume Match Score
            RESUME_VERSION,                               # Resume Version
            "Yes" if cover_letter_used else "No",         # Cover Letter Used
            "",                                           # Confirmation Received
            followup_date,                                # Follow-Up Date
            "Applied",                                    # Current Status
            "",                                           # Notes
        ], value_input_option="RAW")

        # Also add to follow-up tracker
        _add_followup(job, followup_date)
        return True

    except Exception as e:
        logger.error(f"Failed to log applied job {job.get('title')}: {e}")
        return False


# ─── Log Pending Review ───────────────────────────────────────────────────────

def log_pending(job: dict, score: int, reason: str, question: str) -> bool:
    """Write one row to the Pending Review tab."""
    try:
        ws = _get_spreadsheet().worksheet(SHEET_PENDING)

        ws.append_row([
            datetime.now().strftime("%Y-%m-%d"),   # Date Found
            job.get("company", ""),                # Company Name
            job.get("title", ""),                  # Job Title
            job.get("location", ""),               # Location
            job.get("link", ""),                   # Job Link
            score,                                 # Resume Match Score
            reason,                                # Reason for Review
            question,                              # Question Asked
            "",                                    # Recommended Answer
            "",                                    # User Decision
            "Waiting",                             # Status
        ], value_input_option="RAW")
        return True

    except Exception as e:
        logger.error(f"Failed to log pending job {job.get('title')}: {e}")
        return False


# ─── Log Daily Summary ────────────────────────────────────────────────────────

def log_daily_summary(stats: dict) -> bool:
    """Append one row to the Daily Progress tab."""
    try:
        ws = _get_spreadsheet().worksheet(SHEET_PROGRESS)

        ws.append_row([
            datetime.now().strftime("%Y-%m-%d"),
            stats.get("searched", 0),
            stats.get("applied", 0),
            stats.get("pending", 0),
            stats.get("skipped", 0),
            stats.get("duplicates", 0),
            ", ".join(stats.get("top_companies", [])[:5]),
            ", ".join(stats.get("top_roles", [])[:5]),
            ", ".join(stats.get("top_locations", [])[:5]),
            stats.get("recommendations", ""),
        ], value_input_option="RAW")
        return True

    except Exception as e:
        logger.error(f"Failed to log daily summary: {e}")
        return False


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _add_followup(job: dict, followup_date: str):
    try:
        ws = _get_spreadsheet().worksheet(SHEET_FOLLOWUPS)
        ws.append_row([
            followup_date,
            job.get("company", ""),
            job.get("title", ""),
            datetime.now().strftime("%Y-%m-%d"),
            job.get("link", ""),
            "Pending",
        ], value_input_option="RAW")
    except Exception as e:
        logger.warning(f"Could not add follow-up row: {e}")
