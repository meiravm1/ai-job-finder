# Changelog

Notable changes and decisions made to this project, in reverse chronological order.

## 2026-06-20
- Removed the LLM-based Matching Agent (`agents/matching_agent.py`); it always ran the same fixed two-tool sequence regardless of input, so the LLM never made an actual decision there. Profile extraction now runs once up front in `orchestrator.py` and ranking calls `tools/matching_tools.rank_jobs_against_profile()` directly — no LLM ever sees the raw resume text.
- The Search Agent now receives the parsed candidate profile (skills/seniority/years/remote preference) alongside the prompt, so resume-only details can inform search queries; previously the resume was invisible to search.
- Removed the "Job title" and "Location" fields from the Streamlit UI; search input is now free text + optional resume only.
- Decided to maintain this changelog going forward, updated whenever a notable change or decision is made to the project.
