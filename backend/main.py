# backend/main.py
import os
import shutil
import uuid
import importlib
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests
import openai
import textwrap

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# Resume utility import (tolerant)
try:
    from resume_utils import (
        extract_text_from_pdf,
        extract_text_from_docx,
        basic_resume_analysis,
    )
    resume_utils_module = None
except Exception:
    resume_utils_module = importlib.import_module("resume_utils")
    extract_text_from_pdf = getattr(resume_utils_module, "extract_text_from_pdf", None)
    extract_text_from_docx = getattr(resume_utils_module, "extract_text_from_docx", None)
    basic_resume_analysis = getattr(resume_utils_module, "basic_resume_analysis", None)
    if extract_text_from_pdf is None and hasattr(resume_utils_module, "extract_text_from_file"):
        extract_text_from_pdf = lambda p: resume_utils_module.extract_text_from_file(p)
    if extract_text_from_docx is None and hasattr(resume_utils_module, "extract_text_from_file"):
        extract_text_from_docx = lambda p: resume_utils_module.extract_text_from_file(p)
    if basic_resume_analysis is None:
        def basic_resume_analysis(text):
            return {"word_count": len(text.split()) if text else 0, "suggestions": ["No analyzer available; using stub."]}

extractor_missing = (extract_text_from_pdf is None or extract_text_from_docx is None)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Resume Agent Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def save_upload(file: UploadFile):
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, unique_name)
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return path

@app.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    try:
        saved_path = save_upload(file)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to save file: {e}"})
    return {"status": "ok", "path": saved_path, "original_filename": file.filename}

def call_openai_for_resume_improvements(resume_text: str, max_chars=4000):
    """
    Call OpenAI to get resume improvement suggestions.
    We truncate to max_chars to avoid sending huge texts.
    """
    if not OPENAI_API_KEY:
        return {"error": "OpenAI key not configured"}
    prompt = textwrap.dedent(f"""
    You are a professional resume reviewer. Given the resume text below,
    provide: 1) a short summary (1-2 sentences), 2) 6 bullet improvement suggestions that are actionable,
    and 3) 3 tailored keywords suitable for ATS (comma-separated).
    Resume text:
    {resume_text[:max_chars]}
    Please return results in JSON with keys: summary, suggestions (list), keywords (list).
    """)
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            max_tokens=500,
            temperature=0.3,
        )
        out = resp["choices"][0]["message"]["content"].strip()
        # Attempt to parse safe JSON-like text. We'll return the raw text and let frontend show it.
        return {"raw": out}
    except Exception as e:
        return {"error": str(e)}

@app.post("/improve")
async def improve_resume(file_path: str = Form(...), use_ai: bool = Form(False)):
    """
    If use_ai is False -> run basic rule-based analysis.
    If use_ai is True  -> use OpenAI for richer suggestions.
    """
    if not os.path.exists(file_path):
        return JSONResponse(status_code=400, content={"error": "file not found"})
    if extractor_missing:
        return JSONResponse(status_code=500, content={"error": "Text extractor functions not available in resume_utils.py."})

    file_lower = file_path.lower()
    try:
        if file_lower.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif file_lower.endswith(".docx"):
            text = extract_text_from_docx(file_path)
        else:
            return JSONResponse(status_code=400, content={"error": "unsupported file type"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to extract text: {e}"})

    basic = basic_resume_analysis(text)
    if use_ai:
        ai_result = call_openai_for_resume_improvements(text)
        return {"status": "ok", "analysis": basic, "ai": ai_result, "extracted_text_snippet": text[:1000]}
    else:
        return {"status": "ok", "analysis": basic, "extracted_text_snippet": text[:1000]}

@app.post("/jobs")
async def find_jobs(keywords: str = Form(...), location: str = Form(""), page: int = Form(1)):
    """
    Uses RapidAPI JSearch (example).
    Make sure JSEARCH_API_KEY and JSEARCH_API_HOST are set in .env.
    """
    JSEARCH_API_KEY = os.getenv("0838ee21ddmsh93468a76da16875p100693jsn50461723a7c4")
    JSEARCH_API_HOST = os.getenv("JSEARCH_API_HOST", "jsearch.p.rapidapi.com")
    if not JSEARCH_API_KEY:
        # return mock results if no key provided
        sample = [
            {"title":"Software Engineer I", "company":"ExampleCorp", "snippet":"Work on backend APIs.", "url":"https://example.com/job/1"},
            {"title":"Frontend Developer", "company":"Acme Inc", "snippet":"React + TypeScript role", "url":"https://example.com/job/2"},
        ]
        return {"status":"mock", "jobs": sample}

    url = f"https://{JSEARCH_API_HOST}/search"
    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": JSEARCH_API_HOST,
    }
    params = {"query": keywords, "page": page, "num_pages": 1, "location": location}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # adapt to result format (JSearch returns 'data' or 'results' depending on provider)
        jobs = data.get("data") or data.get("results") or data
        # Normalize to list of items with keys title/company/snippet/url
        normalized = []
        for item in jobs if isinstance(jobs, list) else []:
            normalized.append({
                "title": item.get("job_title") or item.get("title") or item.get("position"),
                "company": item.get("company_name") or item.get("company"),
                "snippet": item.get("job_description") or item.get("snippet") or item.get("description"),
                "url": item.get("job_apply_link") or item.get("url") or item.get("apply_link"),
            })
        return {"status":"ok", "jobs": normalized}
    except Exception as e:
        return {"status":"error", "error": str(e)}

@app.post("/cover")
async def generate_cover(file_path: str = Form(...), job_title: str = Form(...), company: str = Form(...), job_description: str = Form(""), use_ai: bool = Form(True)):
    """
    Generate cover letter. If use_ai is True it will call OpenAI for a personalized letter.
    """
    if not os.path.exists(file_path):
        return JSONResponse(status_code=400, content={"error":"file not found"})
    if extractor_missing:
        return JSONResponse(status_code=500, content={"error": "Text extractor functions not available in resume_utils.py."})

    file_lower = file_path.lower()
    try:
        if file_lower.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        else:
            text = extract_text_from_docx(file_path)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to extract text: {e}"})

    snippet = text[:1500].replace("\n", " ")
    if use_ai and OPENAI_API_KEY:
        # create prompt for OpenAI
        prompt = textwrap.dedent(f"""
        You are a skilled writer. Use the resume information and the job description to write a concise, professional cover letter tailored to the job.
        Job title: {job_title}
        Company: {company}
        Job Description: {job_description[:1500]}
        Resume snippet: {snippet}
        Write a 3-paragraph cover letter (introduction, specific fit/achievements, closing). Keep it professional and include a call-to-action. Output only the cover letter text.
        """)
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":prompt}],
                max_tokens=600,
                temperature=0.3,
            )
            letter = resp["choices"][0]["message"]["content"].strip()
            return {"status":"ok", "cover_letter": letter}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"OpenAI error: {e}"})

    # fallback templated cover letter
    letter = f"""Dear Hiring Manager at {company},

I am writing to apply for the position of {job_title}. Based on my resume, I have experience that aligns with this role: {snippet[:400]} ...

I am excited about the opportunity to contribute to {company} and would welcome the opportunity to discuss how my skills and experience can help your team reach its goals.

Sincerely,
[Your Name]
"""
    return {"status":"ok", "cover_letter": letter}
