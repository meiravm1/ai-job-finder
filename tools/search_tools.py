"""Tool functions exposed to the Search Agent."""

from tools.jobdatalake_client import get_jobs


def _normalize_job(raw: dict) -> dict:
    """Map a raw JobDataLake job object onto the agent's job schema."""
    return {
        "title": raw.get("title", "Unknown title"),
        "company": raw.get("company", "Unknown company"),
        "location": raw.get("location", "Unknown location"),
        "remote_type": raw.get("remote_type"),
        "seniority": raw.get("seniority"),
        "salary": raw.get("salary"),
        "skills": raw.get("skills") or [],
        "employment_type": raw.get("employment_type"),
        "url": raw.get("url") or raw.get("job_url"),
    }


def search_jobs_by_keyword(query: str, location: str | None = None, per_page: int = 3) -> dict:
    """Search JobDataLake by keyword, optionally folding location into the query.

    Returns {"jobs": [...], "error": str | None}.
    """
    q = query
    if location:
        q = f"{query} {location}"

    result = get_jobs({"q": q, "per_page": per_page})
    return {"jobs": [_normalize_job(j) for j in result["jobs"]], "error": result["error"]}


def search_jobs_by_semantic_query(semantic_query: str, per_page: int = 3) -> dict:
    """Search JobDataLake using a natural-language semantic query.

    Returns {"jobs": [...], "error": str | None}.
    """
    result = get_jobs({"semantic_query": semantic_query, "per_page": per_page})
    return {"jobs": [_normalize_job(j) for j in result["jobs"]], "error": result["error"]}
