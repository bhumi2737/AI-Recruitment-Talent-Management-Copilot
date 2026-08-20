# AI Driven Smart Hiring Platform with Candidate Matching Copilot (HireFlow AI) ⚡💼

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://hireflow-copilot.streamlit.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

An enterprise-grade, AI-powered **Smart Hiring Platform & Recruitment Copilot** built with **Python**, **Streamlit**, **MongoDB**, and **Groq LLM/Whisper AI**.

**🚀 Live Demo:** [HireFlow AI on Streamlit Cloud](https://hireflow-copilot.streamlit.app/)

**HireFlow AI** streamlines talent acquisition, automated resume parsing, ATS scoring, Job Description candidate matching, AI-driven technical interviews, automated candidate evaluations, and enterprise platform management.

---

## 🌟 Key Features & Role Separation

### 🛡️ Admin Enterprise Control Center
- **Executive Platform Overview**: Real-time DB telemetry tracking Job Requisitions, Recruiters, Candidates Pool, Applications, Shortlisted Candidates, Interviews, and Hires.
- **Job Requisitions Management**: Platform-wide JD overview with application counts, selection metrics, and direct candidate pipeline inspection.
- **System Recruitment Analytics**: Stage distribution pie charts, selection rates, and **Skill Demand vs Candidate Availability** analysis.
- **Recruiter Performance Analytics**: Dynamic recruiter performance tracking (JDs managed, applications received, candidates shortlisted, hires made).
- **AI Monitoring**: Real-time telemetry for Resumes Parsed, ATS Match Scores, AI Question Sets, AI Interview Evaluations, and Whisper STT.
- **Recruitment Health Diagnostics**: Automated anomaly detector inspecting missing JD text, incomplete candidate profiles, stuck applications, and duplicate entries.
- **System Audit Trail**: Immutable filterable log history tracking user authentication, stage changes, and administrative actions.
- **User & Recruiter Onboarding**: Onboard recruiter accounts and manage user statuses (Activate / Deactivate).

### 💼 Recruiter Hiring Portal
- **Automated Resume Parsing**: Parse **PDF** and **DOCX** resumes in-memory via `pypdf` and `python-docx` without saving candidate resumes to disk.
- **ATS Compatibility Scoring**: Calculate match metrics and keyword overlap between candidate profiles and job requisitions.
- **Candidate Matching Engine**: Intelligent matching algorithm mapping candidate skill vectors to open role requirements.
- **AI Technical Question Generator**: Custom job-specific technical interview questions generated in real-time using **Groq LLMs**.
- **Interactive Conversational AI Interview & Evaluation**: Live candidate interviews with automated scoring breakdowns and downloadable PDF feedback reports via `reportlab`.
- **Voice Interview Integration**: Integrated **Groq Whisper Speech-to-Text** service for real-time voice response transcription.

---

## 🏗️ Architecture & Technology Stack

| Layer | Technology |
|---|---|
| **Frontend UI** | [Streamlit](https://streamlit.io/) (SaaS dashboard styling, reactive widgets, dynamic metrics) |
| **Backend Logic** | Python 3.10+, FastAPI (optional REST service wrapper in `main.py`) |
| **Database & Persistence** | [MongoDB](https://www.mongodb.com/) (`pymongo`), JSON disk fallback |
| **AI & Voice Services** | [Groq API](https://groq.com/) (Llama 3.3 70B / Mixtral models for Q&A, Whisper STT) |
| **Document Processing** | `pypdf`, `python-docx`, `reportlab` (PDF generation) |
| **Security & Auth** | `bcrypt`, `PyJWT` |

---

## 📁 Repository Structure

```
AI-Recruitment-Talent-Management-Copilot/
│
├── ResumeParser/
│   ├── app.py                      # Main HireFlow AI Streamlit Application Entry Point
│   ├── database.py                 # MongoDB Database connection & Audit Trail CRUD
│   ├── auth_service.py             # User Authentication & JWT management
│   ├── auth_routes.py              # API Authentication routes
│   ├── ai_question_generator.py    # AI Technical Question Generation service (Groq API)
│   ├── ai_interview_evaluator.py   # AI Candidate Evaluation service
│   ├── conversational_ai_interview.py # Interactive Conversational Interview engine
│   ├── groq_whisper_service.py     # Groq Whisper Voice Speech-to-Text transcription
│   ├── interview_pdf_report.py     # ReportLab PDF Report Generator
│   ├── jd_matcher.py               # Job Description matching algorithm
│   ├── jd_matching_service.py      # JD match processing services
│   ├── offline_storage.py          # Disk-backed JSON fallback storage
│   ├── parser.py                   # In-memory PDF & DOCX resume parser
│   ├── scorer.py                   # ATS Scoring engine
│   ├── main.py                     # Optional FastAPI REST service wrapper
│   ├── requirements.txt            # Python dependencies
│   ├── samples/                    # Sample resume documents for testing
│   └── .streamlit/
│       └── config.toml             # Streamlit server & theme configuration
│
├── .env.example                    # Environment variable configuration template
├── .gitignore                      # Git exclusion rules (cache, env, test artifacts ignored)
├── requirements.txt                # Production dependency manifest
└── README.md                       # Primary project documentation
```

---

## 🚀 Local Quickstart Guide

### 1. Clone the Repository

```bash
git clone https://github.com/bhumi2737/AI-Recruitment-Talent-Management-Copilot.git
cd AI-Recruitment-Talent-Management-Copilot
```

### 2. Create and Activate a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` inside `ResumeParser/` (or workspace root):

```bash
cp .env.example .env
```

Edit `.env` with your MongoDB connection URI and Groq API key:

```env
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?appName=Cluster0
MONGO_DB=recruitment_copilot
MONGO_COLLECTION=candidates
GROQ_API_KEY=gsk_your_actual_groq_api_key
JWT_SECRET_KEY=your_secure_jwt_secret_key
BOOTSTRAP_ADMIN_PASSWORD=admin123
```

> **Note**: If MongoDB is not configured or offline, the application gracefully operates using disk-backed local storage.

### 5. Launch the Streamlit Application

Run the application from the repository root:

```bash
streamlit run ResumeParser/app.py
```

Open your browser at `http://localhost:8501`.

---

## ☁️ Deploying to Streamlit Community Cloud

1. **Push your repository** to GitHub.
2. Log in to [Streamlit Community Cloud](https://streamlit.io/cloud).
3. Click **New app** and select your GitHub repository:
   - **Repository**: `bhumi2737/AI-Recruitment-Talent-Management-Copilot`
   - **Branch**: `main`
   - **Main file path**: `ResumeParser/app.py`
4. In **Advanced Settings**, add your environment variables under **Secrets**:

```toml
MONGO_URI = "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?appName=Cluster0"
MONGO_DB = "recruitment_copilot"
MONGO_COLLECTION = "candidates"
GROQ_API_KEY = "gsk_your_groq_api_key"
JWT_SECRET_KEY = "your_production_jwt_secret_key"
BOOTSTRAP_ADMIN_PASSWORD = "your_password"
```

5. Click **Deploy!** Your application will be live publicly.

---

## 🛡️ Security & Privacy Notes

- **Secrets Management**: No credentials, API keys, or database URI strings are tracked in Git. Always configure secrets via environment variables or Streamlit Cloud Secrets.
- **In-Memory Document Handling**: Uploaded resume files are parsed in-memory using binary buffers (`io.BytesIO`) without persisting raw candidate resumes to disk.
- **Session Security**: Passwords are hashed using `bcrypt` and JWT tokens handle API authorization.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
