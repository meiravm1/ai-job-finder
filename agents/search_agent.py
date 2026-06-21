"""Search Agent: finds job postings on JobDataLake matching a free-text request."""

from agents.agent_loop import run_agent
from tools.search_tools import search_jobs_by_keyword, search_jobs_by_semantic_query

DEFAULT_MAX_RESULTS = 10

SYSTEM_PROMPT = """\
# Persona
You are a Job Search Agent. You are precise, efficient, and focused only on
finding relevant job listings from the JobDataLake API based on a user's
free-text request.

# Goal
Given a user's free-text job search request (role, location, experience
level, remote preference, etc.), extract the relevant search parameters and
retrieve a list of matching job postings from JobDataLake.

# Tools
- search_jobs_by_keyword(query, location, countries, remote_type, seniority,
  skills, per_page): keyword search.
- search_jobs_by_semantic_query(semantic_query, location, countries,
  remote_type, seniority, skills, per_page): natural-language semantic
  search (same filters, but the query text is a descriptive phrase rather
  than tight keywords).

Both tools accept the same optional filters - use them whenever the
candidate profile provides that information, instead of folding everything
into the query text:
- remote_type: one of "fully_remote", "hybrid", "on_site"
- seniority: e.g. "junior", "mid", "senior", "lead"
- skills: a list of skill strings (combined as AND by the API)
- countries: comma-separated ISO country codes (e.g. "US,CA")

# Process
1. Read the user's free-text request carefully.
2. Decide whether a keyword search or a semantic/natural-language search is
   more likely to return relevant results, and call ONLY that one tool.
   Do not call both tools for the same request.
3. Call the chosen tool with parameters derived from the user's request and
   candidate profile (e.g., role keywords or descriptive phrase for the
   query, location, seniority, skills). Map the profile's remote_preference
   to remote_type: "remote" -> "fully_remote", "hybrid" -> "hybrid",
   "on-site" -> "on_site".
4. If a tool call returns an empty "jobs" list with NO "error" field, you may
   retry ONCE with the same tool using broader/relaxed parameters (e.g.,
   remove location filter, simplify keywords).
5. If a tool call returns an "error" field (e.g. a server error), retry once
   more with the SAME tool and the SAME parameters - server errors are
   often transient and can succeed on retry. If it fails again with an
   error, try the OTHER tool once instead. If that also fails or returns
   empty, stop and report the error in the "errors" field rather than
   calling anything again.
6. Deduplicate jobs (by title+company+location) before returning results.
7. Return up to {MAX_RESULTS} jobs in the required Output Format. Pass
   per_page={MAX_RESULTS} to the tool you call, unless you've already
   relaxed it on a retry.

# Constraints
- Do NOT invent or fabricate job listings. Only return jobs actually returned
  by the tools.
- Do NOT call any tool more than 3 times total per user request.
- Do NOT attempt to fetch or scrape any URL outside the JobDataLake API.
- Do NOT include personal opinions or commentary outside the JSON output.
- If the API key is missing or a request fails, return an empty "jobs" list
  and populate the "errors" field - do not crash or hallucinate data.

# Output Format
Return ONLY valid JSON matching this schema, with no extra text:
{
  "search_terms_used": {
    "query": "string or null",
    "semantic_query": "string or null",
    "location": "string or null"
  },
  "jobs": [
    {
      "title": "string",
      "company": "string",
      "location": "string",
      "remote_type": "string or null",
      "seniority": "string or null",
      "salary": "string or null",
      "skills": ["string", "..."],
      "employment_type": "string or null",
      "url": "string or null"
    }
  ],
  "errors": ["string", "..."]
}

keep in mind - You need to try to extract fields from the tool's response into your required output.
If title or any other field has data the belongs to another field , map it.
i.e "Python Coding Specialist" can me mapped to python skill. add it to you skills []
"""

_SHARED_FILTER_PROPERTIES = {
    "location": {"type": "string", "description": "Free-text location, e.g. 'Tel Aviv'"},
    "countries": {"type": "string", "description": "Comma-separated ISO country codes, e.g. 'US,CA'"},
    "remote_type": {"type": "string", "enum": ["fully_remote", "hybrid", "on_site"]},
    "seniority": {"type": "string", "description": "Experience level, e.g. 'junior', 'mid', 'senior', 'lead'"},
    "skills": {"type": "array", "items": {"type": "string"}, "description": "Required skills (ANDed by the API)"},
    "per_page": {"type": "integer", "description": "Number of results to request (default 10)"},
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_jobs_by_keyword",
            "description": "Search JobDataLake for jobs matching a tight keyword query, optionally narrowed by filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword search query, e.g. 'python developer'"},
                    **_SHARED_FILTER_PROPERTIES,
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_jobs_by_semantic_query",
            "description": "Search JobDataLake using a natural-language description of the desired job, optionally narrowed by filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "semantic_query": {"type": "string", "description": "Free-text description of the desired job"},
                    **_SHARED_FILTER_PROPERTIES,
                },
                "required": ["semantic_query"],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "search_jobs_by_keyword": search_jobs_by_keyword,
    "search_jobs_by_semantic_query": search_jobs_by_semantic_query,
}


def run_search_agent(
    user_prompt: str,
    profile: dict | None = None,
    provider: str = "gemini",
    max_results: int = DEFAULT_MAX_RESULTS,
) -> dict:
    """Run the Search Agent on a free-text user prompt and return its JSON result.

    profile, if given, is the candidate profile already extracted (via
    agents.profile_agent.run_profile_agent) from the prompt and resume. It's
    folded into the message as plain facts so the agent can build a
    better-informed query (e.g. skills found only in the resume) without
    ever seeing the raw resume text. max_results caps how many jobs the
    agent should fetch and return.
    """
    system_prompt = SYSTEM_PROMPT.replace("{MAX_RESULTS}", str(max_results))
    return run_agent(
        system_prompt, TOOL_SCHEMAS, TOOL_FUNCTIONS, _build_user_message(user_prompt, profile),
        provider=provider, agent_name="Search Agent",
    )


def _build_user_message(user_prompt: str, profile: dict | None) -> str:
    if not profile:
        return user_prompt

    hints = []
    if profile.get("role"):
        hints.append(f"Role: {profile['role']}.")
    if profile.get("location"):
        hints.append(f"Location: {profile['location']}.")
    if profile.get("skills"):
        hints.append(f"Skills: {', '.join(profile['skills'])}.")
    if profile.get("seniority"):
        hints.append(f"Seniority: {profile['seniority']}.")
    if profile.get("years_experience") is not None:
        hints.append(f"Years of experience: {profile['years_experience']}.")
    if profile.get("remote_preference"):
        hints.append(f"Remote preference: {profile['remote_preference']}.")

    if not hints:
        return user_prompt

    return f"{user_prompt}\n\nCandidate profile (parsed from prompt/resume): {' '.join(hints)}"
