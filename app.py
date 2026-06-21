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
            result = run_pipeline(user_prompt, resume_text=resume_text, provider=provider)

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
