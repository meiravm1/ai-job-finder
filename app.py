"""Streamlit UI: a single Job Search page."""

import streamlit as st
from dotenv import load_dotenv

from agents.agent_loop import PROVIDER_MODELS
from orchestrator import run_pipeline
from tools.resume_tools import extract_resume_text

load_dotenv()

st.set_page_config(page_title="AI Job Finder", page_icon="🔎")
st.title("AI Job Finder")
st.caption("Describe the job you're looking for, optionally upload your resume, and search.")

provider = st.selectbox("LLM provider", options=list(PROVIDER_MODELS.keys()))

free_text = st.text_area(
    "What are you looking for?",
    placeholder="e.g. junior python developer, remote friendly, 2 years experience",
)

col1, col2 = st.columns(2)
with col1:
    title = st.text_input("Job title (optional)", placeholder="e.g. Python Developer")
with col2:
    location = st.text_input("Location (optional)", placeholder="e.g. Tel Aviv")

resume_file = st.file_uploader("Upload your resume (optional)", type=["pdf", "txt"])

if st.button("Search", type="primary"):
    if not free_text and not title:
        st.warning("Please describe what you're looking for, or enter a job title.")
    else:
        prompt_parts = [free_text]
        if title:
            prompt_parts.append(f"Title: {title}.")
        if location:
            prompt_parts.append(f"Location: {location}.")
        user_prompt = " ".join(part for part in prompt_parts if part).strip()

        resume_text = None
        if resume_file is not None:
            resume_text = extract_resume_text(resume_file)

        with st.spinner("Searching and ranking jobs..."):
            result = run_pipeline(user_prompt, resume_text=resume_text, provider=provider)

        ranked_jobs = result.get("ranked_jobs", [])
        errors = result.get("errors", [])

        if errors:
            st.warning("\n".join(str(e) for e in errors))

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
