"""Streamlit UI: a single Job Search page."""

import os

import streamlit as st
from dotenv import load_dotenv

from agents.agent_loop import PROVIDER_MODELS
from orchestrator import run_pipeline
from tools.resume_tools import extract_resume_text

load_dotenv()

st.set_page_config(page_title="AI Job Finder", page_icon="🔎")

# Style company-name buttons to look like hyperlinks.
# Primary buttons (e.g. "Search") use kind="primary" and are unaffected.
st.markdown(
    """
    <style>
    [data-testid="stButton"] > button[kind="secondary"] {
        background: none !important;
        border: none !important;
        color: #1a73e8 !important;
        text-decoration: underline !important;
        padding: 0 !important;
        font-size: 0.9rem !important;
        font-weight: normal !important;
        min-height: 0 !important;
        box-shadow: none !important;
        text-align: left !important;
    }
    [data-testid="stButton"] > button[kind="secondary"]:hover {
        color: #1557b0 !important;
        background: none !important;
        border: none !important;
        box-shadow: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
        st.session_state.pop("selected_company_idx", None)

result = st.session_state.get("search_result")
if result is not None:
    ranked_jobs = result.get("ranked_jobs", [])
    errors = result.get("errors", [])

    if errors:
        st.warning("Something went wrong while searching. See Debug info below for details.")

    if ranked_jobs:
        visible_jobs = [job for job in ranked_jobs if (job.get("matching_score") or 0) >= 20]

        if visible_jobs:
            st.subheader("Ranked results")

            # Table header
            h = st.columns([3, 2, 2, 3, 1, 1])
            for col, label in zip(h, ["Title", "Company", "Location", "Skills", "Score%", "Apply"]):
                col.markdown(f"**{label}**")

            st.divider()

            # Table rows
            for i, job in enumerate(visible_jobs):
                cols = st.columns([3, 2, 2, 3, 1, 1])
                cols[0].write(job.get("title", ""))
                if cols[1].button(job.get("company") or "Unknown", key=f"co_{i}"):
                    st.session_state.selected_company_idx = i
                cols[2].write(job.get("location", ""))
                cols[3].write(", ".join(job.get("skills") or []))
                cols[4].write(f"{job.get('matching_score', 0)}%")
                if job.get("url"):
                    cols[5].markdown(f"[Apply ↗]({job.get('url')})")

            # Company Spotlight (detail panel)
            selected_idx = st.session_state.get("selected_company_idx")
            if selected_idx is not None and selected_idx < len(visible_jobs):
                selected_job = visible_jobs[selected_idx]
                news = selected_job.get("company_news") or []
                st.markdown(f"#### 📰 Company Spotlight: {selected_job.get('company')}")
                if news:
                    for item in news:
                        meta = " · ".join(p for p in (item.get("published"), item.get("source")) if p)
                        headline = item.get("headline", "")
                        url = item.get("url")
                        st.markdown(f"- [{headline}]({url})" if url else f"- {headline}")
                        if meta:
                            st.caption(meta)
                else:
                    st.caption("No notable company news found.")
        else:
            st.info("No matching jobs found. Try a broader search.")

    elif not errors:
        st.info("No matching jobs found. Try a broader search.")

    # with st.expander("Debug info"):
    #     st.json(result)
