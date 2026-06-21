"""Tests for the deterministic ranking helper (tools/matching_tools.py)."""

from tools.matching_tools import normalize_user_profile, rank_jobs_against_profile

JOBS = [
    {"title": "Senior Java Engineer", "company": "Beta", "location": "Haifa",
     "remote_type": "on-site", "seniority": "senior", "skills": ["java"]},
    {"title": "Junior Python Developer", "company": "Acme", "location": "Tel Aviv",
     "remote_type": "remote", "seniority": "junior", "skills": ["python", "sql"]},
    {"title": "Mid Python Developer", "company": "Gamma", "location": "Haifa",
     "remote_type": "on-site", "seniority": "mid", "skills": ["python"]},
    {"title": "Data Analyst", "company": "Delta", "location": "Remote",
     "remote_type": "remote", "seniority": "junior", "skills": ["excel"]},
]

PROFILE = normalize_user_profile("junior python developer, remote, 2 years experience")


def test_rank_jobs_against_profile_sorts_descending_by_score():
    result = rank_jobs_against_profile(PROFILE, JOBS)

    scores = [job["matching_score"] for job in result["ranked_jobs"]]
    assert scores == sorted(scores, reverse=True)


def test_rank_jobs_against_profile_caps_at_max_jobs():
    result = rank_jobs_against_profile(PROFILE, JOBS, max_jobs=3)

    assert len(result["ranked_jobs"]) == 3


def test_rank_jobs_against_profile_defaults_to_ten():
    result = rank_jobs_against_profile(PROFILE, JOBS)

    assert len(result["ranked_jobs"]) == len(JOBS)


def test_rank_jobs_against_profile_empty_jobs_returns_empty_ranked_jobs():
    result = rank_jobs_against_profile(PROFILE, [])

    assert result == {"profile_used": PROFILE, "ranked_jobs": [], "errors": []}


def test_rank_jobs_against_profile_preserves_job_fields():
    result = rank_jobs_against_profile(PROFILE, JOBS[:1])

    ranked = result["ranked_jobs"][0]
    assert ranked["title"] == JOBS[0]["title"]
    assert ranked["company"] == JOBS[0]["company"]
    assert "matching_score" in ranked
    assert "match_reason" in ranked
