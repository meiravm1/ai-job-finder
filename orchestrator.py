"""Plain-Python glue that runs the Search Agent then the Matching Agent."""

from agents.matching_agent import run_matching_agent
from agents.search_agent import run_search_agent


def run_pipeline(user_prompt: str, resume_text: str | None = None, provider: str = "gemini") -> dict:
    """Search for jobs matching user_prompt, then rank them against the candidate profile.

    provider selects the LLM backend used by both agents (e.g. "gemini", "groq").
    """
    search_result = run_search_agent(user_prompt, provider=provider)

    if not search_result.get("jobs"):
        return {
            "profile_used": {},
            "ranked_jobs": [],
            "errors": search_result.get("errors", []),
        }

    return run_matching_agent(user_prompt, search_result["jobs"], resume_text=resume_text, provider=provider)
