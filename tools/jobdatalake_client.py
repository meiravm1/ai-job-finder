"""Thin HTTP client for the JobDataLake API (https://api.jobdatalake.com)."""

import os

import requests

BASE_URL = "https://api.jobdatalake.com/v1/jobs"
TIMEOUT_SECONDS = 10


def get_jobs(params: dict) -> dict:
    """Call the JobDataLake /v1/jobs endpoint and return a parsed dict.

    On any error (missing API key, network error, bad status code), returns
    a dict of the form {"jobs": [], "error": "<message>"} instead of raising,
    so calling tools can surface this gracefully to the agent.
    """
    api_key = os.environ.get("JOBDATALAKE_API_KEY")
    if not api_key:
        return {"jobs": [], "error": "JOBDATALAKE_API_KEY is not set"}

    headers = {"X-API-Key": api_key}

    try:
        response = requests.get(BASE_URL, headers=headers, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {"jobs": [], "error": f"JobDataLake request failed: {exc}"}

    try:
        data = response.json()
    except ValueError:
        return {"jobs": [], "error": "JobDataLake response was not valid JSON"}

    # The API may nest the job list under "jobs", "data", or "results" -
    # check defensively and fall back to an empty list.
    jobs = data.get("jobs") or data.get("data") or data.get("results") or []
    if not isinstance(jobs, list):
        jobs = []

    return {"jobs": jobs, "error": None}
