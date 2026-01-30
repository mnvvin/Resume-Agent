# Resume Agent 🤖📄

Resume Agent is an AI-powered job application assistant that helps users:
- Improve their resumes using AI
- Discover relevant job listings
- Generate personalized cover letters

Built using **Streamlit**, **Flask**, and **LLM-based AI models**, this project aims to simplify and automate the job application process.

---

## 🚀 Features

- 📄 **Resume Improvement**
  - Upload resume (PDF/DOCX)
  - AI-powered suggestions for ATS optimization, formatting, and content

- 🔍 **Job Discovery**
  - Fetches real-time job listings using APIs
  - Filters jobs based on role and location

- ✉️ **Cover Letter Generator**
  - Generates role-specific, professional cover letters
  - Uses AI to tailor content for companies and job roles

---

## 🖼️ Project Demo

![Resume Agent UI](assets/resume-agent-ui.png)

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit (Python)
- **Backend:** Flask (Python)
- **AI / NLP:** Gemini Flash, Agno Agents
- **Resume Parsing:** pdfplumber
- **Job Listings API:** JSearch (RapidAPI)

---

## ⚙️ Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/your-username/resume-agent.git
cd resume-agent
2. Create virtual environment
python -m venv venv
venv\Scripts\activate

3. Install dependencies
pip install -r requirements.txt

4. In Backend terminal
cd backend
uvicorn main:app --reload --port 8000

4. Run the application in frontend terminal
streamlit run streamlit_app.py
