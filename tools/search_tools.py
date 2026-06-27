"""Tool functions exposed to the Search Agent."""

from tools.google_news_client import search_news
from tools.jobdatalake_client import get_jobs


def _coerce_location(value) -> str:
    """Flatten JobDataLake's location field (dict, list, or string) into one string.

    Falls back to "Unknown location" rather than None/empty - search_company
    folds this straight into its query, so an empty value would search news
    for the company name alone instead of failing loudly.
    """
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
        "skills": raw.get("required_skills") or [],
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


def search_company(company_name: str, location: str | None = None, company_domain: str | None = None) -> dict:
    """Look up a company via Google News for a notable, interesting fact about it.

    company_name is quoted in the query to force exact-phrase matching -
    without quotes, Google News ANDs loose words together and a company
    name that's also a common word (e.g. "Hover") pulls in unrelated noise.
    company_domain, if given (the agent's own site, not a generic job
    board), is the strongest disambiguator - a literal domain string rarely
    appears in unrelated content, so it's tried first and alone if needed.
    location is a weaker disambiguator and tried after domain.

    Returns {"results": [{"title", "source", "published", "url"}, ...], "error": str | None}.
    The agent reads the raw headlines to judge whether anything notable is
    actually present - this tool does no interpretation of its own.

    Google News treats the query as an implicit AND of every word, so an
    over-qualified query can return nothing even when real results exist
    for a looser version of the same query. Candidate queries are tried in
    order from most to least specific, returning the first that finds
    anything (or the last, plain one, if all come up empty).
    """
    candidates = []
    if company_domain:
        candidates.append(f'"{company_name}" "{company_domain}" latest interesting fact')
        candidates.append(f'"{company_domain}" latest interesting fact')
    if location:
        candidates.append(f'"{company_name}" {location} latest interesting fact')
    candidates.append(f'"{company_name}" latest interesting fact')

    for query in candidates[:-1]:
        result = search_news(query, max_results=5)
        if result["results"] or result["error"]:
            return result

    return search_news(candidates[-1], max_results=5)
