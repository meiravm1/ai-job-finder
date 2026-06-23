"""Plain-Python glue that runs the Profile and Search agents, then ranks jobs deterministically."""

from agents.profile_agent import run_profile_agent
from agents.search_agent import run_search_agent
from tools.matching_tools import DEFAULT_MAX_JOBS_TO_SCORE, rank_jobs_against_profile


def run_pipeline(
    user_prompt: str,
    resume_text: str | None = None,
    provider: str = "gemini",
    max_results: int = DEFAULT_MAX_JOBS_TO_SCORE,
) -> dict:
    """Search for jobs matching user_prompt, then rank them against the candidate profile.

    The candidate profile is extracted once, via the Profile Agent, from
    user_prompt + resume_text before anything else runs - both are free
    text, so an LLM is used instead of regex. The profile is then used both
    to enrich the Search Agent's query and to score results afterward.
    provider selects the LLM backend used by the Profile and Search agents;
    ranking itself is rule-based and does not use an LLM. max_results caps
    how many jobs the Search Agent fetches and how many get ranked.
    """
    profile = run_profile_agent(user_prompt, resume_text, provider=provider)

    search_result = run_search_agent(user_prompt, profile=profile, provider=provider, max_results=max_results)

    if not search_result.get("jobs"):
        return {
            "profile_used": profile,
            "ranked_jobs": [],
            "errors": search_result.get("errors", []),
        }

    return rank_jobs_against_profile(profile, search_result["jobs"], max_jobs=max_results)
