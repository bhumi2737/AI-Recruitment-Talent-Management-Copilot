"""
AI Recruitment & Talent Management Copilot
Milestone 1: Resume Parser and Candidate Profiling
Streamlit dashboard application.
"""
from __future__ import annotations

import html
import inspect
from collections import Counter
from datetime import datetime
from typing import Any

import streamlit as st
import requests

import database as db
from parser import calculate_extraction_accuracy, parse_resume
from scorer import calculate_ats_score
from jd_matcher import match_candidate_to_job

# ── Mock Jobs Data ────────────────────────────────────────────────────────────
DEFAULT_MOCK_JOBS = [
    {
        "job_id": "JOB-MOCK1",
        "job_title": "Senior Python Backend Engineer",
        "company_name": "TechCorp Solutions",
        "location": "San Francisco, CA (Hybrid)",
        "experience_required": "5+ Years",
        "required_skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "REST API"],
        "job_description": "We are seeking a Senior Python Backend Engineer to design and implement scalable microservices. You will work with FastAPI, Docker, and PostgreSQL on a daily basis.",
        "salary": "$130,000 - $160,000",
    },
    {
        "job_id": "JOB-MOCK2",
        "job_title": "Data Scientist / ML Practitioner",
        "company_name": "AI & Insights Ltd",
        "location": "Remote (US/Canada)",
        "experience_required": "3+ Years",
        "required_skills": ["Python", "TensorFlow", "PyTorch", "Machine Learning", "Scikit-learn"],
        "job_description": "Join our AI & Insights team to build and deploy machine learning models. Experience with TensorFlow or PyTorch and classical ML packages is required.",
        "salary": "$120,000 - $150,000",
    },
    {
        "job_id": "JOB-MOCK3",
        "job_title": "Fullstack Software Engineer (React/Node)",
        "company_name": "WebFlow Inc",
        "location": "New York, NY",
        "experience_required": "2+ Years",
        "required_skills": ["React", "JavaScript", "TypeScript", "Node.js", "HTML", "CSS"],
        "job_description": "Looking for a fullstack engineer to develop user interfaces in React and backend services in Node.js. Must be comfortable writing TypeScript, HTML, and CSS.",
        "salary": "$100,000 - $130,000",
    }
]


# ── Streamlit cache helper ────────────────────────────────────────────────────
def st_cache_data_no_spinner(ttl: int = 20):
    """Return a Streamlit cache decorator that hides the default cache spinner when supported."""
    cache_kwargs = {"ttl": ttl}

    if hasattr(st, "cache_data"):
        try:
            sig = inspect.signature(st.cache_data)
            if "show_spinner" in sig.parameters:
                cache_kwargs["show_spinner"] = False
        except Exception:
            pass
        return st.cache_data(**cache_kwargs)

    if hasattr(st, "cache"):
        try:
            return st.cache(**cache_kwargs)
        except Exception:
            return st.cache

    return lambda func: func


# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RC Recruitment Copilot",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Custom CSS ────────────────────────────────────────────────────────────────
# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        :root {
            --bg: #f0f2f6;
            --card: #ffffff;
            --text: #0f172a;
            --text-2: #1e293b;
            --muted: #475569;
            --border: #cbd5e1;
            --blue: #1e40af;
            --blue-2: #2563eb;
            --badge-bg: #dbeafe;
            --badge-text: #1d4ed8;
            --green: #16a34a;
            --red: #dc2626;
        }

        .stApp,
        [data-testid="stAppViewContainer"] {
            background-color: var(--bg) !important;
            color: var(--text) !important;
        }

        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] span,
        [data-testid="stMarkdownContainer"] div,
        [data-testid="stMarkdownContainer"] strong,
        [data-testid="stMarkdownContainer"] em,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stMarkdownContainer"] h1,
        [data-testid="stMarkdownContainer"] h2,
        [data-testid="stMarkdownContainer"] h3,
        [data-testid="stMarkdownContainer"] h4,
        [data-testid="stMarkdownContainer"] h5,
        [data-testid="stMarkdownContainer"] h6 {
            color: var(--text) !important;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: var(--card) !important;
            border-right: 1px solid var(--border) !important;
        }

        [data-testid="stSidebar"] .stMarkdown h1 {
            font-size: 1.25rem !important;
            color: var(--blue) !important;
            font-weight: 800 !important;
        }

        [data-testid="stSidebar"] div.stButton > button {
            background-color: transparent !important;
            color: #334155 !important;
            border: none !important;
            box-shadow: none !important;
            text-align: left !important;
            justify-content: flex-start !important;
            font-weight: 600 !important;
            padding: 0.5rem 0.75rem !important;
            border-radius: 8px !important;
            margin-bottom: 0.25rem !important;
            width: 100% !important;
        }

        [data-testid="stSidebar"] div.stButton > button * {
            color: #334155 !important;
        }

        [data-testid="stSidebar"] div.stButton > button:hover {
            background-color: #f1f5f9 !important;
            color: var(--text) !important;
        }

        [data-testid="stSidebar"] div.stButton > button:hover * {
            color: var(--text) !important;
        }

        [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
            background-color: var(--blue) !important;
            color: #ffffff !important;
            border-radius: 8px !important;
        }

        [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] * {
            color: #ffffff !important;
        }

        /* Main headings */
        .main-heading {
            font-size: 2rem !important;
            font-weight: 800 !important;
            color: var(--text) !important;
            margin-bottom: 0.25rem !important;
        }

        .main-subtitle {
            font-size: 1rem !important;
            color: var(--muted) !important;
            margin-bottom: 1.5rem !important;
        }

        /* Cards */
        .custom-card {
            background: var(--card) !important;
            color: var(--text) !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.06) !important;
            border: 1px solid var(--border) !important;
            margin-bottom: 1rem !important;
        }

        .custom-card,
        .custom-card *,
        .custom-card p,
        .custom-card div,
        .custom-card span,
        .custom-card strong,
        .custom-card h1,
        .custom-card h2,
        .custom-card h3,
        .custom-card h4,
        .custom-card h5,
        .custom-card h6 {
            color: var(--text) !important;
        }

        .custom-card a,
        .custom-card a:hover,
        a {
            color: var(--blue-2) !important;
            font-weight: 700 !important;
            text-decoration: none !important;
        }

        .card-title {
            font-size: 1.1rem !important;
            font-weight: 800 !important;
            color: var(--text) !important;
            margin-bottom: 1rem !important;
        }

        .field-label {
            font-size: 0.75rem !important;
            font-weight: 800 !important;
            color: var(--muted) !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            margin-bottom: 0.15rem !important;
        }

        .field-value {
            font-size: 0.95rem !important;
            color: var(--text) !important;
            font-weight: 500 !important;
            margin-bottom: 0.75rem !important;
        }

        .section-heading {
            font-size: 0.95rem !important;
            font-weight: 800 !important;
            color: var(--text) !important;
            margin: 0.75rem 0 0.35rem 0 !important;
        }

        .section-text {
            font-size: 0.9rem !important;
            color: var(--text) !important;
            line-height: 1.6 !important;
            white-space: pre-wrap !important;
            background: #f8fafc !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            padding: 0.75rem 1rem !important;
            margin-bottom: 0.5rem !important;
        }

        /* Skills */
        .skill-badge {
            display: inline-block !important;
            background-color: var(--badge-bg) !important;
            color: var(--badge-text) !important;
            padding: 0.25rem 0.75rem !important;
            border-radius: 9999px !important;
            font-size: 0.8rem !important;
            font-weight: 800 !important;
            margin: 0.2rem 0.25rem 0.2rem 0 !important;
        }

        .missing-badge {
            background-color: #fee2e2 !important;
            color: #b91c1c !important;
        }

        /* Candidate list */
        .candidate-list-info,
        .candidate-list-info *,
        .candidate-name,
        .candidate-text,
        .candidate-text strong,
        .candidate-skills {
            color: var(--text) !important;
        }

        .candidate-name {
            font-size: 1.3rem !important;
            font-weight: 800 !important;
            margin: 0 0 0.5rem 0 !important;
            color: var(--text) !important;
        }

        .candidate-text {
            font-size: 0.95rem !important;
            color: var(--text-2) !important;
            margin-bottom: 0.75rem !important;
        }

        .candidate-text strong {
            color: var(--text) !important;
            font-weight: 800 !important;
        }

        /* Metrics */
        .metric-box {
            background: #f8fafc !important;
            border-radius: 8px !important;
            padding: 0.75rem 1rem !important;
            text-align: center !important;
            border: 1px solid var(--border) !important;
        }

        .metric-value {
            font-size: 1.5rem !important;
            font-weight: 800 !important;
            color: var(--blue) !important;
        }

        .metric-label {
            font-size: 0.75rem !important;
            color: var(--muted) !important;
            margin-top: 0.15rem !important;
            font-weight: 700 !important;
        }

        /* Dashboard skill bars */
        .activity-item {
            padding: 0.4rem 0 !important;
        }

        .activity-name {
            color: var(--text) !important;
            font-weight: 800 !important;
        }

        .activity-meta {
            color: var(--muted) !important;
            font-size: 0.85rem !important;
        }

        .skill-row {
            display: flex !important;
            align-items: center !important;
            gap: 0.75rem !important;
            margin-bottom: 0.55rem !important;
        }

        .skill-name {
            flex: 1 !important;
            min-width: 8rem !important;
            font-weight: 800 !important;
            color: var(--text) !important;
        }

        .skill-bar-bg {
            flex: 2 !important;
            background: #e0f2fe !important;
            border-radius: 999px !important;
            height: 0.75rem !important;
            overflow: hidden !important;
        }

        .skill-bar-fill {
            background: var(--blue) !important;
            height: 100% !important;
            border-radius: 999px !important;
        }

        .skill-count {
            min-width: 2.5rem !important;
            text-align: right !important;
            color: var(--muted) !important;
            font-weight: 800 !important;
        }

        /* DB status */
        .status-connected {
            color: var(--green) !important;
            font-size: 0.85rem !important;
            font-weight: 800 !important;
        }

        .status-disconnected {
            color: var(--red) !important;
            font-size: 0.85rem !important;
            font-weight: 800 !important;
        }

        /* Inputs */
        .stTextInput input,
        .stTextInput textarea,
        .stTextArea textarea,
        [data-testid="stTextArea"] textarea {
            background-color: var(--card) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
        }

        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {
            color: #64748b !important;
            opacity: 1 !important;
        }

        .stTextArea textarea:focus,
        [data-testid="stTextArea"] textarea:focus {
            border: 1px solid var(--blue-2) !important;
            box-shadow: 0 0 0 1px var(--blue-2) !important;
        }

        [data-testid="stTextArea"] textarea:disabled,
        .stTextArea textarea:disabled {
            background-color: #ffffff !important;
            color: var(--text) !important;
            opacity: 1 !important;
            -webkit-text-fill-color: var(--text) !important;
        }

        [data-testid="stTextArea"] label,
        [data-testid="stTextArea"] label * {
            color: var(--text) !important;
            font-weight: 700 !important;
        }

        /* File uploader */
        [data-testid="stFileUploader"] {
            background-color: #ffffff !important;
            border: 2px dashed var(--border) !important;
            border-radius: 12px !important;
            padding: 0.75rem !important;
        }

        [data-testid="stFileUploader"] section {
            background-color: #ffffff !important;
            border: none !important;
        }

        [data-testid="stFileUploader"] section > div {
            background-color: #ffffff !important;
        }

        [data-testid="stFileUploader"] section * {
            color: var(--text) !important;
        }

        [data-testid="stFileUploader"] small,
        [data-testid="stFileUploader"] span {
            color: var(--muted) !important;
        }

        [data-testid="stFileUploader"] button {
            background-color: var(--blue) !important;
            color: #ffffff !important;
            border: 1px solid var(--blue) !important;
            border-radius: 8px !important;
            font-weight: 800 !important;
        }

        [data-testid="stFileUploader"] button *,
        [data-testid="stFileUploader"] button p,
        [data-testid="stFileUploader"] button span {
            color: #ffffff !important;
        }

        /* Uploaded file chip visible and readable */
        [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {
            display: flex !important;
            visibility: visible !important;
            background-color: #ffffff !important;
            background: #ffffff !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            box-shadow: none !important;
            opacity: 1 !important;
            padding: 0.45rem 0.6rem !important;
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] > div,
        [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] div {
            background-color: #ffffff !important;
            background: #ffffff !important;
            color: var(--text) !important;
            opacity: 1 !important;
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] p,
        [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] span,
        [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] small,
        [data-testid="stFileUploader"] [data-testid="stFileUploaderFileName"],
        [data-testid="stFileUploader"] [data-testid="stFileUploaderFileSize"] {
            color: var(--text) !important;
            opacity: 1 !important;
            font-weight: 700 !important;
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderFileSize"],
        [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] small {
            color: var(--muted) !important;
            font-weight: 600 !important;
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] svg,
        [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] svg * {
            fill: var(--blue) !important;
            stroke: var(--blue) !important;
            color: var(--blue) !important;
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button {
            background-color: #eff6ff !important;
            color: var(--blue) !important;
            border: 1px solid #bfdbfe !important;
            border-radius: 50% !important;
        }

        [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button * {
            color: var(--blue) !important;
            fill: var(--blue) !important;
            stroke: var(--blue) !important;
        }

        .upload-hint {
            color: var(--muted) !important;
            font-size: 0.85rem !important;
            margin-top: 0.5rem !important;
        }

        .file-name {
            color: var(--text) !important;
            font-weight: 800 !important;
            font-size: 0.9rem !important;
        }

        /* Main content buttons */
        [data-testid="stAppViewContainer"] div.stButton > button {
            background-color: var(--blue) !important;
            color: #ffffff !important;
            border: 1px solid var(--blue) !important;
            border-radius: 8px !important;
            font-weight: 800 !important;
        }

        [data-testid="stAppViewContainer"] div.stButton > button * {
            color: #ffffff !important;
        }

        [data-testid="stAppViewContainer"] div.stButton > button:hover {
            background-color: var(--blue-2) !important;
            border-color: var(--blue-2) !important;
            color: #ffffff !important;
        }

        /* Expander */
        [data-testid="stExpander"] {
            background-color: #ffffff !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
        }

        [data-testid="stExpander"] details {
            background-color: #ffffff !important;
            border-radius: 10px !important;
        }

        [data-testid="stExpander"] summary {
            background-color: #ffffff !important;
            color: var(--text) !important;
            font-weight: 800 !important;
            border-radius: 10px !important;
        }

        [data-testid="stExpander"] summary * {
            color: var(--text) !important;
        }

        /* Dataframe */
        [data-testid="stDataFrame"],
        [data-testid="stDataFrame"] * {
            color: var(--text) !important;
        }

        /* Sidebar collapse icons */
        [data-testid="collapsedControl"] button,
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapseButton"] button,
        button[data-testid="stSidebarCollapseButton"],
        button[data-testid="stBaseButton-header"],
        button[data-testid="stBaseButton-headerNoPadding"] {
            color: #000000 !important;
            display: inline-flex !important;
            visibility: visible !important;
        }

        [data-testid="collapsedControl"] button svg,
        [data-testid="stSidebarCollapseButton"] svg,
        button[data-testid="stSidebarCollapseButton"] svg,
        button[data-testid="stBaseButton-header"] svg,
        button[data-testid="stBaseButton-headerNoPadding"] svg,
        [data-testid="collapsedControl"] button svg *,
        [data-testid="stSidebarCollapseButton"] svg *,
        button[data-testid="stSidebarCollapseButton"] svg *,
        button[data-testid="stBaseButton-header"] svg *,
        button[data-testid="stBaseButton-headerNoPadding"] svg * {
            fill: #000000 !important;
            stroke: #000000 !important;
            color: #000000 !important;
        }

        /* Hide Streamlit extras */
        [class*="deploy"],
        [class*="Deploy"],
        [data-testid*="deploy"],
        [data-testid*="Deploy"],
        [data-testid="stHeaderActionButton"],
        #MainMenu,
        footer {
            display: none !important;
            visibility: hidden !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Session state defaults ────────────────────────────────────────────────────
DEFAULT_SESSION_VALUES = {
    "processed_count": 0,
    "profiles_created": 0,
    "last_profile": None,
    "last_accuracy": 0,
    "progress_value": 0.0,
    "parse_complete": False,
    "already_exists": False,
    "recent_candidates": [],
    "active_page": "Resume Upload",
    "selected_candidate_id": None,
    "search_filter": "",
    "current_file": None,
    "parse_msg": "",
    "saved_to_db": False,
    "save_state": None,
    "scanned_pdf_warning": False,
}

for key, value in DEFAULT_SESSION_VALUES.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ── Utility helpers ───────────────────────────────────────────────────────────
def safe_text(value: Any, default: str = "—") -> str:
    """Return a safe plain string for rendering."""
    if value is None:
        return default
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value if item)
    text = str(value).strip()
    return text if text else default


def candidate_id(candidate: dict) -> str:
    return str(candidate.get("id") or candidate.get("_id") or candidate.get("email") or candidate.get("phone") or "")


def skills_to_list(skills: Any) -> list[str]:
    if not skills:
        return []
    if isinstance(skills, list):
        return [str(skill).strip() for skill in skills if str(skill).strip()]
    if isinstance(skills, (tuple, set)):
        return [str(skill).strip() for skill in skills if str(skill).strip()]
    return [skill.strip() for skill in str(skills).split(",") if skill.strip()]


def skills_to_csv(skills: Any) -> str:
    return ", ".join(skills_to_list(skills))


def normalize_skill(skill: Any) -> str:
    s = str(skill or "").strip().lower()
    mapping = {
        "js": "JavaScript",
        "javascript": "JavaScript",
        "reactjs": "React",
        "react.js": "React",
        "node": "Node.js",
        "nodejs": "Node.js",
        "node.js": "Node.js",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "sql": "SQL",
        "python": "Python",
        "java": "Java",
        "c++": "C++",
        "html": "HTML",
        "css": "CSS",
        "ml": "Machine Learning",
        "machine learning": "Machine Learning",
        "data analysis": "Data Analysis",
        "data science": "Data Science",
        "power bi": "Power BI",
        "tableau": "Tableau",
        "excel": "Excel",
        "git": "Git",
        "mongodb": "MongoDB",
        "docker": "Docker",
        "rest api": "REST API",
        "streamlit": "Streamlit",
        "fastapi": "FastAPI",
    }
    return mapping.get(s, s.title()) if s else ""


def format_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if value:
        return str(value)[:16]
    return "Unknown"


def parse_db_save_response(response: Any) -> tuple[bool, str, str | None]:
    """Normalize different save_candidate return styles."""
    if isinstance(response, tuple):
        success = bool(response[0]) if len(response) > 0 else False
        msg = str(response[1]) if len(response) > 1 else ("Candidate saved." if success else "Candidate not saved.")
        save_state = response[2] if len(response) > 2 else None
        return success, msg, save_state

    if isinstance(response, dict):
        success = bool(response.get("success", True))
        msg = response.get("message") or response.get("msg") or ("Candidate saved." if success else "Candidate not saved.")
        save_state = response.get("status") or response.get("state")
        return success, str(msg), save_state

    if isinstance(response, str):
        return True, f"Candidate {response} successfully.", response

    return bool(response), "Candidate saved successfully." if response else "Candidate not saved.", None


def format_skill_badges(skills: Any, max_display: int = 8) -> str:
    skill_list = skills_to_list(skills)
    if not skill_list:
        return '<span class="field-value">No skills detected</span>'

    badges = ""
    for skill in skill_list[:max_display]:
        badges += f'<span class="skill-badge">{html.escape(skill)}</span>'

    if len(skill_list) > max_display:
        badges += f'<span class="skill-badge">+{len(skill_list) - max_display} more</span>'

    return badges


def render_section_block(icon: str, title: str, content: Any):
    safe_content = html.escape(safe_text(content, "Not found"))
    st.markdown(
        f'<p class="section-heading">{icon} {title}</p>'
        f'<div class="section-text">{safe_content}</div>',
        unsafe_allow_html=True,
    )


def render_progress_card():
    st.markdown('<p class="card-title">⚡ Parsing Progress</p>', unsafe_allow_html=True)
    pct = int(float(st.session_state.progress_value) * 100)
    st.progress(st.session_state.progress_value, text=f"Processing status: {pct}%")

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{st.session_state.processed_count}</div>'
            f'<div class="metric-label">Resumes Processed</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{st.session_state.last_accuracy}%</div>'
            f'<div class="metric-label">Extraction Accuracy</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{st.session_state.profiles_created}</div>'
            f'<div class="metric-label">Profiles Created</div></div>',
            unsafe_allow_html=True,
        )


def calculate_dashboard_stats_from_candidates(candidates: list[dict]) -> dict:
    unique_candidates = {}
    for candidate in candidates:
        key = candidate.get("email") or candidate.get("phone") or candidate_id(candidate)
        if key and key not in unique_candidates:
            unique_candidates[key] = candidate

    clean_candidates = list(unique_candidates.values())

    skill_counter: Counter[str] = Counter()
    for candidate in clean_candidates:
        for skill in skills_to_list(candidate.get("skills")):
            normalized = normalize_skill(skill)
            if normalized:
                skill_counter[normalized] += 1

    fields = ["full_name", "email", "phone", "skills", "education", "experience", "projects", "certifications"]
    completeness_scores = []
    for candidate in clean_candidates:
        filled = 0
        for field in fields:
            value = candidate.get(field)
            if isinstance(value, list) and value:
                filled += 1
            elif isinstance(value, str) and value.strip():
                filled += 1
            elif value and not isinstance(value, (list, str)):
                filled += 1
        completeness_scores.append((filled / len(fields)) * 100)

    avg_completeness = round(sum(completeness_scores) / len(completeness_scores), 1) if completeness_scores else 0

    return {
        "total_candidates": len(clean_candidates),
        "avg_completeness": avg_completeness,
        "unique_skills_count": len(skill_counter),
        "top_skills": [{"skill": skill, "count": count} for skill, count in skill_counter.most_common(15)],
        "recent_activity": clean_candidates[:5],
    }


def normalize_top_skills(top_skills: Any) -> list[dict]:
    result = []
    for item in top_skills or []:
        if isinstance(item, dict):
            skill = item.get("skill") or item.get("name") or item.get("_id") or ""
            count = item.get("count") or item.get("value") or 0
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            skill, count = item[0], item[1]
        else:
            continue
        normalized = normalize_skill(skill)
        if normalized:
            result.append({"skill": normalized, "count": int(count)})
    return result


# ── Cached database readers ───────────────────────────────────────────────────
@st_cache_data_no_spinner(ttl=120)
def load_candidates(search_query: str = "") -> list[dict]:
    try:
        if hasattr(db, "get_all_candidates_light"):
            return db.get_all_candidates_light(search_query)

        candidates, err = db.get_recent_candidates(limit=100)
        return [] if err else candidates
    except Exception:
        return []


@st_cache_data_no_spinner(ttl=120)
def load_recent_candidates(limit: int = 10) -> tuple[list[dict], str | None]:
    try:
        candidates, err = db.get_recent_candidates(limit)
        return candidates or [], err
    except Exception as exc:
        return [], str(exc)


@st_cache_data_no_spinner(ttl=120)
def load_dashboard_stats() -> dict:
    try:
        if hasattr(db, "get_dashboard_stats"):
            stats = db.get_dashboard_stats()
            stats["top_skills"] = normalize_top_skills(stats.get("top_skills", []))
            return stats
    except Exception:
        pass

    candidates = load_candidates("")
    return calculate_dashboard_stats_from_candidates(candidates)

@st_cache_data_no_spinner(ttl=120)
def load_db_status() -> bool:
    ok, _ = db.test_connection()
    return ok


@st_cache_data_no_spinner(ttl=30)
def load_api_status() -> bool:
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=1.0)
        return response.status_code == 200
    except Exception:
        return False


@st_cache_data_no_spinner(ttl=30)
def api_get_jobs() -> list[dict[str, Any]]:
    try:
        response = requests.get("http://127.0.0.1:8000/api/jobs/", timeout=1.5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []


def load_jobs() -> list[dict[str, Any]]:
    api_ok = load_api_status()
    if api_ok:
        jobs = api_get_jobs()
        if jobs:
            return jobs
    db_ok = load_db_status()
    if db_ok:
        try:
            import db_jobs
            jobs = db_jobs.get_all_jobs()
            if jobs:
                return jobs
        except Exception:
            pass
    return DEFAULT_MOCK_JOBS


def save_job(job_data: dict[str, Any]) -> tuple[bool, str]:
    api_ok = load_api_status()
    if api_ok:
        try:
            response = requests.post("http://127.0.0.1:8000/api/jobs/", json=job_data, timeout=2.0)
            if response.status_code == 201:
                return True, "Job description created successfully via API."
            else:
                detail = response.json().get("detail", "Unknown error")
                return False, f"API Error: {detail}"
        except Exception as exc:
            return False, f"Failed to connect to API: {exc}"
    
    db_ok = load_db_status()
    if db_ok:
        try:
            import db_jobs
            job_id = db_jobs.create_job(job_data)
            return True, f"Job description created successfully in Database (API offline). Job ID: {job_id}"
        except Exception as exc:
            return False, f"Database Error: {exc}"
            
    return False, "Both API and Database are offline. Cannot save job."


def delete_job(job_id: str) -> tuple[bool, str]:
    api_ok = load_api_status()
    if api_ok:
        try:
            response = requests.delete(f"http://127.0.0.1:8000/api/jobs/{job_id}", timeout=2.0)
            if response.status_code == 200:
                return True, "Job description deleted successfully via API."
            else:
                detail = response.json().get("detail", "Unknown error")
                return False, f"API Error: {detail}"
        except Exception as exc:
            return False, f"Failed to delete via API: {exc}"
            
    db_ok = load_db_status()
    if db_ok:
        try:
            import db_jobs
            success = db_jobs.delete_job(job_id)
            if success:
                return True, "Job description deleted successfully from Database (API offline)."
            else:
                return False, "Job ID not found in Database."
        except Exception as exc:
            return False, f"Database Error: {exc}"
            
    return False, "Both API and Database are offline. Cannot delete job."

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 📋 RC Recruitment Copilot")
    st.markdown("---")

    nav_items = [
        ("🏠", "Dashboard"),
        ("📤", "Resume Upload"),
        ("👥", "Candidates"),
        ("💼", "Job Postings"),
        ("🤝", "JD Matching"),
        ("📊", "Analytics"),
        ("⚙️", "Settings"),
    ]

    for icon, label in nav_items:
        is_active = st.session_state.active_page == label
        if st.button(
            f"{icon}  {label}",
            key=f"nav_btn_{label}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.active_page = label
            if label == "Candidates":
                st.session_state.selected_candidate_id = None
            st.rerun()

    st.markdown("---")

    db_ok = False
    db_msg = ""
    try:
        db_ok, db_msg = db.test_connection()
    except Exception as exc:
        db_msg = str(exc)

    if db_ok:
        st.markdown('<p class="status-connected">● Database Connected</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-disconnected">● Database Offline</p>', unsafe_allow_html=True)
        st.caption(f"Connection error: {db_msg}")
        st.caption("Parsed data will still display, but will not be saved.")

    # if st.button("🧹 Clear Local Session", use_container_width=True):
    #     for key in list(DEFAULT_SESSION_VALUES.keys()):
    #         st.session_state[key] = DEFAULT_SESSION_VALUES[key]
    #     if hasattr(st, "cache_data"):
    #         st.cache_data.clear()
    #     st.rerun()


# ── Main content routing ──────────────────────────────────────────────────────
active_page = st.session_state.active_page


if active_page == "Dashboard":
    st.markdown('<p class="main-heading">Recruitment Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">AI Resume Parsing & Talent Pipeline Overview</p>', unsafe_allow_html=True)

    if st.button("🔄 Refresh Dashboard", type="secondary"):
        if hasattr(st, "cache_data"):
            st.cache_data.clear()
        st.rerun()

    stats = load_dashboard_stats()
    total_candidates = stats.get("total_candidates", 0)
    avg_completeness = stats.get("avg_completeness", 0)
    unique_skill_count = stats.get("unique_skills_count", 0)
    top_skills = normalize_top_skills(stats.get("top_skills", []))
    recent_activity = stats.get("recent_activity", []) or []

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{total_candidates}</div>'
            f'<div class="metric-label">Total Candidates</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{avg_completeness}%</div>'
            f'<div class="metric-label">Average Profile Completeness</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{unique_skill_count}</div>'
            f'<div class="metric-label">Unique Skills Extracted</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📊 Top Pipeline Skills</p>', unsafe_allow_html=True)

        if top_skills:
            max_count = max(item["count"] for item in top_skills) or 1
            for item in top_skills[:15]:
                bar_width = int((item["count"] / max_count) * 100)
                st.markdown(
                    f'''
                    <div class="skill-row">
                        <div class="skill-name">{html.escape(item["skill"])}</div>
                        <div class="skill-bar-bg">
                            <div class="skill-bar-fill" style="width:{bar_width}%;"></div>
                        </div>
                        <div class="skill-count">{item["count"]}</div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )

            st.markdown('<p class="field-label">All Extracted Skills</p>', unsafe_allow_html=True)
            all_badges = "".join(
                f'<span class="skill-badge">{html.escape(item["skill"])}</span>' for item in top_skills
            )
            st.markdown(all_badges, unsafe_allow_html=True)
        else:
            st.info("No skills extracted yet. Parse resumes to populate the dashboard metrics.")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">🕐 Recent Activity</p>', unsafe_allow_html=True)

        if recent_activity:
            for idx, candidate in enumerate(recent_activity[:5]):
                name = html.escape(safe_text(candidate.get("full_name"), "Unknown"))
                email = html.escape(safe_text(candidate.get("email"), "No email"))
                updated = format_datetime(candidate.get("updated_at") or candidate.get("created_at"))
                st.markdown(
                    f'''
                    <div class="activity-item">
                        <div class="activity-name">{name}</div>
                        <div class="activity-meta">{email} • Updated {html.escape(updated)}</div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )
                if idx < min(len(recent_activity), 5) - 1:
                    st.markdown("---")
        else:
            st.info("No recent candidate activity yet.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


elif active_page == "Candidates":
    st.markdown('<p class="main-heading">Candidates Directory</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Search and manage parsed candidate profiles</p>', unsafe_allow_html=True)

    search_query = st.text_input(
        "🔍 Search Candidates",
        value=st.session_state.get("search_filter", ""),
        placeholder="Type name, email, skills, education, or work history...",
        key="candidate_search_input",
    )
    st.session_state.search_filter = search_query

    selected_candidate_id = st.session_state.get("selected_candidate_id")

    if selected_candidate_id:
        try:
            candidate = db.get_candidate_by_id(selected_candidate_id, include_raw_text=True)
        except Exception as exc:
            candidate = None
            st.error(f"Could not load candidate: {exc}")

        if st.button("⬅️ Back to Candidates List", type="secondary"):
            st.session_state.selected_candidate_id = None
            st.rerun()

        if candidate:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.markdown(
                f'<p class="card-title">👤 Candidate Profile: {html.escape(safe_text(candidate.get("full_name"), "Unknown"))}</p>',
                unsafe_allow_html=True,
            )

            c_col1, c_col2, c_col3 = st.columns(3)
            with c_col1:
                st.markdown(
                    f'<p class="field-label">Full Name</p><p class="field-value">{html.escape(safe_text(candidate.get("full_name")))}</p>',
                    unsafe_allow_html=True,
                )
            with c_col2:
                st.markdown(
                    f'<p class="field-label">Email</p><p class="field-value">{html.escape(safe_text(candidate.get("email")))}</p>',
                    unsafe_allow_html=True,
                )
            with c_col3:
                st.markdown(
                    f'<p class="field-label">Phone</p><p class="field-value">{html.escape(safe_text(candidate.get("phone")))}</p>',
                    unsafe_allow_html=True,
                )

            st.markdown('<p class="field-label">Skills</p>', unsafe_allow_html=True)
            st.markdown(format_skill_badges(candidate.get("skills"), max_display=999), unsafe_allow_html=True)

            st.markdown("---")
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                render_section_block("🎓", "Education", candidate.get("education"))
                render_section_block("🏆", "Certifications", candidate.get("certifications"))
            with d_col2:
                render_section_block("💼", "Work Experience", candidate.get("experience"))
                render_section_block("🛠", "Projects", candidate.get("projects"))

            st.markdown("---")
            with st.expander("📄 View Raw Resume Text"):
                st.text_area("Raw Text Content", candidate.get("raw_text", ""), height=300, disabled=True)

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.error("Candidate not found.")

    else:
        candidates = load_candidates(search_query)

        if candidates:
            st.markdown(f"Showing **{len(candidates)}** candidates matching your search.")

            for c in candidates:
                cid = candidate_id(c)
                with st.container():
                    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                    col_c1, col_c2 = st.columns([4, 1])

                    with col_c1:
                        skills_value = skills_to_csv(c.get("skills"))
                        st.markdown(
                            f'''
                            <div class="candidate-list-info">
                                <h3 class="candidate-name">{html.escape(safe_text(c.get("full_name"), "Unknown"))}</h3>
                                <p class="candidate-text">
                                    📧 <strong>Email:</strong>
                                    <a href="mailto:{html.escape(safe_text(c.get("email"), ""))}">{html.escape(safe_text(c.get("email")))}</a>
                                    &nbsp;&nbsp;&nbsp;&nbsp;
                                    📞 <strong>Phone:</strong> {html.escape(safe_text(c.get("phone")))}
                                </p>
                                <div class="candidate-skills">{format_skill_badges(skills_value, max_display=6)}</div>
                            </div>
                            ''',
                            unsafe_allow_html=True,
                        )

                    with col_c2:
                        if st.button("👁️ View Profile", key=f"view_c_{cid}", use_container_width=True):
                            st.session_state.selected_candidate_id = cid
                            st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No candidates found matching the search criteria.")

    st.stop()


elif active_page == "Job Postings":
    st.markdown('<p class="main-heading">Job Postings</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Manage open vacancies and match candidate profiles</p>', unsafe_allow_html=True)

    # ── Create Job Expander & Form ────────────────────────────────────────────
    with st.expander("➕ Create New Job Description"):
        with st.form("create_job_form", clear_on_submit=True):
            job_title = st.text_input("Job Title*", placeholder="e.g. Senior Software Engineer")
            company_name = st.text_input("Company Name*", placeholder="e.g. Acme Corp")
            
            # Skills input
            required_skills_str = st.text_input(
                "Required Skills (comma-separated)*", 
                placeholder="e.g. Python, FastAPI, Docker"
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                experience_required = st.text_input("Experience Required*", placeholder="e.g. 3-5 Years")
            with col2:
                location = st.text_input("Location*", placeholder="e.g. San Francisco, CA (Hybrid)")
            with col3:
                salary = st.text_input("Salary / Compensation", placeholder="e.g. $120,000 - $150,000")
                
            job_description = st.text_area(
                "Job Description*", 
                placeholder="Provide details about the role, responsibilities, and requirements..."
            )
            
            submitted = st.form_submit_button("Create Job Posting", use_container_width=True)
            if submitted:
                if not (job_title.strip() and company_name.strip() and required_skills_str.strip() and experience_required.strip() and job_description.strip()):
                    st.error("Please fill in all required fields (marked with *).")
                else:
                    skills_list = [s.strip() for s in required_skills_str.split(",") if s.strip()]
                    job_data = {
                        "job_title": job_title.strip(),
                        "company_name": company_name.strip(),
                        "required_skills": skills_list,
                        "experience_required": experience_required.strip(),
                        "location": location.strip() or "Remote",
                        "salary": salary.strip() or "Not Specified",
                        "job_description": job_description.strip(),
                    }
                    success, msg = save_job(job_data)
                    if success:
                        st.success(msg)
                        if hasattr(st, "cache_data"):
                            st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(msg)

    # ── Load and Render Job Postings ──────────────────────────────────────────
    jobs = load_jobs()
    
    if not jobs:
        st.info("No job postings available. Click the button above to create one.")
    else:
        for idx, job in enumerate(jobs):
            jid = job.get("job_id") or f"MOCK-{idx}"
            title = job.get("job_title", "Untitled Role")
            company = job.get("company_name", "Unknown Company")
            loc = job.get("location", "Not Specified")
            exp = job.get("experience_required", "Not Specified")
            sal = job.get("salary", "Not Specified")
            skills = job.get("required_skills") or []
            desc = job.get("job_description", "")

            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            col_j1, col_j2 = st.columns([3, 1])

            with col_j1:
                st.markdown(f"### {html.escape(title)}")
                st.markdown(
                    f"🏢 **{html.escape(company)}** &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"📍 {html.escape(loc)} &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"💼 {html.escape(exp)} &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"💰 {html.escape(sal)}",
                    unsafe_allow_html=True,
                )
                st.markdown(format_skill_badges(skills, max_display=999), unsafe_allow_html=True)
                if desc:
                    with st.expander("📄 View Job Description Text"):
                        st.write(desc)

            with col_j2:
                st.write("")
                st.write("")
                match_btn_key = f"match_j_{jid}_{idx}"
                first_skill = skills[0] if skills else ""
                if st.button("🔍 Match Candidates", key=match_btn_key, use_container_width=True):
                    st.session_state.active_page = "Candidates"
                    st.session_state.selected_candidate_id = None
                    st.session_state.search_filter = first_skill
                    st.rerun()

                # Only show delete button for non-mock or if DB/API is connected
                delete_btn_key = f"delete_j_{jid}_{idx}"
                if st.button("🗑️ Delete Job", key=delete_btn_key, use_container_width=True, type="secondary"):
                    success, msg = delete_job(jid)
                    if success:
                        st.success(msg)
                        if hasattr(st, "cache_data"):
                            st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(msg)

            st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


elif active_page == "Analytics":
    st.markdown('<p class="main-heading">Pipeline Analytics</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Talent intake metrics and funnel analysis</p>', unsafe_allow_html=True)

    import numpy as np
    import pandas as pd

    col_a1, col_a2 = st.columns(2)

    with col_a1:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📈 Talent Intake Trend (Last 7 Days)</p>', unsafe_allow_html=True)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=7)
        data = pd.DataFrame(np.random.randint(2, 10, size=(7, 1)), index=dates, columns=["Candidates Registered"])
        st.line_chart(data, color="#1e40af")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_a2:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">🎯 Extraction Completeness Funnel</p>', unsafe_allow_html=True)
        stages = ["Uploaded Resumes", "Parsed Successfully", "Saved in MongoDB", "Matched Vacancy"]
        counts = [100, 95, 80, 45]
        df_funnel = pd.DataFrame(counts, index=stages, columns=["Count"])
        st.bar_chart(df_funnel, color="#1e40af")
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


elif active_page == "JD Matching":
    st.markdown('<p class="main-heading">Job Description Matching</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Compare candidates against Job Descriptions</p>', unsafe_allow_html=True)
    
    import db_jobs
    from jd_matching_service import compare_candidates_with_jd
    
    jds = db_jobs.get_all_jobs()
    if not jds:
        st.info("No Job Descriptions found. Please add a Job Description via API or DB to use this feature.")
    else:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        # Search / Select JD
        jd_options = {jd["job_id"]: f"{jd['job_title']} at {jd.get('company_name', 'Unknown')}" for jd in jds}
        selected_jd_id = st.selectbox("Select a Job Description to Match", options=list(jd_options.keys()), format_func=lambda x: jd_options[x])
        
        if st.button("Compare", type="primary"):
            with st.spinner("Comparing candidates..."):
                results = compare_candidates_with_jd(selected_jd_id)
                
            if results:
                st.success(f"Matched against {len(results)} candidates.")
                
                # Display table
                # Format the data for dataframe display
                df_data = []
                for res in results:
                    matched_str = ", ".join(res["matched_skills"]) if res["matched_skills"] else "None"
                    missing_str = ", ".join(res["missing_skills"]) if res["missing_skills"] else "None"
                    added_str = ", ".join(res["additional_skills"]) if res["additional_skills"] else "None"
                    
                    df_data.append({
                        "Candidate": res["candidate_name"],
                        "Match %": res["match_percentage"],
                        "Matched Skills": matched_str,
                        "Missing Skills": missing_str,
                        "Additional Skills": added_str
                    })
                
                st.dataframe(
                    df_data,
                    column_config={
                        "Match %": st.column_config.ProgressColumn(
                            "Match %",
                            help="Skill Match Percentage",
                            format="%f%%",
                            min_value=0,
                            max_value=100,
                        ),
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.warning("No candidates found in database to compare.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


elif active_page == "Settings":
    st.markdown('<p class="main-heading">Settings</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Configure application settings and connections</p>', unsafe_allow_html=True)

    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">⚙️ Parser Settings</p>', unsafe_allow_html=True)
    st.toggle("Enable Regex Name Heuristics", value=True)
    st.toggle("Enable Automated Skills Extractor", value=True)
    st.selectbox(
        "Resume OCR Parsing engine",
        ["pypdf (native metadata text extraction)", "tesseract (OCR scan mode - Disabled in M1)"],
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


elif active_page == "Resume Upload":
    st.markdown('<p class="main-heading">Resume Parsing & Candidate Profiling</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="main-subtitle">Upload and process resumes to create structured candidate profiles</p>',
        unsafe_allow_html=True,
    )

    col_upload, col_progress = st.columns([1, 1])

    with col_upload:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📤 Upload Resume</p>', unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Choose a resume file",
            type=["pdf", "docx"],
            label_visibility="collapsed",
        )

        if uploaded_file:
            st.markdown(f'<p class="file-name">📄 {html.escape(uploaded_file.name)}</p>', unsafe_allow_html=True)

        st.markdown('<p class="upload-hint">Supported formats: PDF, DOCX</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_progress:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        render_progress_card()
        st.markdown("</div>", unsafe_allow_html=True)

    if uploaded_file:
        if st.session_state.get("current_file") != uploaded_file.name:
            st.session_state.current_file = uploaded_file.name
            st.session_state.parse_complete = False
            st.session_state.progress_value = 0.0
            st.session_state.already_exists = False
    else:
        if st.session_state.get("current_file") is not None:
            st.session_state.current_file = None
            st.session_state.parse_complete = False
            st.session_state.progress_value = 0.0
            st.session_state.already_exists = False

    if uploaded_file is not None:
        if st.button("🚀 Parse Resume", type="primary", use_container_width=True):
            with st.spinner("Parsing resume..."):
                try:
                    file_bytes = uploaded_file.read()
                    profile = parse_resume(file_bytes, uploaded_file.name)

                    saved_to_db = False
                    save_state = None
                    parse_msg = "Database offline — profile parsed but not saved."

                    if db_ok:
                        response = db.save_candidate(profile)
                        saved_to_db, parse_msg, save_state = parse_db_save_response(response)
                    if save_state == "updated":
                         parse_msg = "Candidate already exists — existing profile was updated."
                    elif save_state == "inserted":
                        parse_msg = "New candidate inserted successfully."
                    is_scanned_pdf = (
                        profile.get("source_file_type") == "pdf"
                        and len(profile.get("raw_text", "").strip()) < 20
                    )

                    st.session_state.last_profile = profile
                    st.session_state.parse_complete = True
                    st.session_state.progress_value = 1.0
                    st.session_state.processed_count = 1
                    st.session_state.last_accuracy = int(calculate_extraction_accuracy(profile))
                    st.session_state.profiles_created = 1 if saved_to_db else 0
                    st.session_state.saved_to_db = saved_to_db
                    st.session_state.save_state = save_state
                    st.session_state.parse_msg = parse_msg
                    st.session_state.scanned_pdf_warning = is_scanned_pdf

                    status_text = "Saved" if saved_to_db else "Parsed (not saved)"
                    if save_state == "updated":
                        status_text = "Updated"
                    elif save_state == "inserted":
                        status_text = "Inserted"

                    st.session_state.recent_candidates.insert(
                        0,
                        {
                            "Name": safe_text(profile.get("full_name"), "Unknown"),
                            "Email": safe_text(profile.get("email")),
                            "Phone": safe_text(profile.get("phone")),
                            "Skills": skills_to_csv(profile.get("skills")) or "—",
                            "Status": status_text,
                        },
                    )

                    if hasattr(st, "cache_data"):
                        st.cache_data.clear()

                    st.rerun()

                except Exception as exc:
                    st.error(f"Parsing failed: {exc}")

    if st.session_state.last_profile:
        if st.session_state.get("parse_complete"):
            if st.session_state.get("saved_to_db"):
                if st.session_state.get("save_state") == "updated":
                    st.info(st.session_state.get("parse_msg", "Candidate already exists — profile updated."))
                else:
                    st.success(st.session_state.get("parse_msg", "Candidate saved successfully."))
            else:
                st.warning(st.session_state.get("parse_msg", "Database offline — profile parsed but not saved."))

        profile = st.session_state.last_profile

        if st.session_state.get("scanned_pdf_warning"):
            st.warning("This PDF appears to be scanned or image-based. Text extraction may not work without OCR.")

        with st.expander("Parser Debug"):
            st.write("**Uploaded file name:**", profile.get("source_filename", "—"))
            st.write("**File type:**", profile.get("source_file_type", "—"))
            st.write("**Extracted email:**", profile.get("email", "—") or "—")
            st.write("**Extracted phone:**", profile.get("phone", "—") or "—")
            st.write("**Raw text length:**", len(profile.get("raw_text", "")))
            st.write("**Save status:**", st.session_state.get("save_state", "—"))

        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">👤 Extracted Candidate Profile</p>', unsafe_allow_html=True)

        info_col1, info_col2, info_col3 = st.columns(3)
        with info_col1:
            st.markdown(
                f'<p class="field-label">Full Name</p><p class="field-value">{html.escape(safe_text(profile.get("full_name"), "Unknown"))}</p>',
                unsafe_allow_html=True,
            )
        with info_col2:
            st.markdown(
                f'<p class="field-label">Email</p><p class="field-value">{html.escape(safe_text(profile.get("email")))}</p>',
                unsafe_allow_html=True,
            )
        with info_col3:
            st.markdown(
                f'<p class="field-label">Phone</p><p class="field-value">{html.escape(safe_text(profile.get("phone")))}</p>',
                unsafe_allow_html=True,
            )

        st.markdown('<p class="field-label">Skills</p>', unsafe_allow_html=True)
        st.markdown(format_skill_badges(profile.get("skills"), max_display=999), unsafe_allow_html=True)

        st.markdown("---")

        detail_col1, detail_col2 = st.columns(2)
        with detail_col1:
            render_section_block("🎓", "Education", profile.get("education"))
            render_section_block("🏆", "Certifications", profile.get("certifications"))
        with detail_col2:
            render_section_block("💼", "Work Experience", profile.get("experience"))
            render_section_block("🛠", "Projects", profile.get("projects"))

        st.markdown("</div>", unsafe_allow_html=True)

        # ── ATS Score & Skill Gap Analysis ───────────────────────────────────────
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">🎯 ATS Score & Skill Gap Analysis</p>', unsafe_allow_html=True)

        # Let user choose a saved vacancy or manual pasting
        jobs_pool = load_jobs()
        
        mode = st.radio("Choose evaluation mode:", ["Select Saved Vacancy", "Paste Custom Job Description"], horizontal=True)
        
        selected_job = None
        job_description = ""
        
        if mode == "Select Saved Vacancy" and jobs_pool:
            job_options = [f"{j.get('job_title')} ({j.get('company_name')})" for j in jobs_pool]
            selected_job_title = st.selectbox("Select saved Job Post:", options=job_options)
            job_index = job_options.index(selected_job_title)
            selected_job = jobs_pool[job_index]
            job_description = selected_job.get("job_description", "")
            
            st.markdown(
                f"""
                <div style="background-color: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem;">
                    <strong>Company:</strong> {html.escape(selected_job.get("company_name", ""))} | 
                    <strong>Location:</strong> {html.escape(selected_job.get("location", ""))} | 
                    <strong>Exp:</strong> {html.escape(selected_job.get("experience_required", ""))}
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            job_description = st.text_area(
                "Paste Custom Job Description Text",
                placeholder="Paste the job description here to calculate ATS score...",
                height=180,
                key="job_description_input",
            )

        if st.button("Calculate ATS Score", use_container_width=True):
            if not job_description.strip():
                st.warning("Please select a job or paste a job description first.")
            else:
                if selected_job:
                    # Run structured match
                    ats_result = match_candidate_to_job(profile, selected_job)
                else:
                    # Run generic text match
                    ats_result = calculate_ats_score(profile, job_description)

                st.markdown(
                    f"""
                    <div class="metric-box">
                        <div class="metric-value">{ats_result["ats_score"]}%</div>
                        <div class="metric-label">ATS Score - {ats_result["verdict"]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                if "experience_feedback" in ats_result:
                    st.markdown('<p class="field-label">Experience Check</p>', unsafe_allow_html=True)
                    st.markdown(f'<p class="field-value" style="font-weight: 600;">{html.escape(ats_result["experience_feedback"])}</p>', unsafe_allow_html=True)

                st.markdown('<p class="field-label">Matched Skills</p>', unsafe_allow_html=True)

                if ats_result["matched_skills"]:
                    matched_html = "".join(
                        f'<span class="skill-badge">{html.escape(skill)}</span>'
                        for skill in ats_result["matched_skills"]
                    )
                    st.markdown(matched_html, unsafe_allow_html=True)
                else:
                    st.markdown('<p class="field-value">No matched skills found.</p>', unsafe_allow_html=True)

                st.markdown('<p class="field-label">Missing Skills / Skill Gap</p>', unsafe_allow_html=True)

                if ats_result["missing_skills"]:
                    missing_html = "".join(
                        f'<span class="skill-badge missing-badge">{html.escape(skill)}</span>'
                        for skill in ats_result["missing_skills"]
                    )
                    st.markdown(missing_html, unsafe_allow_html=True)
                else:
                    st.success("No major skill gap found.")
                    
                if "keyword_matches" in ats_result and ats_result["keyword_matches"]:
                    st.markdown('<p class="field-label">Context Keywords Overlap</p>', unsafe_allow_html=True)
                    st.markdown(", ".join(ats_result["keyword_matches"]))

                st.markdown('<p class="field-label">Recommendations</p>', unsafe_allow_html=True)

                if ats_result["recommendations"]:
                    for rec in ats_result["recommendations"]:
                        st.markdown(
                            f'<p class="field-value">• {html.escape(rec)}</p>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        '<p class="field-value">Candidate profile is well aligned with the job description.</p>',
                        unsafe_allow_html=True,
                    )

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">🕐 Recently Processed Candidates</p>', unsafe_allow_html=True)



    table_rows = []
    if db_ok:
        candidates, err = load_recent_candidates(limit=10)
        if err:
            st.warning(f"Could not load candidates: {err}")
            table_rows = st.session_state.recent_candidates
        elif candidates:
            for c in candidates:
                skills_csv = skills_to_csv(c.get("skills"))
                table_rows.append(
                    {
                        "Name": safe_text(c.get("full_name"), "Unknown"),
                        "Email": safe_text(c.get("email")),
                        "Phone": safe_text(c.get("phone")),
                        "Skills": skills_csv or "—",
                        "Status": "Saved",
                    }
                )
        else:
            table_rows = st.session_state.recent_candidates
    else:
        table_rows = st.session_state.recent_candidates

    if table_rows:
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No candidates processed yet. Upload a resume to get started.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

