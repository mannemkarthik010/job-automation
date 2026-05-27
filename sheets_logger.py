"""
sheets_logger.py
─────────────────────────────────────────────
Handles all Google Sheets read/write operations.
Credentials come in as a JSON string via environment variable.
No file writing needed.
"""

import logging
import json
import os
from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

from config import (
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


def _get_client() -> gspread.Client:
    """
    Build credentials directly from the JSON string in the environment.
    Works for both GitHub Actions (JSON string) and local (file path).
    """
    raw = os.environ.get("GOOGLE_SHEETS_CREDS", "").strip()

    if not raw:
        raise ValueError(
            "GOOGLE_SHEETS_CREDS is empty. "
            "Add it as a GitHub Secret (paste the full JSON content)."
        )

    # GitHub Actions: value is the JSON content itself
    if raw.startswith("{"):
        # Find the outermost { } in case of any surrounding whitespace
        start = raw.index("{")
        end   = raw.rindex("}") + 1
        info  = json.loads(raw[start:end])

    # Local development: value is a file path
    else:
        if not os.path.exists(raw):
            raise FileNotFoundError(
                f"GOOGLE_SHEETS_CREDS points to '{raw}' but that file does not exist."
            )
        with open(raw, "r", encoding="utf-8") as f:
            content = f.read().strip()
        start = content.index("{")
        end   = content.rindex("}") + 1
        info  = json.loads(content[start:end])

    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_spreadsheet():
    sid = SPREADSHEET_ID.strip()
    if not sid:
        raise ValueError(
            "SPREADSHEET_ID is empty. "
            "Add it as a GitHub Secret (just the ID from the Google Sheet URL)."
        )
    return _get_client().open_by_key(sid)


def ensure_sheets_exist():
    ss       = _get_spreadsheet()
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
            logger.debug(f"Tab already exists: {tab_name}")


def is_duplicate(company: str, title: str) -> bool:
    try:
        ws      = _get_spreadsheet().worksheet(SHEET_APPLIED)
        records = ws.get_all_records()
        for row in records:
            if (str(row.get("Company Name", "")).lower() == company.lower() and
                    str(row.get("Job Title", "")).lower() == title.lower()):
                return True
        return False
    except Exception as e:
        logger.error(f"Duplicate check failed: {e}")
        return False


def log_applied(job: dict, score: int, cover_letter_used: bool) -> bool:
    try:
        ws            = _get_spreadsheet().worksheet(SHEET_APPLIED)
        followup_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            job.get("company", ""),
            job.get("title", ""),
            job.get("location", ""),
            job.get("link", ""),
            job.get("source", ""),
            job.get("job_type", ""),
            job.get("skills", ""),
            job.get("experience", ""),
            score,
            RESUME_VERSION,
            "Yes" if cover_letter_used else "No",
            "",
            followup_date,
            "Applied",
            "",
        ], value_input_option="RAW")
        _add_followup(job, followup_date)
        return True
    except Exception as e:
        logger.error(f"Failed to log applied job {job.get('title')}: {e}")
        return False


def log_pending(job: dict, score: int, reason: str, question: str) -> bool:
    try:
        ws = _get_spreadsheet().worksheet(SHEET_PENDING)
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d"),
            job.get("company", ""),
            job.get("title", ""),
            job.get("location", ""),
            job.get("link", ""),
            score,
            reason,
            question,
            "",
            "",
            "Waiting",
        ], value_input_option="RAW")
        return True
    except Exception as e:
        logger.error(f"Failed to log pending job {job.get('title')}: {e}")
        return False


def log_daily_summary(stats: dict) -> bool:
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
