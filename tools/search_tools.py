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


def search_jobs(
    query: str | None = None,
    location: str | None = None,
    countries: str | None = None,
    remote_type: str | None = None,
    seniority: str | None = None,
    skills: list[str] | None = None,
    per_page: int = 10,
) -> dict:
    """Search JobDataLake by free-text query and/or structured filters.

    query is JobDataLake's single text-search param - it can be tight
    keywords, a descriptive natural-language phrase, or omitted/"*" to skip
    text matching entirely and rely only on the structured filters
    (location, countries, remote_type, seniority, skills).

    Returns {"jobs": [...], "error": str | None}.
    """
    params: dict = {"query": query or "*", "per_page": per_page}
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

    result = get_jobs(params)
    return {"jobs": [_normalize_job(j) for j in result["jobs"]], "error": result["error"]}
