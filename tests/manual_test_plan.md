# Manual Test Plan

1. **Environment check:** `.env` has `ANTHROPIC_API_KEY` and `JOBDATALAKE_API_KEY`;
   `pip install -r requirements.txt` succeeds.

2. **API client smoke test (no LLM):**
   ```python
   from tools.jobdatalake_client import get_jobs
   print(get_jobs({"q": "python developer"}))
   ```
   Confirm a 200 response with a parseable jobs list — validates the API key
   and base URL before involving the LLM.

3. **Search Agent isolated test:**
   ```python
   from agents.search_agent import run_search_agent
   print(run_search_agent("junior python developer jobs in Tel Aviv, remote friendly"))
   ```
   For each prompt in `sample_prompts.md`, verify the output matches the
   schema (`jobs` is a list of dicts, `errors` is a list).

4. **Matching Agent isolated test:**
   ```python
   from agents.matching_agent import run_matching_agent
   jobs = [
       {"title": "Junior Python Developer", "company": "Acme", "location": "Tel Aviv",
        "remote_type": "remote", "seniority": "junior", "skills": ["python", "sql"]},
       {"title": "Senior Java Engineer", "company": "Beta", "location": "Haifa",
        "remote_type": "on-site", "seniority": "senior", "skills": ["java"]},
   ]
   print(run_matching_agent("junior python developer, remote, 2 years experience", jobs))
   ```
   Verify `ranked_jobs` is sorted descending by `matching_score`, scores are
   ints 0-100, and `profile_used` looks reasonable.

5. **End-to-end test:**
   ```python
   from orchestrator import run_pipeline
   print(run_pipeline("junior python developer jobs in Tel Aviv, remote friendly, 2 years experience"))
   ```
   Run for each sample prompt; confirm output has `profile_used` and
   `ranked_jobs`, and that scores roughly align with intuition (e.g. a remote
   job scores higher for a "remote friendly" prompt).

6. **Streamlit smoke test:**
   ```
   streamlit run app.py
   ```
   - Enter sample prompt 1, optionally upload a resume (.pdf or .txt), click Search.
   - Confirm the results table renders without errors.
   - Confirm the top-ranked job is plausibly relevant.
   - Temporarily set an invalid `JOBDATALAKE_API_KEY` and confirm a warning
     is shown instead of a crash.

7. **Edge cases:**
   - Empty/garbage prompt should not crash; should return empty/low-confidence
     results with a note.
   - A very narrow query with zero results should trigger the Search Agent's
     broaden-and-retry step.

8. **Record results:** for each prompt tested in steps 5-7, fill out one
   entry using `docs/retrospective_template.md` (e.g. saved under
   `docs/retrospectives/<date>-<run>.md`).
