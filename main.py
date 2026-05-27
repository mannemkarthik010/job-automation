"""
main.py
─────────────────────────────────────────────
Master orchestrator. This is the file that runs every morning.
Called by GitHub Actions at 6 AM PST automatically.

Flow:
  1. Load resume
  2. Search for jobs via Claude + web search
  3. For each job:
     a. Check duplicate
     b. Score against resume
     c. Route: apply / pending review / silent skip
  4. Log daily summary to Google Sheets
  5. Print final report to console (visible in GitHub Actions logs)
"""

import logging
import sys
import time
from datetime import datetime

from config import DAILY_TARGET, MIN_MATCH_SCORE, RESUME_FILE
from job_searcher import search_jobs
from resume_matcher import evaluate_job
from sheets_logger import (
    ensure_sheets_exist,
    is_duplicate,
    log_applied,
    log_pending,
    log_daily_summary,
)
from daily_summary import generate_recommendations

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
logger = logging.getLogger(__name__)


# ─── Load Resume ──────────────────────────────────────────────────────────────

def load_resume() -> str:
    try:
        with open(RESUME_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            logger.error(f"{RESUME_FILE} is empty. Add your resume text and retry.")
            sys.exit(1)
        logger.info(f"Resume loaded ({len(content)} characters).")
        return content
    except FileNotFoundError:
        logger.error(f"{RESUME_FILE} not found. Create it with your resume text.")
        sys.exit(1)


# ─── Main Workflow ────────────────────────────────────────────────────────────

def run():
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"MORNING JOB APPLICATION RUN — {start_time.strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 60)

    # Step 0: Ensure all Google Sheets tabs exist
    logger.info("Verifying Google Sheets structure...")
    ensure_sheets_exist()

    # Step 1: Load resume
    resume_text = load_resume()

    # Step 2: Search for jobs
    logger.info("Searching for jobs...")
    jobs = search_jobs()
    logger.info(f"Total jobs found: {len(jobs)}")

    if not jobs:
        logger.warning("No jobs found today. Logging empty summary and exiting.")
        log_daily_summary({
            "searched": 0, "applied": 0, "pending": 0,
            "skipped": 0, "duplicates": 0,
            "top_companies": [], "top_roles": [], "top_locations": [],
            "recommendations": "Job search returned 0 results. Check search prompt.",
        })
        return

    # Step 3: Process each job
    stats = {
        "searched": len(jobs),
        "applied": 0,
        "pending": 0,
        "skipped": 0,
        "duplicates": 0,
        "top_companies": [],
        "top_roles": [],
        "top_locations": [],
    }

    for i, job in enumerate(jobs):
        company = job.get("company", "Unknown")
        title   = job.get("title", "Unknown")
        logger.info(f"[{i+1}/{len(jobs)}] Processing: {title} at {company}")

        # Stop if daily target is reached
        if stats["applied"] >= DAILY_TARGET:
            logger.info(f"Daily target of {DAILY_TARGET} applications reached. Stopping.")
            break

        # ── Check duplicate ──────────────────────────────────────────────────
        if is_duplicate(company, title):
            logger.info(f"  DUPLICATE — skipping.")
            stats["duplicates"] += 1
            continue

        # ── Score and evaluate ───────────────────────────────────────────────
        result = evaluate_job(job, resume_text)
        score  = result["score"]

        logger.info(f"  Score: {score}/10 | Apply: {result['apply']} | "
                    f"Exceeds exp: {result['exceeds_experience']}")

        # ── Route based on result ────────────────────────────────────────────

        # Silent skip: score too low or requires too much experience
        if score < MIN_MATCH_SCORE or result["exceeds_experience"]:
            stats["skipped"] += 1
            logger.info(f"  SKIPPED (score {score} < {MIN_MATCH_SCORE} "
                        f"or exceeds experience threshold).")
            continue

        # Pending review: score is fine but has uncertain questions
        if not result["apply"]:
            reason   = result.get("pending_reason", "Manual review required")
            question = result.get("pending_question", "See job posting")
            if log_pending(job, score, reason, question):
                stats["pending"] += 1
                logger.info(f"  PENDING REVIEW — {reason}")
            continue

        # Apply: score >= threshold and no blockers
        cover_letter_used = bool(result.get("cover_letter"))
        if log_applied(job, score, cover_letter_used):
            stats["applied"] += 1
            stats["top_companies"].append(company)
            stats["top_roles"].append(title)
            stats["top_locations"].append(job.get("location", "Unknown"))
            logger.info(f"  APPLIED ✓ (score {score})")

        # Small delay to avoid hammering APIs
        time.sleep(1)

    # Step 4: Deduplicate top lists and trim
    stats["top_companies"] = list(dict.fromkeys(stats["top_companies"]))[:5]
    stats["top_roles"]     = list(dict.fromkeys(stats["top_roles"]))[:5]
    stats["top_locations"] = list(dict.fromkeys(stats["top_locations"]))[:5]

    # Step 5: Generate recommendations
    logger.info("Generating tomorrow's recommendations...")
    stats["recommendations"] = generate_recommendations(stats)

    # Step 6: Log daily summary
    log_daily_summary(stats)

    # Step 7: Final console report
    elapsed = (datetime.now() - start_time).seconds // 60
    logger.info("")
    logger.info("=" * 60)
    logger.info("DAILY SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Jobs searched:       {stats['searched']}")
    logger.info(f"  Applications sent:   {stats['applied']}")
    logger.info(f"  Pending review:      {stats['pending']}")
    logger.info(f"  Silently skipped:    {stats['skipped']}")
    logger.info(f"  Duplicates avoided:  {stats['duplicates']}")
    logger.info(f"  Top companies:       {', '.join(stats['top_companies'])}")
    logger.info(f"  Top roles:           {', '.join(stats['top_roles'])}")
    logger.info(f"  Run time:            {elapsed} minutes")
    logger.info("")
    logger.info(f"  Recommendations:\n{stats['recommendations']}")
    logger.info("=" * 60)
    logger.info("Run complete. Check your Google Sheets for full details.")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run()
