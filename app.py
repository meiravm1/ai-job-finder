"""Streamlit UI: a single Job Search page."""

import streamlit as st
from dotenv import load_dotenv

from agents.agent_loop import PROVIDER_MODELS
from orchestrator import run_pipeline
from tools.matching_tools import DEFAULT_MAX_JOBS_TO_SCORE
from tools.resume_tools import extract_resume_text

load_dotenv()

st.set_page_config(page_title="AI Job Finder", page_icon="🔎")
st.title("AI Job Finder")
st.caption("Describe the job you're looking for, optionally upload your resume, and search.")

provider = st.selectbox("LLM provider", options=list(PROVIDER_MODELS.keys()))
max_results = st.number_input(
    "Number of results", min_value=1, max_value=50, value=DEFAULT_MAX_JOBS_TO_SCORE,
)

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
            result = run_pipeline(user_prompt, resume_text=resume_text, provider=provider, max_results=int(max_results))

        ranked_jobs = result.get("ranked_jobs", [])
        errors = result.get("errors", [])

        if errors:
            st.warning("Something went wrong while searching. See Debug info below for details.")

        if ranked_jobs:
            st.subheader("Ranked results")
            st.dataframe(
                [
                    {
                        "Title": job.get("title"),
                        "Company": job.get("company"),
                        "Location": job.get("location"),
                        "Score": job.get("matching_score"),
                        "Why": job.get("match_reason"),
                        "Link": job.get("url"),
                    }
                    for job in ranked_jobs
                ],
                use_container_width=True,
            )
        elif not errors:
            st.info("No matching jobs found. Try a broader search.")

        with st.expander("Debug info"):
            st.json(result)
