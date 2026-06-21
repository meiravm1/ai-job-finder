# ai-job-finder

A small AI-assisted system that searches [JobDataLake](https://www.jobdatalake.com/)
for jobs matching a free-text request, then ranks the results against the
candidate's profile (and optional resume).

## How it works

1. The user enters a free-text prompt (plus an optional resume) in the
   Streamlit app.
2. The **Profile Agent** (`agents/profile_agent.py`) extracts a candidate
   profile (role, location, seniority, remote preference, years of
   experience, skills) from the prompt and resume up front, via an LLM call
   — resumes are too free-form for regex to parse reliably. Falls back to a
   deterministic regex extractor (`tools/matching_tools.normalize_user_profile`)
   if the LLM call fails.
3. The **Search Agent** (`agents/search_agent.py`) turns the prompt
   (enriched with the extracted profile) into a JobDataLake API query and
   returns matching job listings.
4. A deterministic rule-based ranking step (`tools/matching_tools.py`)
   scores each job 0-100 against the already-extracted profile — no LLM
   call is involved, since this step is a fixed sequence with no actual
   decision for an LLM to make.
5. Ranked results are displayed in the Streamlit app.

## Architecture

```mermaid
flowchart TD
      User([User]) -->|"free text + resume upload"| UI[Streamlit App\napp.py]
      UI -->|user_prompt + resume_text| Orchestrator[orchestrator.py\nrun_pipeline]

      Orchestrator -->|user_prompt + resume_text| ProfileAgent[Profile Agent — LLM\nagents/profile_agent.py]
      ProfileAgent -->|profile JSON| Orchestrator

      Orchestrator -->|user_prompt + profile| SearchAgent[Search Agent — LLM\nagents/search_agent.py]
      SearchAgent -->|search_jobs| JDL[(JobDataLake API\napi.jobdatalake.com)]
      JDL --> SearchAgent
      SearchAgent -->|jobs JSON| Orchestrator

      Orchestrator -->|profile + jobs| MatchTools[Rule-based ranking — no LLM\ntools/matching_tools.py]
      MatchTools -->|ranked_jobs JSON| Orchestrator

    Orchestrator -->|ranked_jobs| UI
    UI -->|results table| User
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # then fill in GEMINI_API_KEY and JOBDATALAKE_API_KEY
streamlit run app.py
```

The LLM backend (`gemini` or `groq`) is a deployment-time choice, not a
per-search UI option - set it via the `LLM_PROVIDER` env var (defaults to
`gemini`), e.g. `LLM_PROVIDER=groq streamlit run app.py`.

## Project layout

- `app.py` — Streamlit UI (single Job Search page)
- `orchestrator.py` — runs the Profile Agent, then the Search Agent, then ranks jobs via deterministic scoring (`tools/matching_tools.py`)
- `agents/` — Profile Agent and Search Agent system prompts/tool schemas, and the shared tool-use loop (`agent_loop.py`)
- `tools/` — tool implementations (JobDataLake client, search, matching, resume parsing)
- `docs/retrospective_template.md` — "what worked / what didn't" template for test runs
- `tests/` — manual test plan and sample prompts
