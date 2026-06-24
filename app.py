"""Streamlit UI: a single Job Search page."""

import os

import streamlit as st
from dotenv import load_dotenv

from agents.agent_loop import PROVIDER_MODELS
from orchestrator import run_pipeline
from tools.resume_tools import extract_resume_text

load_dotenv()

st.set_page_config(page_title="AI Job Finder", page_icon="🔎")

# LLM provider is a deployment-time choice, not a per-search UI option -
# set via the LLM_PROVIDER env var (defaults to "gemini").
provider = os.environ.get("LLM_PROVIDER", "gemini")
if provider not in PROVIDER_MODELS:
    st.error(f"Unknown LLM_PROVIDER '{provider}'. Choose one of: {', '.join(PROVIDER_MODELS)}")
    st.stop()

st.title("AI Job Finder")
st.caption("Describe the job you're looking for, optionally upload your resume, and search.")

free_text = st.text_area(
    "What are you looking for?",
    placeholder="e.g. junior python developer, remote friendly, 2 years experience",
)

resume_file = st.file_uploader("Upload your resume (optional)", type=["pdf", "txt"])

if st.button("Search", type="primary"):
    if not free_text:
        st.warning("Please describe what you're looking for.")
    else:
        user_prompt = free_text.strip()

        resume_text = None
        if resume_file is not None:
            resume_text = extract_resume_text(resume_file)

        with st.spinner("Searching and ranking jobs..."):
            st.session_state.search_result = run_pipeline(user_prompt, resume_text=resume_text, provider=provider)
        # New results invalidate any previously selected row index in the table below.
        st.session_state.pop("ranked_jobs_table", None)

result = st.session_state.get("search_result")
if result is not None:
    ranked_jobs = result.get("ranked_jobs", [])
    errors = result.get("errors", [])

    if errors:
        st.warning("Something went wrong while searching. See Debug info below for details.")

    if ranked_jobs:
        st.subheader("Ranked results")
        st.caption("Click a row to see company news below.")
        selection = st.dataframe(
            [
                {
                    "Title": job.get("title"),
                    "Company": job.get("company"),
                    "Location": job.get("location"),
                    "Skills": ", ".join(job.get("skills") or []),
                    "Score%": job.get("matching_score"),
                    "Why": job.get("match_reason"),
                    "Link": job.get("url"),
                }
                for job in ranked_jobs
            ],
            width="stretch",
            on_select="rerun",
            selection_mode="single-row",
            key="ranked_jobs_table",
            column_config={"Link": st.column_config.LinkColumn("Link", display_text="Apply ↗")},
        )

        selected_rows = selection.selection.rows if selection else []
        if selected_rows and selected_rows[0] < len(ranked_jobs):
            selected_job = ranked_jobs[selected_rows[0]]
            news = selected_job.get("company_news") or []
            st.markdown(f"#### 📰 Company Spotlight: {selected_job.get('company')}")
            if news:
                for item in news:
                    meta = " · ".join(p for p in (item.get("published"), item.get("source")) if p)
                    st.markdown(f"- {item.get('headline')}")
                    if meta:
                        st.caption(meta)
            else:
                st.caption("No notable company news found.")
    elif not errors:
        st.info("No matching jobs found. Try a broader search.")

    with st.expander("Debug info"):
        st.json(result)
