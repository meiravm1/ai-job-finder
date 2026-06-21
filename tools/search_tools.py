"""Tool functions exposed to the Search Agent."""

from tools.jobdatalake_client import get_jobs


def _coerce_location(value) -> str:
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("city", "state", "country", "region") if value.get(k)]
        return ", ".join(parts) if parts else "Unknown location"
    if isinstance(value, list):
        parts = [_coerce_location(v) for v in value if v]
        parts = [p for p in parts if p and p != "Unknown location"]
        return ", ".join(parts) if parts else "Unknown location"
    return value or "Unknown location"


def _normalize_job(raw: dict) -> dict:
    """Map a raw JobDataLake job object onto the agent's job schema."""
    seniority = raw.get("seniority")
    if isinstance(seniority, list):
        seniority = seniority[0] if seniority else None

    # JobDataLake returns a "locations" array of free-text strings (e.g.
    # ["San Francisco, CA", "Remote"]); "location" is kept as a fallback
    # for older/alternate response shapes.
    location = raw.get("locations") or raw.get("location")

    return {
        "title": raw.get("title", "Unknown title"),
        "company": raw.get("company_name") or raw.get("company") or "Unknown company",
        "location": _coerce_location(location),
        "remote_type": raw.get("remote_type"),
        "seniority": seniority,
        "salary": raw.get("salary"),
        "skills": raw.get("skills") or [],
        "employment_type": raw.get("employment_type"),
        "url": raw.get("url") or raw.get("job_url"),
    }


def _build_params(
    query: str,
    location: str | None,
    countries: str | None,
    remote_type: str | None,
    seniority: str | None,
    skills: list[str] | None,
    per_page: int,
) -> dict:
    params: dict = {"query": query, "per_page": per_page}
    if location:
        params["location"] = location
    if countries:
        params["countries"] = countries
    if remote_type:
        params["remoteType"] = remote_type
    if seniority:
        params["seniority"] = seniority
    if skills:
        params["skills"] = ",".join(skills)
    return params


def search_jobs_by_keyword(
    query: str,
    location: str | None = None,
    countries: str | None = None,
    remote_type: str | None = None,
    seniority: str | None = None,
    skills: list[str] | None = None,
    per_page: int = 10,
) -> dict:
    """Search JobDataLake by keyword, optionally narrowed by location/countries/
    remote type/seniority/skills.

    Returns {"jobs": [...], "error": str | None}.
    """
    params = _build_params(query, location, countries, remote_type, seniority, skills, per_page)
    result = get_jobs(params)
    return {"jobs": [_normalize_job(j) for j in result["jobs"]], "error": result["error"]}


def search_jobs_by_semantic_query(
    semantic_query: str,
    location: str | None = None,
    countries: str | None = None,
    remote_type: str | None = None,
    seniority: str | None = None,
    skills: list[str] | None = None,
    per_page: int = 10,
) -> dict:
    """Search JobDataLake using a natural-language description of the desired job.

    JobDataLake has a single free-text "query" param (no separate semantic
    endpoint/param), so this sends the natural-language phrase as the query
    itself - this tool differs from search_jobs_by_keyword in the shape of
    text the caller passes in (a descriptive phrase vs. tight keywords), not
    in the underlying API call.

    Returns {"jobs": [...], "error": str | None}.
    """
    params = _build_params(semantic_query, location, countries, remote_type, seniority, skills, per_page)
    result = get_jobs(params)
    return {"jobs": [_normalize_job(j) for j in result["jobs"]], "error": result["error"]}
