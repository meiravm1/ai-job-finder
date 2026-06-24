"""Tool functions exposed to the Matching/Rating Agent.

Both tools are deterministic, pure-Python helpers (no external API calls),
which keeps scoring reproducible and easy for students to test and tweak.
"""

import re

KNOWN_SKILLS = [
    "python", "java", "javascript", "typescript", "react", "angular", "vue",
    "node", "node.js", "sql", "nosql", "mongodb", "postgres", "postgresql",
    "aws", "azure", "gcp", "docker", "kubernetes", "django", "flask",
    "fastapi", "c++", "c#", "go", "golang", "rust", "html", "css", "excel",
    "tableau", "power bi", "machine learning", "data analysis", "pandas",
    "numpy", "spark", "hadoop", "git",
]

SENIORITY_KEYWORDS = {
    "entry level": "junior",
    "entry-level": "junior",
    "junior": "junior",
    "jr": "junior",
    "mid level": "mid",
    "mid-level": "mid",
    "mid": "mid",
    "senior": "senior",
    "sr": "senior",
    "lead": "lead",
    "principal": "lead",
}

REMOTE_KEYWORDS = {
    "remote": "remote",
    "hybrid": "hybrid",
    "on-site": "on-site",
    "onsite": "on-site",
    "in-office": "on-site",
}

ROLE_PATTERN = re.compile(
    r"([a-zA-Z][a-zA-Z\s\-/]*?\b(?:developer|engineer|analyst|designer|manager|scientist|architect|administrator))",
    re.IGNORECASE,
)
LOCATION_PATTERN = re.compile(r"\bin\s+([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)")
YEARS_PATTERN = re.compile(r"(\d+)\+?\s*years?", re.IGNORECASE)


def normalize_user_profile(free_text: str, resume_text: str | None = None) -> dict:
    """Extract a structured candidate profile from free text and optional resume text.

    Returns a dict with keys: role, location, seniority, remote_preference,
    years_experience, skills.
    """
    profile = _extract_profile(free_text)

    if resume_text:
        resume_profile = _extract_profile(resume_text)
        for key in ("role", "location", "seniority", "remote_preference", "years_experience"):
            if profile.get(key) is None and resume_profile.get(key) is not None:
                profile[key] = resume_profile[key]
        merged_skills = set(profile["skills"]) | set(resume_profile["skills"])
        profile["skills"] = sorted(merged_skills)

    return profile


def _extract_profile(text: str) -> dict:
    lower = text.lower()

    role_match = ROLE_PATTERN.search(text)
    role = role_match.group(1).strip() if role_match else None

    location_match = LOCATION_PATTERN.search(text)
    location = location_match.group(1).strip() if location_match else None

    seniority = None
    for keyword, level in SENIORITY_KEYWORDS.items():
        if keyword in lower:
            seniority = level
            break

    remote_preference = None
    for keyword, value in REMOTE_KEYWORDS.items():
        if keyword in lower:
            remote_preference = value
            break

    years_match = YEARS_PATTERN.search(text)
    years_experience = int(years_match.group(1)) if years_match else None

    skills = sorted({skill for skill in KNOWN_SKILLS if skill in lower})

    return {
        "role": role,
        "location": location,
        "seniority": seniority,
        "remote_preference": remote_preference,
        "years_experience": years_experience,
        "skills": skills,
    }


def score_job_against_profile(job: dict, profile: dict) -> dict:
    """Compute a 0-100 matching score for a job against a candidate profile.

    Returns {"matching_score": int, "match_reason": str}.
    """
    score = 0
    reasons = []

    title = (job.get("title") or "").lower()
    if profile.get("role") and profile["role"].lower() in title:
        score += 30
        reasons.append(f"title matches desired role '{profile['role']}'")
    elif profile.get("role") and job.get("role_match_signal"):
        signal = job["role_match_signal"]
        score += round(30 * signal)
        reasons.append(f"title is a partial match for role '{profile['role']}' (similarity {signal:.2f})")

    job_remote = (job.get("remote_type") or "").lower()
    job_location = (job.get("location") or "").lower()
    if profile.get("remote_preference") == "remote" and "remote" in job_remote:
        score += 20
        reasons.append("offers remote work as requested")
    elif profile.get("location") and profile["location"].lower() in job_location:
        score += 20
        reasons.append(f"location matches '{profile['location']}'")

    job_seniority = (job.get("seniority") or "").lower()
    if profile.get("seniority") and profile["seniority"] == job_seniority:
        score += 20
        reasons.append(f"seniority matches '{profile['seniority']}'")

    profile_skills = set(profile.get("skills") or [])
    job_skills = {s.lower() for s in (job.get("skills") or [])}
    if profile_skills:
        overlap = profile_skills & job_skills
        if overlap:
            score += round(30 * len(overlap) / len(profile_skills))
            reasons.append(f"shares skills: {', '.join(sorted(overlap))}")

    score = max(0, min(100, score))
    match_reason = "; ".join(reasons) if reasons else "Limited overlap with the candidate's stated profile."

    return {"matching_score": score, "match_reason": match_reason}


DEFAULT_MAX_JOBS_TO_SCORE = 5


def rank_jobs_against_profile(profile: dict, jobs: list[dict], max_jobs: int = DEFAULT_MAX_JOBS_TO_SCORE) -> dict:
    """Score and rank jobs against an already-extracted candidate profile.

    Pure-Python replacement for the old LLM-orchestrated Matching Agent.
    Scores at most max_jobs jobs and returns them sorted by matching_score
    descending.
    """
    ranked_jobs = [{**job, **score_job_against_profile(job, profile)} for job in jobs[:max_jobs]]
    ranked_jobs.sort(key=lambda j: j["matching_score"], reverse=True)

    return {"profile_used": profile, "ranked_jobs": ranked_jobs, "errors": []}
