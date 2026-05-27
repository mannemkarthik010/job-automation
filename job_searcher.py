"""
job_searcher.py
─────────────────────────────────────────────
Uses Claude with web search to find job postings.
Accepts partial data — we don't need perfect info, just enough to log and apply.
"""

import anthropic
import json
import logging
import re
from config import (
    ANTHROPIC_API_KEY,
    MAX_EXPERIENCE_YEARS,
    PROFILE,
)

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_search_prompt() -> str:
    return f"""
Search the web for current job postings for these roles:
Machine Learning Engineer, AI Engineer, Data Scientist, Software Engineer,
NLP Engineer, MLOps Engineer, Data Analyst, Full Stack Developer,
Python Developer, Deep Learning Engineer, Generative AI Engineer,
Junior Software Engineer, Data Engineer, Backend Engineer.

Search on LinkedIn, Indeed, Wellfound, Glassdoor, and company career pages.
Focus on US locations and remote roles.
Only include jobs for 0-{MAX_EXPERIENCE_YEARS} years experience, new grads, interns, junior roles.

IMPORTANT: Return whatever you find. Partial information is fine.
If you don't have a direct link, use the search result URL.
If you don't have the full description, use the snippet you found.
Do NOT refuse to return JSON. Always return a JSON array even with partial data.

Return a JSON array like this:
[
  {{
    "company": "Company name here",
    "title": "Job title here",
    "location": "City, State or Remote",
    "link": "whatever URL you found for this job",
    "source": "LinkedIn / Indeed / etc",
    "job_type": "full-time / internship / new grad",
    "skills": "skills mentioned in snippet",
    "experience": "0-2 years / new grad / intern",
    "description": "whatever description text you found, even if partial",
    "asks_sensitive_questions": false,
    "sensitive_question": ""
  }}
]

Search now. Return ONLY the JSON array. No explanations. No markdown.
Even if data is incomplete, still return it as JSON.
"""


def _make_fallback_jobs_from_text(text: str) -> list[dict]:
    """
    Last resort: if Claude returned a table or list instead of JSON,
    try to extract company/title pairs from it.
    """
    jobs = []

    # Look for patterns like "Company | Role" or "Company - Role"
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("|---"):
            continue

        # Try "| Company | Role | Location |" table format
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                company = parts[0]
                title   = parts[1]
                location = parts[2] if len(parts) > 2 else "US"
                # Skip header rows
                if company.lower() in ["company", "organization", "employer"]:
                    continue
                if len(company) > 3 and len(title) > 3:
                    jobs.append({
                        "company":    company,
                        "title":      title,
                        "location":   location,
                        "link":       f"https://www.linkedin.com/jobs/search/?keywords={title.replace(' ', '%20')}%20{company.replace(' ', '%20')}",
                        "source":     "extracted from search summary",
                        "job_type":   "full-time",
                        "skills":     "",
                        "experience": "0-2 years",
                        "description": f"{title} role at {company} in {location}",
                        "asks_sensitive_questions": False,
                        "sensitive_question": "",
                    })

    logger.info(f"Fallback extraction found {len(jobs)} jobs from text.")
    return jobs


def search_jobs() -> list[dict]:
    logger.info("Starting job search via Claude web search...")

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=8192,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search"
            }],
            messages=[
                {
                    "role": "user",
                    "content": _build_search_prompt()
                }
            ],
        )

        # Collect all text blocks
        full_text = ""
        for block in response.content:
            if hasattr(block, "type") and block.type == "text":
                full_text += block.text

        logger.info(f"Response text length: {len(full_text)} chars")

        if not full_text.strip():
            logger.warning("No text in response.")
            return []

        # ── Strategy 1: Direct JSON parse ─────────────────────────────────
        try:
            cleaned = re.sub(r"```json|```", "", full_text).strip()
            jobs = json.loads(cleaned)
            if isinstance(jobs, list) and jobs:
                logger.info(f"Strategy 1 success: {len(jobs)} jobs parsed.")
                return _validate_jobs(jobs)
        except Exception:
            pass

        # ── Strategy 2: Find [ ... ] array ────────────────────────────────
        try:
            start = full_text.index("[")
            end   = full_text.rindex("]") + 1
            jobs  = json.loads(full_text[start:end])
            if isinstance(jobs, list) and jobs:
                logger.info(f"Strategy 2 success: {len(jobs)} jobs parsed.")
                return _validate_jobs(jobs)
        except Exception:
            pass

        # ── Strategy 3: Extract individual { } objects ────────────────────
        try:
            pattern = r'\{(?:[^{}]|\{[^{}]*\})*\}'
            matches = re.findall(pattern, full_text, re.DOTALL)
            jobs = []
            for m in matches:
                try:
                    obj = json.loads(m)
                    if "company" in obj or "title" in obj:
                        jobs.append(obj)
                except Exception:
                    pass
            if jobs:
                logger.info(f"Strategy 3 success: {len(jobs)} jobs extracted.")
                return _validate_jobs(jobs)
        except Exception:
            pass

        # ── Strategy 4: Parse tables/lists as fallback ────────────────────
        jobs = _make_fallback_jobs_from_text(full_text)
        if jobs:
            logger.info(f"Strategy 4 (fallback) success: {len(jobs)} jobs.")
            return jobs

        # ── Strategy 5: Ask Claude to reformat what it found ──────────────
        logger.info("Trying Strategy 5: asking Claude to reformat its results...")
        reformat_response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": _build_search_prompt()
                },
                {
                    "role": "assistant",
                    "content": full_text
                },
                {
                    "role": "user",
                    "content": """Take everything you found above and reformat it 
as a JSON array. Use partial data where needed — empty strings are fine.
Every job must have: company, title, location, link, source, job_type,
skills, experience, description, asks_sensitive_questions, sensitive_question.
Return ONLY the JSON array, nothing else. Start your response with ["""
                }
            ],
        )

        reformat_text = ""
        for block in reformat_response.content:
            if hasattr(block, "type") and block.type == "text":
                reformat_text += block.text

        # Prepend [ since we told Claude to start with it
        if reformat_text and not reformat_text.strip().startswith("["):
            reformat_text = "[" + reformat_text

        try:
            end  = reformat_text.rindex("]") + 1
            jobs = json.loads(reformat_text[:end])
            if isinstance(jobs, list) and jobs:
                logger.info(f"Strategy 5 success: {len(jobs)} jobs reformatted.")
                return _validate_jobs(jobs)
        except Exception as e:
            logger.error(f"Strategy 5 failed: {e}")

        logger.warning("All strategies failed. No jobs extracted.")
        logger.warning(f"Response preview: {full_text[:500]}")
        return []

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in job search: {e}", exc_info=True)
        return []


def _validate_jobs(jobs: list) -> list[dict]:
    """Fill in missing fields with defaults so downstream code never crashes."""
    valid = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        # Must have at least company and title
        if not job.get("company") and not job.get("title"):
            continue
        # Fill missing fields with defaults
        job.setdefault("company",    "Unknown")
        job.setdefault("title",      "Unknown")
        job.setdefault("location",   "US")
        job.setdefault("link",       "")
        job.setdefault("source",     "web search")
        job.setdefault("job_type",   "full-time")
        job.setdefault("skills",     "")
        job.setdefault("experience", "0-2 years")
        job.setdefault("description","")
        job.setdefault("asks_sensitive_questions", False)
        job.setdefault("sensitive_question", "")
        valid.append(job)
    return valid
