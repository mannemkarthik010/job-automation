"""
resume_matcher.py
─────────────────────────────────────────────
Uses Claude to score each job against the applicant's resume
and generate a humanized cover letter when the score is high enough.
"""

import anthropic
import json
import logging
import re
from config import (
    ANTHROPIC_API_KEY,
    PROFILE,
    MIN_MATCH_SCORE,
    MAX_EXPERIENCE_YEARS,
)

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_match_prompt(job: dict, resume_text: str) -> str:
    return f"""
You are evaluating a job posting for {PROFILE['name']}.

APPLICANT PROFILE:
- Degree: {PROFILE['degree']} at {PROFILE['university']}
- Graduating: {PROFILE['graduation']}
- GPA: {PROFILE['gpa']}
- Work Authorization: {PROFILE['work_auth']}
- Needs Sponsorship: {PROFILE['needs_sponsorship']}
- Willing to Relocate: {PROFILE['relocate']}

RESUME:
{resume_text}

JOB POSTING:
Company:      {job.get('company', '')}
Title:        {job.get('title', '')}
Location:     {job.get('location', '')}
Type:         {job.get('job_type', '')}
Experience:   {job.get('experience', '')}
Skills:       {job.get('skills', '')}
Description:
{job.get('description', '')}

TASK 1 — SCORE (mandatory):
Score the match from 1-10 based on:
  - Technical skills overlap (35%)
  - Project relevance (25%)
  - Education match (15%)
  - Experience level fit (15%)
  - Eligibility (10%)

TASK 2 — EXPERIENCE CHECK:
If the role explicitly requires {MAX_EXPERIENCE_YEARS + 1}+ years of full-time
professional experience, set "exceeds_experience": true.

TASK 3 — COVER LETTER (only if score >= {MIN_MATCH_SCORE} and not exceeds_experience):
Write a cover letter that:
- Sounds like {PROFILE['name']} wrote it personally after researching the company
- Opens with something specific about the company's work or product (NOT "I am excited to apply")
- Mentions 2-3 of the applicant's most relevant projects with specific details
- Explains why THIS company specifically interests the applicant
- Closes confidently in 1 sentence
- Is under 350 words, 3-4 paragraphs
- Uses ZERO of these banned phrases: "excited to apply", "leverage", "passionate",
  "dynamic team", "synergy", "quick learner", "team player", "I am writing to express",
  "thank you for your time and consideration", "I would be a great fit"
- Sounds warm, specific, and fully human — no AI tells whatsoever

TASK 4 — RESUME SUMMARY (only if score >= {MIN_MATCH_SCORE} and not exceeds_experience):
Write a 2-3 sentence professional summary customized for this specific role.
Use keywords from the job description naturally.

Return ONLY this JSON (no markdown, no explanation):
{{
  "score": 7,
  "exceeds_experience": false,
  "apply": true,
  "match_reason": "Strong Python and ML skills match; CNN and recommendation system projects directly relevant",
  "cover_letter": "full cover letter text here",
  "resume_summary": "Customized 2-3 sentence summary here",
  "pending_reason": "",
  "pending_question": ""
}}

Set "apply" to false (and fill pending_reason/pending_question) if:
- The job asks about visa sponsorship in a non-standard way
- The job asks for salary expectations
- The job asks about security clearance
- Any eligibility question cannot be answered from the profile above
Otherwise set "apply" to true for all jobs with score >= {MIN_MATCH_SCORE}.
"""


def evaluate_job(job: dict, resume_text: str) -> dict:
    """
    Score a job and generate cover letter + resume summary.
    Returns a result dict with keys: score, apply, cover_letter,
    resume_summary, match_reason, exceeds_experience, pending_reason,
    pending_question.
    """
    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": _build_match_prompt(job, resume_text)
            }],
        )

        raw = response.content[0].text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()

        # Find JSON object
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning(f"No JSON in evaluator response for {job.get('title')} at {job.get('company')}")
            return _default_result()

        result = json.loads(raw[start:end])

        # Safety defaults for missing keys
        result.setdefault("score", 0)
        result.setdefault("apply", False)
        result.setdefault("exceeds_experience", False)
        result.setdefault("cover_letter", "")
        result.setdefault("resume_summary", "")
        result.setdefault("match_reason", "")
        result.setdefault("pending_reason", "")
        result.setdefault("pending_question", "")

        # Force apply=False if score is below threshold or exceeds experience
        if result["score"] < MIN_MATCH_SCORE or result["exceeds_experience"]:
            result["apply"] = False

        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error evaluating {job.get('title')}: {e}")
        return _default_result()
    except Exception as e:
        logger.error(f"Error evaluating {job.get('title')}: {e}")
        return _default_result()


def _default_result() -> dict:
    return {
        "score": 0,
        "apply": False,
        "exceeds_experience": False,
        "cover_letter": "",
        "resume_summary": "",
        "match_reason": "Evaluation failed",
        "pending_reason": "",
        "pending_question": "",
    }
