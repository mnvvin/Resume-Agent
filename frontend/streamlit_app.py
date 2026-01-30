# frontend/streamlit_app.py
import streamlit as st
import requests
from pathlib import Path
import os

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
UPLOAD_ENDPOINT = f"{BACKEND_URL}/upload"
IMPROVE_ENDPOINT = f"{BACKEND_URL}/improve"
JOBS_ENDPOINT = f"{BACKEND_URL}/jobs"
COVER_ENDPOINT = f"{BACKEND_URL}/cover"

st.set_page_config(page_title="Resume Agent", layout="centered")

# Optional: show screenshot reference (uses uploaded file path from session)
# Developer-provided file path: /mnt/data/Screenshot 2025-11-23 131411.jpg
screenshot_path = "/mnt/data/Screenshot 2025-11-23 131411.jpg"
if Path(screenshot_path).exists():
    st.image(screenshot_path, caption="Design reference (screenshot)")

# Header
st.markdown('<div style="font-weight:800;font-size:36px">Resume Agent : Your AI-Powered Job Assistant</div>', unsafe_allow_html=True)
st.markdown('<div style="color:#6b7280;margin-bottom:16px">Upload your resume and let our AI assistant help you improve it, find job listings, and write cover letters.</div>', unsafe_allow_html=True)

# Uploader
uploaded_file = st.file_uploader("Upload Your Resume", type=["pdf", "docx"], accept_multiple_files=False)

if uploaded_file:
    st.markdown(f"**{uploaded_file.name}** — {uploaded_file.size} bytes")
    st.success("Resume uploaded successfully!")

    if st.button("Save resume on server"):
        files = {"file": (uploaded_file.name, uploaded_file.read())}
        with st.spinner("Uploading..."):
            resp = requests.post(UPLOAD_ENDPOINT, files=files)
        if resp.ok:
            data = resp.json()
            st.info("Resume saved on server. You can now choose an action.")
            st.session_state["uploaded_path"] = data.get("path")
        else:
            st.error("Upload failed: " + resp.text)

# AI toggles
use_ai_improve = st.checkbox("Use AI for resume suggestions (OpenAI)", value=True)
use_ai_cover = st.checkbox("Use AI for cover letter (OpenAI)", value=True)

# Action buttons
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Improve Resume"):
        file_path = st.session_state.get("uploaded_path")
        if not file_path:
            st.warning("Please upload and save your resume first.")
        else:
            with st.spinner("Analyzing resume..."):
                resp = requests.post(IMPROVE_ENDPOINT, data={"file_path": file_path, "use_ai": str(use_ai_improve)})
            if resp.ok:
                res = resp.json()
                st.success("Analysis complete")
                st.write("**Word count:**", res["analysis"]["word_count"])
                st.write("**Suggestions (basic):**")
                for s in res["analysis"]["suggestions"]:
                    st.markdown(f"- {s}")
                if "ai" in res:
                    st.subheader("AI suggestions (raw):")
                    # if OpenAI output is raw JSON-like text, just show it in a text area
                    ai_raw = res["ai"].get("raw") if isinstance(res["ai"], dict) else None
                    if ai_raw:
                        st.text_area("AI Output", value=ai_raw, height=260)
                    else:
                        st.write(res["ai"])
                st.write("**Text snippet:**")
                st.code(res.get("extracted_text_snippet", "")[:1000])
            else:
                st.error("Error: " + resp.text)

with col2:
    if st.button("Find Job Listings"):
        st.session_state["show_jobs"] = True

with col3:
    if st.button("Generate Cover Letter"):
        st.session_state["show_cover"] = True

st.markdown("---")

# Job search area
if st.session_state.get("show_jobs", False):
    st.header("Job Search (JSearch via RapidAPI)")
    keywords = st.text_input("Keywords (e.g. 'Data Engineer')")
    location = st.text_input("Location (optional)")
    page = st.number_input("Page", value=1, min_value=1)
    if st.button("Search Jobs"):
        with st.spinner("Fetching jobs..."):
            resp = requests.post(JOBS_ENDPOINT, data={"keywords": keywords, "location": location, "page": page})
        if resp.ok:
            data = resp.json()
            if data.get("status") == "mock":
                st.info("Showing sample (mock) jobs because no JSEARCH_API_KEY is configured.")
            jobs = data.get("jobs", [])
            if not jobs:
                st.write("No jobs found.")
            for j in jobs:
                st.markdown(f"**{j.get('title', 'No title')}** — {j.get('company', '')}")
                st.write(j.get("snippet", ""))
                if j.get("url"):
                    st.markdown(f"[View Job]({j.get('url')})")
        else:
            st.error("Job fetch error: " + resp.text)

# Cover letter area
if st.session_state.get("show_cover", False):
    st.header("Generate Cover Letter")
    job_title = st.text_input("Job Title (e.g. 'Software Engineer')")
    company = st.text_input("Company (e.g. 'Acme Corp')")
    job_desc = st.text_area("Paste job description (optional)")
    if st.button("Generate Letter"):
        file_path = st.session_state.get("uploaded_path")
        if not file_path:
            st.warning("Please upload and save your resume first.")
        else:
            with st.spinner("Generating cover letter..."):
                resp = requests.post(COVER_ENDPOINT, data={
                    "file_path": file_path,
                    "job_title": job_title,
                    "company": company,
                    "job_description": job_desc,
                    "use_ai": str(use_ai_cover)
                })
            if resp.ok:
                data = resp.json()
                letter = data.get("cover_letter", "")
                st.success("Cover letter generated")
                st.text_area("Cover Letter", value=letter, height=300)
                st.download_button("Download Letter", data=letter, file_name=f"cover_{company}_{job_title}.txt")
            else:
                st.error("Error: " + resp.text)
