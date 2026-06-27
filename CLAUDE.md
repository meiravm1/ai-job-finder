# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the Streamlit app
streamlit run app.py

# Run all tests
pytest

# Run a single test file
pytest tests/test_matching_tools.py

# Install dependencies
pip install -r requirements.txt
```

**Environment variables** (copy `.env.example` to `.env` and fill in):
- `GEMINI_API_KEY` — required for the default Gemini provider
- `GROQ_API_KEY` — required only when `LLM_PROVIDER=groq`
- `JOBDATALAKE_API_KEY` — required for job search

`LLM_PROVIDER` env var selects the LLM backend at deployment time (`gemini` default, `groq` alternative). Not a per-search UI option.

## Architecture

**Flow:** `app.py` → `orchestrator.py:run_pipeline` → Profile Agent → Search Agent → `matching_tools.rank_jobs_against_profile`

### Layers

**`orchestrator.py`** — thin glue, no LLM logic. Calls agents sequentially and passes profile output from Profile Agent into Search Agent.

**`agents/profile_agent.py`** — toolless LLM call (no tools, no loop). Converts raw free text (user prompt + resume) into a structured profile JSON (`role`, `location`, `seniority`, `remote_preference`, `years_experience`, `skills`). Falls back to `tools/matching_tools.normalize_user_profile` (regex-based) if the LLM call fails or returns unparseable output. Has no tools intentionally — isolates prompt injection risk from untrusted resume content.

**`agents/search_agent.py`** — LLM agent with two tools: `search_jobs` (JobDataLake API) and `search_company` (Google News RSS). Receives the structured profile as context alongside the raw user prompt. Appends a `role_match_signal` float (0–1) to each job before returning. The agent's final answer is a JSON object — not a natural language response.

**`agents/agent_loop.py`** — shared tool-use loop used by both agents. Supports Gemini (`google-genai` SDK, native function-calling) and Groq (OpenAI-compatible client). Groq falls back to Gemini on rate limits or `tool_use_failed` errors. Handles JSON-parse retries (up to `MAX_JSON_RETRIES=2`) when the model returns prose instead of JSON.

**`tools/matching_tools.py`** — pure Python, no LLM. `rank_jobs_against_profile` scores each job (0–100) using weighted rules: title/role match (40 pts, uses `role_match_signal` from the agent for partial matches), location or remote match (10–15 pts), seniority match (10 pts), skill overlap (up to 25 pts). `normalize_user_profile` is the regex fallback for profile extraction.

**`tools/search_tools.py`** — wraps `jobdatalake_client.get_jobs` and `google_news_client.search_news` into the tool function signatures the Search Agent calls. Normalizes the inconsistent JobDataLake response shape (`locations` vs `location`, `company_name` vs `company`, etc.).

**`tools/resume_tools.py`** — called by `app.py` before the pipeline. Extracts plain text from uploaded PDF (via `pypdf`) or `.txt` files. Known limitation: `pypdf` can garble complex PDF layouts, which degrades profile extraction quality even with the LLM agent.

### Key design constraints

- The Profile Agent has **zero tools** — this is intentional to contain prompt injection from untrusted resume content.
- The Search Agent limits `skills` filter to ≤2–3 skills: the JobDataLake API ANDs all skills, and longer lists reliably return zero results.
- `role_match_signal` (LLM-assigned, 0–1) feeds into the deterministic scorer as a weight on the 40-point role component — keeping costly LLM evaluation narrow and rule-based ranking authoritative.
- `MAX_ITERATIONS=10` in `agent_loop.py` caps the tool-use loop. Each `search_company` call per job plus the initial `search_jobs` call can eat this budget; the prompt instructs the agent to return jobs with empty `company_news` rather than running out of turns.
