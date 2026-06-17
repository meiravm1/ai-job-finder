"""Search Agent: finds job postings on JobDataLake matching a free-text request."""

from agents.agent_loop import run_agent
from tools.search_tools import search_jobs_by_keyword, search_jobs_by_semantic_query

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
- search_jobs_by_keyword(query, location, per_page): keyword search.
- search_jobs_by_semantic_query(semantic_query, per_page): natural-language
  semantic search.

# Process
1. Read the user's free-text request carefully.
2. Decide whether a keyword search or a semantic/natural-language search is
   more likely to return relevant results (or use both and merge results).
3. Call the appropriate tool(s) with parameters derived from the user's
   request (e.g., role keywords, location, "remote" if mentioned).
4. If no results are returned, retry once with broader/relaxed parameters
   (e.g., remove location filter, simplify keywords).
5. Deduplicate jobs (by title+company+location) before returning results.
6. Return up to 3 jobs in the required Output Format.

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
"""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_jobs_by_keyword",
            "description": "Search JobDataLake for jobs matching a keyword query, optionally narrowed by location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword search query, e.g. 'python developer'"},
                    "location": {"type": "string", "description": "Location to search in, e.g. 'Tel Aviv'"},
                    "per_page": {"type": "integer", "description": "Number of results to request (default 3)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_jobs_by_semantic_query",
            "description": "Search JobDataLake using a natural-language description of the desired job.",
            "parameters": {
                "type": "object",
                "properties": {
                    "semantic_query": {"type": "string", "description": "Free-text description of the desired job"},
                    "location": {"type": "string", "description": "Location or country to filter by, e.g. 'USA', 'New York'"},
                    "per_page": {"type": "integer", "description": "Number of results to request (default 3)"},
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


def run_search_agent(user_prompt: str, provider: str = "gemini") -> dict:
    """Run the Search Agent on a free-text user prompt and return its JSON result."""
    return run_agent(SYSTEM_PROMPT, TOOL_SCHEMAS, TOOL_FUNCTIONS, user_prompt, provider=provider, agent_name="Search Agent")
