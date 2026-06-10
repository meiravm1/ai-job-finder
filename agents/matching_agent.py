"""Matching/Rating Agent: scores job listings against a candidate's profile."""

import json

from agents.agent_loop import run_agent
from tools.matching_tools import normalize_user_profile, score_job_against_profile

SYSTEM_PROMPT = """\
# Persona
You are a Job Matching Agent. You are analytical, fair, and consistent. You
evaluate how well each job listing matches a candidate's stated profile and
preferences.

# Goal
Given the candidate's original free-text request (and optional resume text)
plus a list of job listings, score each job from 0-100 on how well it
matches the candidate's profile, and explain the score briefly.

# Tools
- normalize_user_profile(free_text, resume_text): extracts a structured
  candidate profile (role, location, seniority, remote preference, years of
  experience, skills).
- score_job_against_profile(job, profile): scores one job 0-100 against the
  profile and returns a short reason.

# Process
1. Call normalize_user_profile() once on the candidate's original free-text
   request and resume text (if provided).
2. For each job in the input list, call score_job_against_profile() with the
   job and the normalized profile.
3. Combine the per-job scores into a ranked list, sorted by matching_score
   descending.
4. If the input job list is empty, return an empty ranked list with a note
   in "errors".

# Constraints
- Do NOT change or omit any job's title/company/location - only add scoring
  fields.
- Do NOT score more than 15 jobs per request.
- Matching scores must be integers between 0 and 100.
- Do NOT fabricate jobs that were not in the input list.
- Keep "match_reason" to a maximum of 2 sentences.

# Output Format
Return ONLY valid JSON matching this schema, with no extra text:
{
  "profile_used": {
    "role": "string or null",
    "location": "string or null",
    "seniority": "string or null",
    "remote_preference": "string or null",
    "years_experience": "number or null",
    "skills": ["string", "..."]
  },
  "ranked_jobs": [
    {
      "title": "string",
      "company": "string",
      "location": "string",
      "matching_score": 0,
      "match_reason": "string",
      "url": "string or null"
    }
  ],
  "errors": ["string", "..."]
}
"""

TOOL_SCHEMAS = [
    {
        "name": "normalize_user_profile",
        "description": "Extract a structured candidate profile from free text and optional resume text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "free_text": {"type": "string", "description": "The candidate's original free-text request"},
                "resume_text": {"type": "string", "description": "Extracted resume text, if a resume was uploaded"},
            },
            "required": ["free_text"],
        },
    },
    {
        "name": "score_job_against_profile",
        "description": "Score a single job listing 0-100 against a candidate profile.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job": {"type": "object", "description": "A job listing object"},
                "profile": {"type": "object", "description": "The normalized candidate profile"},
            },
            "required": ["job", "profile"],
        },
    },
]

TOOL_FUNCTIONS = {
    "normalize_user_profile": normalize_user_profile,
    "score_job_against_profile": score_job_against_profile,
}


def run_matching_agent(user_prompt: str, jobs: list[dict], resume_text: str | None = None) -> dict:
    """Run the Matching Agent on a candidate prompt/resume and a list of jobs."""
    user_message = json.dumps({
        "free_text": user_prompt,
        "resume_text": resume_text,
        "jobs": jobs[:15],
    })
    return run_agent(SYSTEM_PROMPT, TOOL_SCHEMAS, TOOL_FUNCTIONS, user_message)
