"""
daily_summary.py
─────────────────────────────────────────────
Uses Claude to generate intelligent recommendations
based on today's application run statistics.
"""

import anthropic
import logging
from config import ANTHROPIC_API_KEY, PROFILE

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_recommendations(stats: dict) -> str:
    """
    Ask Claude to analyze today's stats and suggest tomorrow's strategy.
    Returns a plain text recommendation string.
    """
    try:
        prompt = f"""
Today's job application run for {PROFILE['name']} is complete.

Stats:
- Jobs searched: {stats.get('searched', 0)}
- Applications submitted: {stats.get('applied', 0)}
- Pending review: {stats.get('pending', 0)}
- Silently skipped (score < 5 or 5+ years exp): {stats.get('skipped', 0)}
- Duplicates avoided: {stats.get('duplicates', 0)}
- Top companies applied to: {', '.join(stats.get('top_companies', []))}
- Top roles applied to: {', '.join(stats.get('top_roles', []))}
- Top locations: {', '.join(stats.get('top_locations', []))}

Based on these stats, write 3-4 short bullet point recommendations for tomorrow's run.
Focus on: which role categories to prioritize, which locations had good results,
whether the search volume needs adjustment, and any patterns to exploit.
Keep it under 100 words total. Plain text, no JSON.
"""
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    except Exception as e:
        logger.error(f"Could not generate recommendations: {e}")
        return "Continue with current strategy. Review pending jobs manually."
