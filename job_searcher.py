"""
job_searcher.py
─────────────────────────────────────────────
Uses Claude with web search to find fresh job postings every morning.
Returns a list of structured job dictionaries.
"""

import anthropic
import json
import logging
import re
from config import (
    ANTHROPIC_API_KEY,
    TARGET_ROLES,
    TARGET_LOCATIONS,
    JOB_SOURCES,
    MAX_EXPERIENCE_YEARS,
    PROFILE,
)

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_search_prompt() -> str:
    roles_str     = "\n".join(f"  - {r}" for r in TARGET_ROLES[:30])
    locations_str = ", ".join(TARGET_LOCATIONS[:15]) + ", and all other US cities"
    sources_str   = ", ".join(JOB_SOURCES)

    return f"""
You are a job search agent running an automated morning search for {PROFILE['name']},
a {PROFILE['degree']} student at {PROFILE['university']} graduating {PROFILE['graduation']}.

Use your web search tool to find job postings from the LAST 48 HOURS on these platforms:
{sources_str}

Search for these roles:
{roles_str}

Search in these locations (applicant will relocate anywhere in the US):
{locations_str}

Also search for "Remote" versions of all roles above.

STRICT RULES:
1. Only include roles requiring {MAX_EXPERIENCE_YEARS} or fewer years of experience,
   OR internship / new grad / entry-level / junior roles.
2. Skip any role explicitly requiring 5+ years of experience.
3. Include direct application links only — no aggregator redirect links if possible.
4. Search multiple sources. Try to return 50-100 unique jobs.

For EVERY job found, return a JSON array with this exact structure:
[
  {{
    "company": "Company Name",
    "title": "Exact Job Title",
    "location": "City, State or Remote",
    "link": "https://direct-application-link.com",
    "source": "LinkedIn / Indeed / company career page / etc",
    "job_type": "internship / new grad / junior / full-time 0-2 years",
    "skills": "comma-separated top skills from job description",
    "experience": "e.g. 0-2 years / new graduate / intern",
    "description": "full job description text (copy as much as possible)",
    "deadline": "date if mentioned, else empty string",
    "asks_sensitive_questions": false,
    "sensitive_question": ""
  }}
]

If a posting mentions visa sponsorship requirements, salary questions, security
clearance, or unusual eligibility questions, set asks_sensitive_questions to true
and describe the question in sensitive_question.

Return ONLY the JSON array. No preamble, no markdown fences, no explanation.
If you find no jobs, return an empty array [].
"""


def search_jobs() -> list[dict]:
    """
    Call Claude with web search enabled and return a list of job dicts.
    Falls back to an empty list on any error.
    """
    logger.info("Starting job search via Claude web search...")

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=8192,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": _build_search_prompt()}],
        )

        # Extract the text block from the response
        raw_text = ""
        for block in response.content:
            if hasattr(block, "type") and block.type == "text":
                raw_text += block.text

        if not raw_text.strip():
            logger.warning("Claude returned no text content from job search.")
            return []

        # Strip markdown fences if present
        raw_text = re.sub(r"```json|```", "", raw_text).strip()

        # Find the JSON array
        start = raw_text.find("[")
        end   = raw_text.rfind("]") + 1
        if start == -1 or end == 0:
            logger.error("No JSON array found in Claude response.")
            logger.debug(f"Raw response: {raw_text[:500]}")
            return []

        jobs = json.loads(raw_text[start:end])
        logger.info(f"Found {len(jobs)} jobs from search.")
        return jobs

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in job search: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in job search: {e}")
        return []
