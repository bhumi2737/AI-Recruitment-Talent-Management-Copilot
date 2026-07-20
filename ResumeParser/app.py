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
from jd_matcher import calculate_candidate_score

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


# ── Theme Configuration & Custom CSS ──────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "Dark" # Default to Dark Theme as requested

def inject_custom_css():
    theme = st.session_state.theme
    
    if theme == "Dark":
        bg = "#0B1120"
        bg_sec = "#111827"
        card = "#1E293B"
        border = "#334155"
        primary = "#34D399"
        primary_hover = "#10B981"
        sec_accent = "#22D3EE"
        gold = "#FBBF24"
        success = "#22C55E"
        warning = "#F59E0B"
        danger = "#EF4444"
        heading = "#F8FAFC"
        text = "#CBD5E1"
        muted = "#94A3B8"
        btn_prim_bg = "linear-gradient(135deg, #10B981, #34D399)"
        btn_sec_bg = "transparent"
        btn_sec_border = "#34D399"
        btn_sec_text = "#34D399"
        card_border_hover = "#FBBF24"
        card_shadow_hover = "0 0 15px rgba(52, 211, 153, 0.2)"
        hr_color = "#334155"
    else: # Light
        bg = "#F8FAF7"
        bg_sec = "#F3F4F6"
        card = "#FFFFFF"
        border = "#E5E7EB"
        primary = "#047857"
        primary_hover = "#065F46"
        sec_accent = "#10B981"
        gold = "#D4AF37"
        success = "#16A34A"
        warning = "#D97706"
        danger = "#DC2626"
        heading = "#1F2937"
        text = "#374151"
        muted = "#6B7280"
        btn_prim_bg = "#047857"
        btn_sec_bg = "#FFFFFF"
        btn_sec_border = "#D4AF37"
        btn_sec_text = "#D4AF37"
        card_border_hover = "#D4AF37"
        card_shadow_hover = "0 10px 15px -3px rgba(0, 0, 0, 0.1)"
        hr_color = "#E5E7EB"

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

        :root {{
            --bg: {bg};
            --bg-sec: {bg_sec};
            --card: {card};
            --border: {border};
            --primary: {primary};
            --primary-hover: {primary_hover};
            --sec-accent: {sec_accent};
            --gold: {gold};
            --success: {success};
            --warning: {warning};
            --danger: {danger};
            --heading: {heading};
            --text: {text};
            --muted: {muted};
            --btn-prim-bg: {btn_prim_bg};
            --btn-sec-bg: {btn_sec_bg};
            --btn-sec-border: {btn_sec_border};
            --btn-sec-text: {btn_sec_text};
            --card-border-hover: {card_border_hover};
            --card-shadow-hover: {card_shadow_hover};
            --hr-color: {hr_color};
        }}

        /* Animations */
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        @keyframes slideUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes fillProgress {{
            from {{ width: 0; }}
        }}

        /* Base Typography & Backgrounds */
        .stApp, [data-testid="stAppViewContainer"] {{
            background-color: var(--bg) !important;
            color: var(--text) !important;
            font-family: 'Inter', sans-serif !important;
            animation: fadeIn 0.8s ease-in-out;
            transition: background-color 0.4s ease, color 0.4s ease;
        }}

        h1, h2, h3, h4, h5, h6, 
        [data-testid="stMarkdownContainer"] h1, 
        [data-testid="stMarkdownContainer"] h2, 
        [data-testid="stMarkdownContainer"] h3 {{
            font-family: 'Poppins', sans-serif !important;
            color: var(--heading) !important;
        }}

        p, span, div, li {{
            color: var(--text);
            font-family: 'Inter', sans-serif;
        }}
        
        hr {{
            border-color: var(--hr-color) !important;
        }}

        /* Sidebar Styling */
        [data-testid="stSidebar"] {{
            background-color: var(--card) !important;
            border-right: 1px solid var(--border) !important;
            transition: background-color 0.4s ease, border-color 0.4s ease;
        }}

        /* Custom Cards */
        .custom-card {{
            background: var(--card) !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            border: 1px solid var(--border) !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
            margin-bottom: 1rem !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease, background-color 0.4s ease !important;
            animation: slideUp 0.6s ease-out forwards;
            position: relative;
            overflow: hidden;
        }}
        
        /* Light mode specific tiny emerald strip */
        {"" if theme == "Dark" else ".custom-card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 3px; background: var(--primary); }"}

        .custom-card:hover {{
            transform: scale(1.02) !important;
            box-shadow: var(--card-shadow-hover) !important;
            border-color: var(--card-border-hover) !important;
        }}

        /* Selected Card Glow */
        .custom-card.selected {{
            border-color: var(--primary) !important;
            box-shadow: 0 0 15px rgba(52, 211, 153, 0.4) !important;
        }}

        /* Typography Classes */
        .main-heading {{
            font-family: 'Poppins', sans-serif !important;
            font-size: 2.2rem !important;
            font-weight: 800 !important;
            color: var(--heading) !important;
            margin-bottom: 0.25rem !important;
        }}
        .main-subtitle {{
            font-size: 1.1rem !important;
            color: var(--muted) !important;
            margin-bottom: 2rem !important;
        }}
        .card-title {{
            font-family: 'Poppins', sans-serif !important;
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            color: var(--heading) !important;
            margin-bottom: 1rem !important;
        }}

        /* Inputs & Textareas */
        .stTextInput input, .stTextArea textarea, [data-testid="stTextArea"] textarea {{
            background-color: var(--bg-sec) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            font-family: 'Inter', sans-serif !important;
            transition: border-color 0.2s ease, background-color 0.4s ease !important;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus, [data-testid="stTextArea"] textarea:focus {{
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 1px var(--primary) !important;
        }}

        /* Buttons */
        [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primary"] button, div.stButton > button[kind="primary"] {{
            background: var(--btn-prim-bg) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }}
        [data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primary"] button:hover, div.stButton > button[kind="primary"]:hover {{
            opacity: 0.9 !important;
            transform: scale(1.02) !important;
        }}

        div.stButton > button {{
            background-color: var(--btn-sec-bg) !important;
            color: var(--btn-sec-text) !important;
            border: 1px solid var(--btn-sec-border) !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }}
        div.stButton > button:hover {{
            background-color: var(--btn-sec-border) !important;
            color: #ffffff !important;
        }}

        /* File Uploader */
        [data-testid="stFileUploader"] {{
            background-color: var(--bg-sec) !important;
            border: 2px dashed var(--border) !important;
            border-radius: 12px !important;
            padding: 1rem !important;
            transition: border-color 0.2s ease, background-color 0.4s ease !important;
        }}
        [data-testid="stFileUploader"]:hover {{
            border-color: var(--primary) !important;
        }}
        [data-testid="stFileUploader"] section {{
            background-color: transparent !important;
        }}
        [data-testid="stFileUploader"] span, [data-testid="stFileUploader"] small {{
            color: var(--muted) !important;
        }}

        /* Expanders */
        [data-testid="stExpander"] {{
            background-color: var(--bg-sec) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            margin-bottom: 1rem !important;
            transition: background-color 0.4s ease, border-color 0.4s ease;
        }}
        [data-testid="stExpander"] summary {{
            color: var(--heading) !important;
            font-weight: 600 !important;
            font-family: 'Poppins', sans-serif !important;
        }}

        /* Metrics */
        [data-testid="stMetricValue"] {{
            font-family: 'Space Grotesk', sans-serif !important;
            color: var(--heading) !important;
            font-weight: 700 !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: var(--muted) !important;
            font-weight: 600 !important;
        }}

        /* Hide Streamlit Junk */
        header {{ visibility: hidden !important; }}
        footer {{ visibility: hidden !important; }}
        #MainMenu {{ visibility: hidden !important; }}
        
        /* Custom Table */
        .custom-table {{ width: 100% !important; border-collapse: collapse !important; margin-top: 1rem !important; margin-bottom: 1rem !important; border-radius: 8px !important; overflow: hidden !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important; border: none !important; }}
        .custom-table thead {{ background-color: var(--card) !important; border-bottom: 2px solid var(--border) !important; }}
        .custom-table th {{ background-color: var(--card) !important; padding: 0.75rem 1rem !important; text-align: left !important; font-family: 'Poppins', sans-serif !important; font-size: 0.85rem !important; font-weight: 600 !important; color: var(--muted) !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; border: none !important; border-bottom: 2px solid var(--border) !important; }}
        .custom-table tbody tr {{ background-color: var(--bg) !important; transition: background-color 0.2s ease !important; border: none !important; }}
        .custom-table tbody tr:hover {{ background-color: var(--bg-sec) !important; }}
        .custom-table td {{ background-color: transparent !important; padding: 1rem !important; font-size: 0.9rem !important; color: var(--text) !important; vertical-align: middle !important; border: none !important; border-bottom: 1px solid var(--border) !important; }}
        
        /* Utility */
        .skill-badge {{
            display: inline-block;
            background-color: var(--bg-sec);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            margin: 0.2rem 0.25rem 0.2rem 0;
            transition: border-color 0.2s ease, background-color 0.4s ease;
        }}
        .skill-badge:hover {{
            border-color: var(--primary);
        }}
        
        .metric-box {{
            background: var(--bg-sec);
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            border: 1px solid var(--border);
            transition: background-color 0.4s ease;
        }}
        .metric-value {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--primary);
        }}
        .metric-label {{
            font-size: 0.8rem;
            color: var(--muted);
            margin-top: 0.25rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        /* Recommendation Badges */
        .badge-highly-rec {{ background-color: #DCFCE7; color: #166534; border: 1px solid #166534; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; display: inline-block; margin: 0.2rem 0.25rem 0.2rem 0; }}
        .badge-rec {{ background-color: #DBEAFE; color: #1D4ED8; border: 1px solid #1D4ED8; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; display: inline-block; margin: 0.2rem 0.25rem 0.2rem 0; }}
        .badge-consider {{ background-color: #FEF3C7; color: #92400E; border: 1px solid #92400E; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; display: inline-block; margin: 0.2rem 0.25rem 0.2rem 0; }}
        .badge-not-rec {{ background-color: #FEE2E2; color: #991B1B; border: 1px solid #991B1B; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; display: inline-block; margin: 0.2rem 0.25rem 0.2rem 0; }}

        /* Old Badges (for backward compatibility during refactor) */
        .badge-green {{ background-color: rgba(16, 185, 129, 0.1); color: var(--success); border: 1px solid var(--success); padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; display: inline-block; margin: 0.2rem 0.25rem 0.2rem 0; }}
        .badge-blue {{ background-color: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid #3b82f6; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; display: inline-block; margin: 0.2rem 0.25rem 0.2rem 0; }}
        .badge-amber {{ background-color: rgba(245, 158, 11, 0.1); color: var(--warning); border: 1px solid var(--warning); padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; display: inline-block; margin: 0.2rem 0.25rem 0.2rem 0; }}
        .badge-red {{ background-color: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid var(--danger); padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; display: inline-block; margin: 0.2rem 0.25rem 0.2rem 0; }}
        
        .empty-state {{ text-align: center; padding: 3rem 1rem; color: var(--muted); }}
        .empty-state-icon {{ font-size: 3rem; margin-bottom: 1rem; opacity: 0.5; }}
        .empty-state-text {{ font-size: 1.1rem; font-weight: 500; font-family: 'Poppins', sans-serif; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

inject_custom_css()

def custom_progress_bar(label: str, value: int, color: str):
    """Renders a custom HTML progress bar to allow specific colors"""
    safe_val = max(0, min(100, value))
    label_html = f'<div style="font-size: 0.8rem; color: var(--muted); margin-bottom: 0.2rem; font-weight: 600;">{label}</div>' if label else ''
    
    html = f'''<div style="margin-bottom: 1rem;">
{label_html}
<div style="width: 100%; background-color: var(--bg-sec); border-radius: 9999px; height: 8px; overflow: hidden; border: 1px solid var(--border);">
<div style="width: {safe_val}%; background-color: {color}; height: 100%; border-radius: 9999px; transition: width 1s ease-in-out; animation: fillProgress 1s ease-out;"></div>
</div>
</div>'''
    st.markdown(html, unsafe_allow_html=True)

def render_html_table(df):
    """Renders a styled HTML table from a pandas DataFrame"""
    html = '<table class="custom-table">'
    html += "<thead><tr>"
    for col in df.columns:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr>"
        for val in row:
            html += f"<td>{val}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)




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
    custom_progress_bar(f"Processing status: {pct}%", pct, "var(--primary)")

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
    st.markdown("# 📋 RC Recruitment")
    st.markdown("---")

    theme_mode = st.session_state.get("theme", "Dark")
    p_color = "#34D399" if theme_mode == "Dark" else "#059669"
    text_c = "#CBD5E1" if theme_mode == "Dark" else "#334155"
    bg_sec_c = "#111827" if theme_mode == "Dark" else "#F1F5F9"
    
    try:
        from streamlit_option_menu import option_menu
        active_page = option_menu(
            menu_title=None,
            options=["Dashboard", "Resume Upload", "Job Descriptions", "Candidate Matching", "Candidate Details", "Skill Gap Analysis", "Candidate Ranking", "Executive Reports", "Settings"],
            icons=["house", "upload", "briefcase", "handshake", "people", "lightning", "trophy", "file-earmark-text", "gear"],
            default_index=["Dashboard", "Resume Upload", "Job Descriptions", "Candidate Matching", "Candidate Details", "Skill Gap Analysis", "Candidate Ranking", "Executive Reports", "Settings"].index(st.session_state.active_page) if st.session_state.active_page in ["Dashboard", "Resume Upload", "Job Descriptions", "Candidate Matching", "Candidate Details", "Skill Gap Analysis", "Candidate Ranking", "Executive Reports", "Settings"] else 0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent", "border": "none"},
                "icon": {"color": p_color, "font-size": "1.1rem"}, 
                "nav-link": {"font-size": "0.95rem", "text-align": "left", "margin":"0px", "margin-bottom": "0.25rem", "--hover-color": bg_sec_c, "color": text_c},
                "nav-link-selected": {"background-color": p_color, "color": "white", "font-weight": "600"},
            }
        )
    except ImportError:
        # Fallback if not installed
        active_page = st.radio("Navigation", ["Dashboard", "Resume Upload", "Job Descriptions", "Candidate Matching", "Candidate Details", "Skill Gap Analysis", "Candidate Ranking", "Executive Reports", "Settings"], index=0)

    if st.session_state.active_page != active_page:
        st.session_state.active_page = active_page
        if active_page == "Candidates":
            st.session_state.selected_candidate_id = None
        st.rerun()

    st.markdown("---")
    
    # Theme Toggle
    theme_choice = st.radio("Theme", ["Dark", "Light"], index=0 if st.session_state.theme == "Dark" else 1, horizontal=True)
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
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
    
    import database as db_stats
    evals = db_stats.get_all_evaluations(500)
    
    try:
        import db_jobs
        total_jobs = len(db_jobs.get_all_jobs()) if hasattr(db_jobs, "get_all_jobs") else 0
    except:
        total_jobs = 0
        
    avg_ats = round(sum([e["hiring_score"] for e in evals]) / len(evals)) if evals else 0
    selected_cands = len([e for e in evals if e.get("recommendation") in ["Excellent Match", "Highly Recommended"]])
    rejected_cands = len([e for e in evals if e.get("recommendation") in ["Weak Match", "Not Recommended"]])
    reports_gen = len(evals)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    metrics_data = [
        (total_candidates, "Total Candidates"),
        (total_jobs, "Total Jobs"),
        (f"{avg_ats}%", "Avg ATS Score"),
        (selected_cands, "Highly Recommended"),
        (rejected_cands, "Not Recommended"),
        (reports_gen, "Evaluations")
    ]
    for col, (val, label) in zip([m1, m2, m3, m4, m5, m6], metrics_data):
        with col:
            st.markdown(f'''<div class="metric-box" style="padding: 1rem 0.5rem;"><div class="metric-value" style="font-size: 1.4rem;">{val}</div><div class="metric-label" style="font-size: 0.7rem;">{label}</div></div>''', unsafe_allow_html=True)

    st.markdown("---")

    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    import numpy as np
    
    theme = st.session_state.theme
    plotly_template = "plotly_dark" if theme == "Dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)"

    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📈 Hiring Score Trend</p>', unsafe_allow_html=True)
        
        if evals:
            df_trend = pd.DataFrame(evals)
            df_trend["Date"] = pd.to_datetime(df_trend["evaluation_time"]).dt.date
            df_trend = df_trend.groupby("Date").agg({"hiring_score": "mean"}).reset_index()
            fig1 = px.area(df_trend, x="Date", y="hiring_score", template=plotly_template, markers=True)
        else:
            dates = pd.date_range(end=pd.Timestamp.now(), periods=14)
            scores = np.zeros(14)
            df_trend = pd.DataFrame({"Date": dates, "Score": scores})
            fig1 = px.area(df_trend, x="Date", y="Score", template=plotly_template, markers=True)
            
        primary_hex = "#34D399" if theme == "Dark" else "#047857"
        teal_hex = "rgba(20, 184, 166, 0.2)"
        fig1.update_traces(line_color=primary_hex, fillcolor=teal_hex)
        fig1.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, margin=dict(l=0, r=0, t=10, b=0), height=250)
        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
        st.markdown("</div>", unsafe_allow_html=True)
        
    with c2:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">🎯 Recommendation Status</p>', unsafe_allow_html=True)
        if evals:
            rec_counts = {}
            for e in evals:
                rec = e.get("recommendation", "Not Recommended")
                rec_counts[rec] = rec_counts.get(rec, 0) + 1
            rec_data = {"Status": list(rec_counts.keys()), "Count": list(rec_counts.values())}
        else:
            rec_data = {"Status": ["No Data"], "Count": [1]}
            
        fig2 = px.pie(rec_data, values="Count", names="Status", hole=0.6, template=plotly_template,
                      color="Status", color_discrete_map={"Excellent Match": "#10b981", "Highly Recommended": "#34d399", "Recommended": "#3b82f6", "Consider": "#f59e0b", "Weak Match": "#ef4444", "Not Recommended": "#b91c1c", "No Data": "#64748b"})
        fig2.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, margin=dict(l=0, r=0, t=10, b=0), height=250, showlegend=False)
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
        st.markdown("</div>", unsafe_allow_html=True)

    c3, c4 = st.columns([2, 1])
    with c3:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">👥 Recent Candidates</p>', unsafe_allow_html=True)
        recent_candidates = load_candidates("")[:6]
        if recent_candidates:
            df_recent = pd.DataFrame([{
                "Candidate Name": c.get("full_name", "Unknown"),
                "Email": c.get("email", ""),
                "Parsed Date": format_datetime(c.get("updated_at") or c.get("created_at")),
                "Status": '<span class="badge-rec">Saved</span>'
            } for c in recent_candidates])
            render_html_table(df_recent)
        else:
            st.markdown('<div class="empty-state"><div class="empty-state-icon">👥</div><div class="empty-state-text">No Candidates Found</div></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with c4:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">🏆 Top Ranked Candidates</p>', unsafe_allow_html=True)
        if evals:
            top_evals = sorted(evals, key=lambda x: x.get("hiring_score", 0), reverse=True)[:5]
            for idx, e in enumerate(top_evals):
                cand = db_stats.get_candidate_by_id(e.get("candidate_id", ""))
                name = cand.get("full_name", "Unknown") if cand else "Unknown"
                initial = name[0].upper() if name else "U"
                score = e.get("hiring_score", 0)
                st.markdown(f'''
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
                    <div style="display: flex; align-items: center;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background-color: var(--primary); display: flex; align-items: center; justify-content: center; margin-right: 0.8rem; color: white; font-weight: bold; font-size: 0.9rem;">
                            {initial}
                        </div>
                        <div style="font-size: 0.9rem; font-weight: 600; color: var(--text);">{html.escape(name)}</div>
                    </div>
                    <div style="font-weight: 700; color: var(--primary);">{score}%</div>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty-state"><div class="empty-state-icon">🏆</div><div class="empty-state-text">No Rankings Yet</div></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


elif active_page == "Candidate Details":
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
            
            import plotly.express as px
            import plotly.graph_objects as go
            import pandas as pd
            import numpy as np
            
            theme = st.session_state.theme
            plotly_template = "plotly_dark" if theme == "Dark" else "plotly_white"
            bg_color = "rgba(0,0,0,0)"
            
            import db_jobs
            jds = db_jobs.get_all_jobs()
            if not jds:
                st.info("No Job Descriptions available to evaluate against. Please create one.")
                st.stop()
            
            st.markdown("#### Evaluate Candidate")
            jd_options = {jd["job_id"]: f"{jd['job_title']} at {jd.get('company_name', 'Unknown')}" for jd in jds}
            selected_jd_id = st.selectbox("Select a Job Description for ATS Scoring", options=list(jd_options.keys()), format_func=lambda x: jd_options[x], key=f"details_jd_select_{candidate.get('_id', '')}")
            selected_job = next((j for j in jds if j["job_id"] == selected_jd_id), jds[0])
            
            ats_result = calculate_candidate_score(candidate, selected_job)
            actual_ats = ats_result.get("hiring_score", 0)
            breakdown = ats_result.get("score_breakdown", {})
            
            # Header with Avatar and ATS Gauge
            h_col1, h_col2 = st.columns([3, 1])
            with h_col1:
                name = html.escape(safe_text(candidate.get("full_name"), "Unknown"))
                initial = name[0].upper() if name else "U"
                st.markdown(f'''
                <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                    <div style="width: 80px; height: 80px; border-radius: 50%; background-color: var(--primary); display: flex; align-items: center; justify-content: center; margin-right: 1.5rem; color: white; font-weight: 700; font-size: 2.5rem; border: 3px solid var(--border);">
                        {initial}
                    </div>
                    <div>
                        <h2 style="margin: 0; padding: 0; color: var(--heading);">{name}</h2>
                        <p style="color: var(--muted); font-size: 1.1rem; margin-top: 0.2rem;">📧 {html.escape(safe_text(candidate.get("email")))} &nbsp;&nbsp;|&nbsp;&nbsp; 📱 {html.escape(safe_text(candidate.get("phone")))}</p>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
            with h_col2:
                fig_ats = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=actual_ats,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "ATS Score", 'font': {'size': 12}},
                    gauge={
                        'axis': {'range': [0, 100], 'tickwidth': 1},
                        'bar': {'color': "var(--primary)"},
                        'bgcolor': "var(--bg-sec)",
                        'borderwidth': 0
                    }
                ))
                fig_ats.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=140, paper_bgcolor="rgba(0,0,0,0)", font={'color': "var(--text)"})
                st.plotly_chart(fig_ats, use_container_width=True, config={'displayModeBar': False})

            st.markdown("---")
            
            # Radar Chart and Skills
            r_col1, r_col2 = st.columns([1, 1])
            with r_col1:
                st.markdown('<p class="card-title">📊 Competency Radar</p>', unsafe_allow_html=True)
                categories = ['Skills', 'Experience', 'Education', 'Projects', 'Certifications']
                values = [
                    breakdown.get("skill_match", 0),
                    breakdown.get("experience_match", 0),
                    breakdown.get("education_match", 0),
                    breakdown.get("project_relevance", 0),
                    breakdown.get("certification_match", 0)
                ]
                fig_radar = go.Figure(data=go.Scatterpolar(
                    r=values + [values[0]],
                    theta=categories + [categories[0]],
                    fill='toself',
                    fillcolor="rgba(16, 185, 129, 0.2)",
                    line_color="var(--primary)"
                ))
                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 100]),
                        bgcolor=bg_color
                    ),
                    showlegend=False,
                    paper_bgcolor=bg_color,
                    plot_bgcolor=bg_color,
                    margin=dict(l=30, r=30, t=30, b=30),
                    height=300
                )
                st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})
                
            with r_col2:
                st.markdown('<p class="card-title">🎯 Top Skills</p>', unsafe_allow_html=True)
                skills_list = candidate.get("skills")
                if isinstance(skills_list, str):
                    skills_list = [s.strip() for s in skills_list.split(",") if s.strip()]
                elif not skills_list:
                    skills_list = []
                
                s_html = "".join([f'<span class="badge-blue">{html.escape(s)}</span>' for s in skills_list[:25]])
                st.markdown(s_html if s_html else '<span class="badge-amber">None</span>', unsafe_allow_html=True)

            st.markdown("---")
            
            # Timelines
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.markdown("#### 🎓 Education Timeline")
                edu_text = html.escape(safe_text(candidate.get("education"), "No education found")).replace("\n", "<br>")
                st.markdown(f'<div style="border-left: 2px solid var(--primary); padding-left: 1rem; margin-left: 0.5rem; margin-bottom: 1.5rem;"><p style="white-space: pre-wrap;">{edu_text}</p></div>', unsafe_allow_html=True)
                
                st.markdown("#### 🏆 Certifications")
                cert_text = html.escape(safe_text(candidate.get("certifications"), "None")).replace("\n", "<br>")
                st.markdown(f'<div style="background: var(--bg-sec); padding: 1rem; border-radius: 8px; border: 1px solid var(--border);"><p style="white-space: pre-wrap;">{cert_text}</p></div>', unsafe_allow_html=True)
                
            with t_col2:
                st.markdown("#### 💼 Work Experience Timeline")
                exp_text = html.escape(safe_text(candidate.get("experience"), "No experience found")).replace("\n", "<br>")
                st.markdown(f'<div style="border-left: 2px solid var(--primary); padding-left: 1rem; margin-left: 0.5rem; margin-bottom: 1.5rem;"><p style="white-space: pre-wrap;">{exp_text}</p></div>', unsafe_allow_html=True)
                
                st.markdown("#### 🛠 Projects")
                proj_text = html.escape(safe_text(candidate.get("projects"), "None")).replace("\n", "<br>")
                st.markdown(f'<div style="background: var(--bg-sec); padding: 1rem; border-radius: 8px; border: 1px solid var(--border);"><p style="white-space: pre-wrap;">{proj_text}</p></div>', unsafe_allow_html=True)

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


elif active_page == "Job Descriptions":
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
        import plotly.express as px
        import pandas as pd
        import numpy as np
        theme = st.session_state.theme
        plotly_template = "plotly_dark" if theme == "Dark" else "plotly_white"
        bg_color = "rgba(0,0,0,0)"

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
            col_j1, col_j2 = st.columns([2, 1])

            with col_j1:
                st.markdown(f"### {html.escape(title)}")
                st.markdown(
                    f"🏢 **{html.escape(company)}** &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"📍 {html.escape(loc)} &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"💼 {html.escape(exp)} &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"💰 {html.escape(sal)}",
                    unsafe_allow_html=True,
                )
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Mock Required vs Optional donut
                fig_donut = px.pie(
                    names=["Required Skills", "Optional Skills"],
                    values=[len(skills), max(2, int(len(skills)*0.4))],
                    hole=0.7, template=plotly_template,
                    color_discrete_sequence=["#3b82f6", "#94a3b8"]
                )
                fig_donut.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, margin=dict(l=0, r=0, t=0, b=0), height=150, showlegend=True)
                st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False}, key=f"donut_{jid}_{idx}")
                
                if desc:
                    with st.expander("📄 View Job Description Text"):
                        st.write(desc)

            with col_j2:
                st.markdown('<p class="field-label">Required Skills Profile</p>', unsafe_allow_html=True)
                if skills:
                    df_skills = pd.DataFrame({"Skill": skills, "Importance": np.random.randint(60, 100, size=len(skills))})
                    df_skills = df_skills.sort_values(by="Importance", ascending=True)
                    primary_hex = "#34D399" if theme == "Dark" else "#047857"
                    teal_hex = "#0f766e" if theme == "Dark" else "#14b8a6"
                    fig_bar = px.bar(df_skills, x="Importance", y="Skill", orientation="h", template=plotly_template, color="Importance", color_continuous_scale=[teal_hex, primary_hex])
                    fig_bar.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, margin=dict(l=0, r=0, t=0, b=0), height=200, coloraxis_showscale=False)
                    st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False}, key=f"bar_{jid}_{idx}")
                else:
                    st.info("No skills specified.")

                match_btn_key = f"match_j_{jid}_{idx}"
                first_skill = skills[0] if skills else ""
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("🔍 Match", key=match_btn_key, use_container_width=True, type="primary"):
                        st.session_state.active_page = "Candidate Matching"
                        st.session_state.selected_candidate_id = None
                        st.session_state.search_filter = first_skill
                        st.rerun()
                with b2:
                    delete_btn_key = f"delete_j_{jid}_{idx}"
                    if st.button("🗑️ Delete", key=delete_btn_key, use_container_width=True, type="secondary"):
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


elif active_page == "Skill Gap Analysis":
    st.markdown('<p class="main-heading">Skill Gap Analysis</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Identify missing competencies across your talent pool</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">🔍 Talent Pool Skill Coverage</p>', unsafe_allow_html=True)
    
    import plotly.express as px
    import pandas as pd
    import numpy as np
    theme = st.session_state.theme
    plotly_template = "plotly_dark" if theme == "Dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)"
    
    candidates = load_candidates("")
    import db_jobs
    jds = db_jobs.get_all_jobs()
    if not candidates:
        st.info("No candidates available for gap analysis.")
        st.stop()
    if not jds:
        st.info("No Job Descriptions available for gap analysis.")
        st.stop()

    jd_options = {jd["job_id"]: f"{jd['job_title']} at {jd.get('company_name', 'Unknown')}" for jd in jds}
    selected_jd_id = st.selectbox("Select a Job Description to Analyze Gaps against", options=list(jd_options.keys()), format_func=lambda x: jd_options[x], key="gap_jd_select")
    selected_job = next((j for j in jds if j["job_id"] == selected_jd_id), jds[0])

    missing_counts = {}
    for c in candidates:
        ats_result = calculate_candidate_score(c, selected_job)
        missing = ats_result.get("missing_skills", [])
        for skill in missing:
            missing_counts[skill] = missing_counts.get(skill, 0) + 1

    if not missing_counts:
        st.success("No skill gaps found in the current talent pool for this job!")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    sorted_gaps = sorted(missing_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    total_candidates = len(candidates)
    
    gap_data = []
    for skill, count in sorted_gaps:
        gap_data.append({
            "Skill": skill,
            "Gap Percentage": round((count / total_candidates) * 100)
        })

    df_gaps = pd.DataFrame(gap_data).sort_values("Gap Percentage", ascending=True)
    
    primary_hex = "#34D399" if theme == "Dark" else "#047857"
    teal_hex = "#0f766e" if theme == "Dark" else "#14b8a6"
    fig_gap = px.bar(df_gaps, x="Gap Percentage", y="Skill", orientation='h', template=plotly_template, title="Highest Skill Gaps", color="Gap Percentage", color_continuous_scale=[primary_hex, teal_hex])
    fig_gap.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, margin=dict(l=0, r=0, t=30, b=0), height=250, coloraxis_showscale=False)
    st.plotly_chart(fig_gap, use_container_width=True, config={'displayModeBar': False})
    st.markdown("#### ?? Recommended Learning Roadmap")
    roadmap_html = ""
    for idx, row in df_gaps.sort_values("Gap Percentage", ascending=False).iterrows():
        pct = row["Gap Percentage"]
        color = "#ef4444" if pct > 70 else "#f59e0b"
        roadmap_html += f"""
        <div style="border-left: 2px solid {color}; padding-left: 1rem; margin-bottom: 1rem;">
            <strong>{row["Skill"]} ({pct}% Gap)</strong><br>
            <span style="color: var(--muted); font-size: 0.9rem;">Consider providing training or sourcing candidates specifically with {row["Skill"]} expertise.</span>
        </div>
        """
    st.markdown(roadmap_html, unsafe_allow_html=True)
elif active_page == "Candidate Ranking":
    st.markdown('<p class="main-heading">Candidate Rankings</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Global leaderboard of top talent</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">🏆 Top Candidate Leaderboard</p>', unsafe_allow_html=True)
    
    import pandas as pd
    import numpy as np
    import plotly.express as px
    theme = st.session_state.theme
    plotly_template = "plotly_dark" if theme == "Dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)"
    
    candidates = load_candidates("")
    import db_jobs
    jds = db_jobs.get_all_jobs()
    if not candidates:
        st.info("No candidates available for ranking.")
        st.stop()
    if not jds:
        st.info("No Job Descriptions available to rank candidates against. Please create one first.")
        st.stop()
        
    jd_options = {jd["job_id"]: f"{jd['job_title']} at {jd.get('company_name', 'Unknown')}" for jd in jds}
    selected_jd_id = st.selectbox("Select a Job Description to Rank Candidates against", options=list(jd_options.keys()), format_func=lambda x: jd_options[x], key="rank_jd_select")
    selected_job = next((j for j in jds if j["job_id"] == selected_jd_id), jds[0])
          
    rank_data = []
    for c in candidates:
        ats_result = calculate_candidate_score(c, selected_job)
        score = ats_result.get("hiring_score", 0)
        status = ats_result.get("recommendation", "Not Recommended")
        
        if status in ["Excellent Match", "Highly Recommended"]:
            badge = f'<span class="badge-green">{status}</span>'
        elif status == "Recommended":
            badge = f'<span class="badge-blue">{status}</span>'
        elif status == "Consider":
            badge = f'<span class="badge-amber">{status}</span>'
        else:
            badge = f'<span class="badge-red">{status}</span>'
            
        rank_data.append({
            "Candidate": c.get("full_name") or "Unknown",
            "Hiring Score": score,
            "Status": badge
        })
        
    df_rank = pd.DataFrame(rank_data).sort_values("Hiring Score", ascending=False).reset_index(drop=True)
    df_rank.insert(0, "Rank", df_rank.index + 1)
    df_rank = df_rank.head(10)
    
    render_html_table(df_rank)
    
    st.markdown("<br>", unsafe_allow_html=True)
    primary_hex = "#34D399" if theme == "Dark" else "#047857"
    teal_hex = "#0f766e" if theme == "Dark" else "#14b8a6"
    fig_rank = px.bar(df_rank, x="Candidate", y="Hiring Score", template=plotly_template, color="Hiring Score", color_continuous_scale=[teal_hex, primary_hex])
    fig_rank.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, margin=dict(l=0, r=0, t=10, b=0), height=300, coloraxis_showscale=False)
    st.plotly_chart(fig_rank, use_container_width=True, config={'displayModeBar': False})
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()
    
elif active_page == "Executive Reports":
    st.markdown('<p class="main-heading">Executive Summary</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">High-level insights and automated recruitment reports</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">?? Recruitment Analytics Report</p>', unsafe_allow_html=True)
    
    import db_jobs
    jds = db_jobs.get_all_jobs()
    candidates = load_candidates("")
    import database as db_stats
    evals = db_stats.get_all_evaluations(100)
    total_evals = len(evals)
    avg_hiring_score = round(sum([e["hiring_score"] for e in evals]) / total_evals) if total_evals > 0 else 0
    
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        st.markdown("#### ? Key Metrics")
        st.markdown(f"""
        - **Total Active Jobs:** {len(jds)}
        - **Total Talent Pool:** {len(candidates)} candidates.
        - **Evaluations Processed:** {total_evals}
        - **Average Hiring Score:** {avg_hiring_score} / 100
        """)
    with r_col2:
        st.markdown("#### ?? Pipeline Status")
        st.markdown("""
        - **Top Matches:** Highly Recommended candidates are automatically flagged in rankings.
        - **Skill Gaps:** Check the Skill Gap Analysis tab to identify missing competencies.
        - **Diversity:** Continue broad sourcing to expand talent pool diversity.
        """)
        
    st.markdown("---")
    st.button("?? Download PDF Report", type="primary")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

elif active_page == "Candidate Matching":
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
        
        if st.button("🔍 Run Matching Engine", type="primary"):
            with st.spinner("Analyzing candidate pool against requirements..."):
                results = compare_candidates_with_jd(selected_jd_id)
                
            if results:
                st.success(f"Successfully evaluated {len(results)} candidates.")
                
                for res in results:
                    pct = res["match_percentage"]
                    name = html.escape(res["candidate_name"])
                    initial = name[0].upper() if name else "U"
                    matched = res["matched_skills"] or []
                    missing = res["missing_skills"] or []
                    additional = res["additional_skills"] or []
                    
                    rec = res.get("recommendation", "")
                    if rec in ["Excellent Match", "Highly Recommended"]:
                        badge = f'<span class="badge-green">{rec}</span>'
                    elif rec == "Recommended":
                        badge = f'<span class="badge-blue">{rec}</span>'
                    elif rec == "Consider":
                        badge = f'<span class="badge-amber">{rec}</span>'
                    else:
                        badge = f'<span class="badge-red">{rec}</span>'

                    st.markdown('<div class="custom-card" style="margin-top: 1rem;">', unsafe_allow_html=True)
                    st.markdown(f'''
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
                        <div style="display: flex; align-items: center;">
                            <div style="width: 48px; height: 48px; border-radius: 50%; background-color: var(--primary); display: flex; align-items: center; justify-content: center; margin-right: 1rem; color: white; font-weight: 700; font-size: 1.2rem; border: 2px solid var(--border);">
                                {initial}
                            </div>
                            <div>
                                <h3 style="margin: 0; padding: 0; color: var(--heading);">{name}</h3>
                                {badge}
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.8rem; font-weight: 800; font-family: 'Space Grotesk', sans-serif; color: var(--primary);">{pct}%</div>
                            <div style="font-size: 0.8rem; color: var(--muted); text-transform: uppercase;">Match Score</div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                    
                    custom_progress_bar("", pct, "var(--primary)")
                    
                    m_html = "".join([f'<span class="badge-green">{html.escape(s)}</span>' for s in matched])
                    x_html = "".join([f'<span class="badge-red">{html.escape(s)}</span>' for s in missing])
                    a_html = "".join([f'<span class="badge-blue">{html.escape(s)}</span>' for s in additional[:5]])
                    
                    b1, b2, b3 = st.columns(3)
                    with b1:
                        st.markdown("#### ✅ Matched Skills")
                        st.markdown(m_html if m_html else '<span class="badge-amber">None</span>', unsafe_allow_html=True)
                    with b2:
                        st.markdown("#### ❌ Missing Skills")
                        st.markdown(x_html if x_html else '<span class="badge-amber">None</span>', unsafe_allow_html=True)
                    with b3:
                        st.markdown("#### ➕ Additional Skills")
                        st.markdown(a_html if a_html else '<span class="badge-amber">None</span>', unsafe_allow_html=True)
                        
                    st.markdown('</div>', unsafe_allow_html=True)
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
        
        # Completeness Gauge and Basic Info
        comp_col, info_col = st.columns([1, 2])
        with comp_col:
            import plotly.graph_objects as go
            completeness = int(st.session_state.last_accuracy)
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=completeness,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Completeness", 'font': {'size': 14}},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1},
                    'bar': {'color': "var(--primary)"},
                    'bgcolor': "var(--bg-sec)",
                    'borderwidth': 0,
                    'steps': [
                        {'range': [0, 50], 'color': "rgba(239, 68, 68, 0.2)"},
                        {'range': [50, 80], 'color': "rgba(245, 158, 11, 0.2)"},
                        {'range': [80, 100], 'color': "rgba(16, 185, 129, 0.2)"}
                    ]
                }
            ))
            fig_gauge.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=180, paper_bgcolor="rgba(0,0,0,0)", font={'color': "var(--text)"})
            st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})
            
        with info_col:
            st.markdown(f'<p style="font-size: 1.5rem; font-weight: 700; margin-bottom: 0;">{html.escape(safe_text(profile.get("full_name"), "Unknown"))}</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="color: var(--muted); margin-bottom: 1rem;">📧 {html.escape(safe_text(profile.get("email")))} | 📱 {html.escape(safe_text(profile.get("phone")))}</p>', unsafe_allow_html=True)
            
            skills_html = "".join([f'<span class="badge-blue">{html.escape(s)}</span>' for s in profile.get("skills", [])[:15]])
            st.markdown(skills_html, unsafe_allow_html=True)

        st.markdown("---")

        detail_col1, detail_col2 = st.columns(2)
        with detail_col1:
            st.markdown("#### 🎓 Education Timeline")
            edu_text = html.escape(safe_text(profile.get("education"), "No education found")).replace("\n", "<br>")
            st.markdown(f'<div style="border-left: 2px solid var(--primary); padding-left: 1rem; margin-left: 0.5rem; margin-bottom: 1.5rem;"><p style="white-space: pre-wrap;">{edu_text}</p></div>', unsafe_allow_html=True)
            
            st.markdown("#### 🏆 Certifications")
            cert_text = html.escape(safe_text(profile.get("certifications"), "None")).replace("\n", "<br>")
            st.markdown(f'<div style="background: var(--bg-sec); padding: 1rem; border-radius: 8px; border: 1px solid var(--border);"><p style="white-space: pre-wrap;">{cert_text}</p></div>', unsafe_allow_html=True)
            
        with detail_col2:
            st.markdown("#### 💼 Work Experience Timeline")
            exp_text = html.escape(safe_text(profile.get("experience"), "No experience found")).replace("\n", "<br>")
            st.markdown(f'<div style="border-left: 2px solid var(--primary); padding-left: 1rem; margin-left: 0.5rem; margin-bottom: 1.5rem;"><p style="white-space: pre-wrap;">{exp_text}</p></div>', unsafe_allow_html=True)
            
            st.markdown("#### 🛠 Projects")
            proj_text = html.escape(safe_text(profile.get("projects"), "None")).replace("\n", "<br>")
            st.markdown(f'<div style="background: var(--bg-sec); padding: 1rem; border-radius: 8px; border: 1px solid var(--border);"><p style="white-space: pre-wrap;">{proj_text}</p></div>', unsafe_allow_html=True)

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
                import json
                import pandas as pd
                import plotly.express as px
                
                if selected_job:
                    # Run structured match
                    ats_result = calculate_candidate_score(profile, selected_job)
                else:
                    # Run generic text match
                    # Since calculate_ats_score might not have the new fields, let's wrap the generic text in a mock job and use calculate_candidate_score
                    mock_job = {"job_id": "CUSTOM-TEXT", "job_description": job_description}
                    ats_result = calculate_candidate_score(profile, mock_job)

                # Save evaluation to database
                if db_ok and profile.get("email"):
                    db.save_evaluation(
                        ats_result["job_id"], 
                        profile.get("email"), 
                        ats_result["hiring_score"], 
                        ats_result["recommendation"], 
                        ats_result["score_breakdown"]
                    )

                # Candidate Card UI
                badge_color_map = {
                    "Highly Recommended": "var(--green)",
                    "Recommended": "var(--blue)",
                    "Consider": "#ca8a04", # Yellow
                    "Not Recommended": "var(--red)"
                }
                rec_color = badge_color_map.get(ats_result["recommendation"], "var(--muted)")

                st.markdown(
                    f"""
                    <div style="background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-top: 1rem; transition: transform 0.2s ease-in-out;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                            <div>
                                <h3 style="margin: 0; font-size: 1.5rem; font-weight: 800; color: var(--text);">{html.escape(safe_text(profile.get("full_name"), "Unknown Candidate"))}</h3>
                                <p style="margin: 0; color: var(--muted); font-size: 0.9rem;">Job ID: {html.escape(ats_result["job_id"])}</p>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 2.5rem; font-weight: 900; color: {rec_color}; line-height: 1;">{ats_result["hiring_score"]}</div>
                                <div style="font-size: 0.8rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em;">Hiring Score</div>
                            </div>
                        </div>
                        <div style="margin-bottom: 1.5rem;">
                            <span style="background-color: {rec_color}; color: white; padding: 0.3rem 0.8rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 700; display: inline-block;">
                                {ats_result["recommendation"]}
                            </span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("### Score Breakdown")
                
                # Progress Bars for Score Breakdown
                breakdown = ats_result["score_breakdown"]
                metrics = [
                    ("Skill Match (50%)", breakdown["skill_match"], "var(--success)"),
                    ("Experience Fit (20%)", breakdown["experience_match"], "#0ea5e9"),
                    ("Education Fit (10%)", breakdown["education_match"], "#6366f1"),
                    ("Project Relevance (10%)", breakdown["project_relevance"], "var(--gold)"),
                    ("Certification Match (10%)", breakdown["certification_match"], "#14b8a6")
                ]
                
                for label, value, color in metrics:
                    custom_progress_bar(f"{label} - {value}%", value, color)
                
                # Plotly Horizontal Bar Chart
                df_chart = pd.DataFrame({
                    "Metric": ["Skill", "Experience", "Education", "Projects", "Certifications"],
                    "Score": [breakdown["skill_match"], breakdown["experience_match"], breakdown["education_match"], breakdown["project_relevance"], breakdown["certification_match"]]
                })
                
                theme = st.session_state.theme
                plotly_template = "plotly_dark" if theme == "Dark" else "plotly_white"
                primary_color = "#34D399" if theme == "Dark" else "#047857"
                
                teal_color = "#0f766e" if theme == "Dark" else "#14b8a6"
                fig = px.bar(
                    df_chart, 
                    x="Score", 
                    y="Metric", 
                    orientation='h',
                    template=plotly_template,
                    color="Score",
                    color_continuous_scale=[teal_color, primary_color]
                )
                fig.update_layout(coloraxis_showscale=False)
                fig.update_traces(marker_line_width=0)
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=0, r=0, t=10, b=0),
                    height=200,
                    xaxis=dict(range=[0, 100])
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                with st.expander("🤔 How was this score calculated?"):
                    st.markdown(
                        f"""
                        - **Skill Match (50%):** {breakdown['skill_match']}% - Based on matching candidate skills with required job skills.
                        - **Experience (20%):** {breakdown['experience_match']}% - Evaluated against the required {html.escape(selected_job.get("experience_required", "") if selected_job else "experience")}.
                        - **Education (10%):** {breakdown['education_match']}% - Based on presence of education section.
                        - **Projects (10%):** {breakdown['project_relevance']}% - Measured by context overlap with Job Description keywords.
                        - **Certifications (10%):** {breakdown['certification_match']}% - Relevant certifications matched.
                        """
                    )

                with st.expander("🛠️ Skill Gap Analysis"):
                    col_sk1, col_sk2, col_sk3 = st.columns(3)
                    with col_sk1:
                        st.markdown("**✅ Matched Skills**")
                        if ats_result["matched_skills"]:
                            for sk in ats_result["matched_skills"]:
                                st.markdown(f"- {sk}")
                        else:
                            st.write("None")
                    with col_sk2:
                        st.markdown("**❌ Missing Skills**")
                        if ats_result["missing_skills"]:
                            for sk in ats_result["missing_skills"]:
                                st.markdown(f"- {sk}")
                        else:
                            st.write("None")
                    with col_sk3:
                        st.markdown("**🌟 Extra Skills**")
                        if ats_result["extra_skills"]:
                            for sk in ats_result["extra_skills"][:10]: # Limit to 10
                                st.markdown(f"- {sk}")
                            if len(ats_result["extra_skills"]) > 10:
                                st.markdown(f"- ...and {len(ats_result['extra_skills'])-10} more")
                        else:
                            st.write("None")

                with st.expander("💡 Recommendations"):
                    if ats_result["recommendations"]:
                        for rec in ats_result["recommendations"]:
                            st.markdown(f"- {html.escape(rec)}")
                    else:
                        st.write("Candidate profile is well aligned with the job description.")

                # Download Skill Gap Report
                report_content = f"Skill Gap Report for {profile.get('full_name', 'Unknown')}\n"
                report_content += f"Job ID: {ats_result['job_id']}\n"
                report_content += f"Hiring Score: {ats_result['hiring_score']}\n"
                report_content += f"Recommendation: {ats_result['recommendation']}\n\n"
                report_content += "Breakdown:\n"
                for k, v in ats_result["score_breakdown"].items():
                    report_content += f"- {k}: {v}%\n"
                report_content += "\nMissing Skills:\n"
                report_content += ", ".join(ats_result["missing_skills"]) if ats_result["missing_skills"] else "None"
                
                st.download_button(
                    label="📥 Download Skill Gap Report",
                    data=report_content,
                    file_name=f"Skill_Gap_Report_{profile.get('full_name', 'candidate').replace(' ', '_')}.txt",
                    mime="text/plain",
                    use_container_width=True
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
        import pandas as pd
        df_settings = pd.DataFrame(table_rows)
        render_html_table(df_settings)
    else:
        st.info("No candidates processed yet. Upload a resume to get started.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

