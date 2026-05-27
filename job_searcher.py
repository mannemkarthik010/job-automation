"""
job_searcher.py
─────────────────────────────────────────────
Uses Claude with web search to find fresh job postings every morning.
"""

import anthropic
import json
import logging
import re
from config import (
    ANTHROPIC_API_KEY,
    TARGET_ROLES,
    TARGET_LOCATIONS,
    MAX_EXPERIENCE_YEARS,
    PROFILE,
)

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _extract_json_from_text(text: str) -> list:
    """Try multiple strategies to extract a JSON array from text."""

    # Strategy 1: Direct parse if it's clean JSON
    try:
        cleaned = re.sub(r"```json|```", "", text).strip()
        return json.loads(cleaned)
    except Exception:
        pass

    # Strategy 2: Find [ ... ] array in the text
    try:
        start = text.index("[")
        end   = text.rindex("]") + 1
        return json.loads(text[start:end])
    except Exception:
        pass

    # Strategy 3: Extract individual job objects with regex
    try:
        objects = re.findall(r'\{[^{}]+\}', text, re.DOTALL)
        jobs = []
        for obj in objects:
            try:
                jobs.append(json.loads(obj))
            except Exception:
                pass
        if jobs:
            return jobs
    except Exception:
        pass

    return []


def _build_search_prompt() -> str:
    # Use a smaller subset of roles to keep the prompt focused
    priority_roles = [
        "Machine Learning Engineer", "AI Engineer", "Data Scientist",
        "Software Engineer new grad", "NLP Engineer", "MLOps Engineer",
        "Data Analyst", "Full Stack Developer", "Python Developer",
        "Computer Vision Engineer", "Deep Learning Engineer",
        "Generative AI Engineer", "Junior Software Engineer",
        "Data Engineer", "Backend Engineer"
    ]
    roles_str = ", ".join(priority_roles)

    return f"""
Search the web RIGHT NOW for software and AI/ML job postings.

Search these job boards: LinkedIn Jobs, Indeed, Handshake, Wellfound, Glassdoor, Dice.

Search for these roles: {roles_str}

Search in: San Francisco CA, Seattle WA, New York NY, Austin TX, Boston MA,
Los Angeles CA, Remote, and any other US city.

Only include jobs requiring 0-{MAX_EXPERIENCE_YEARS} years experience, internships, 
new grad roles, or junior positions. Skip anything requiring 5+ years.

Return a JSON array. Each item must have exactly these fields:
- company (string)
- title (string)  
- location (string)
- link (string, direct URL to job posting)
- source (string, e.g. "LinkedIn" or "Indeed")
- job_type (string, e.g. "full-time" or "internship")
- skills (string, comma separated skills from job description)
- experience (string, e.g. "0-2 years" or "new grad")
- description (string, job description text)
- asks_sensitive_questions (boolean)
- sensitive_question (string, empty if none)

Example format:
[
  {{
    "company": "Google",
    "title": "Machine Learning Engineer",
    "location": "Mountain View, CA",
    "link": "https://careers.google.com/jobs/...",
    "source": "company career page",
    "job_type": "full-time",
    "skills": "Python, TensorFlow, PyTorch",
    "experience": "0-2 years",
    "description": "We are looking for an ML engineer...",
    "asks_sensitive_questions": false,
    "sensitive_question": ""
  }}
]

Search now and return as many real current job postings as you can find (aim for 20-50).
Return ONLY the JSON array, nothing else.
"""


def search_jobs() -> list[dict]:
    """
    Call Claude with web search and return a list of job dicts.
    Uses multiple fallback strategies to extract jobs from the response.
    """
    logger.info("Starting job search via Claude web search...")

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=8192,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search"
            }],
            messages=[{
                "role": "user",
                "content": _build_search_prompt()
            }],
        )

        # Log what we got back for debugging
        logger.info(f"Response has {len(response.content)} content blocks")
        for i, block in enumerate(response.content):
            logger.info(f"  Block {i}: type={block.type}")

        # Collect all text from response
        full_text = ""
        for block in response.content:
            if hasattr(block, "type"):
                if block.type == "text":
                    full_text += block.text
                    logger.info(f"  Text block length: {len(block.text)} chars")
                elif block.type == "tool_result":
                    # Sometimes search results come back as tool_result
                    if hasattr(block, "content"):
                        for item in block.content:
                            if hasattr(item, "text"):
                                full_text += item.text

        if not full_text.strip():
            logger.warning("Claude returned no text. Full response content blocks:")
            for block in response.content:
                logger.warning(f"  {block}")
            return []

        logger.info(f"Total text length: {len(full_text)} chars")
        logger.info(f"First 200 chars: {full_text[:200]}")

        jobs = _extract_json_from_text(full_text)

        if not jobs:
            logger.warning("Could not extract jobs from response.")
            logger.warning(f"Full response text: {full_text[:1000]}")
            return []

        # Validate each job has required fields
        valid_jobs = []
        required_fields = ["company", "title", "location", "link", "description"]
        for job in jobs:
            if isinstance(job, dict) and all(job.get(f) for f in required_fields):
                valid_jobs.append(job)
            else:
                logger.debug(f"Skipping invalid job entry: {job}")

        logger.info(f"Found {len(valid_jobs)} valid jobs from search.")
        return valid_jobs

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in job search: {e}", exc_info=True)
        return []
