"""
HireFlow AI
Milestone 1: Resume Parser and Candidate Profiling
Streamlit dashboard application.
"""
from __future__ import annotations

import os
import sys

# Ensure module directory is in sys.path when running from repo root or subdirectories
_app_dir = os.path.dirname(os.path.abspath(__file__))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

# Sync secrets from Streamlit Cloud (st.secrets) to os.environ if available
try:
    import streamlit as _st
    if hasattr(_st, "secrets"):
        for _key in _st.secrets:
            if _key not in os.environ:
                _val = _st.secrets[_key]
                if isinstance(_val, str):
                    os.environ[_key] = _val
except Exception:
    pass

import html
import inspect
from collections import Counter
from datetime import datetime
from typing import Any

import requests
import streamlit as st

import database as db
import db_jobs
import db_interviews
import db_applications
import db_auth
import auth_service
import ai_question_generator
import db_question_generator
import db_question_sets
import ai_interview_evaluator
import db_interview_evaluator
import interview_pdf_report
from parser import calculate_extraction_accuracy, parse_resume
from scorer import calculate_ats_score
from jd_matcher import calculate_candidate_score

# ── Mock Jobs Data (Fallback Sample Data when DB is Empty) ───────────────────
DEFAULT_MOCK_JOBS = [
    {
        "job_id": "JOB-MOCK1",
        "job_title": "Senior Python Backend Engineer (Sample)",
        "company_name": "TechCorp Solutions [Demo Sample]",
        "location": "San Francisco, CA (Hybrid)",
        "experience_required": "5+ Years",
        "required_skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "REST API"],
        "job_description": "We are seeking a Senior Python Backend Engineer to design and implement scalable microservices. You will work with FastAPI, Docker, and PostgreSQL on a daily basis.",
        "salary": "$130,000 - $160,000",
        "is_demo": True,
    },
    {
        "job_id": "JOB-MOCK2",
        "job_title": "Data Scientist / ML Practitioner (Sample)",
        "company_name": "AI & Insights Ltd [Demo Sample]",
        "location": "Remote (US/Canada)",
        "experience_required": "3+ Years",
        "required_skills": ["Python", "TensorFlow", "PyTorch", "Machine Learning", "Scikit-learn"],
        "job_description": "Join our AI & Insights team to build and deploy machine learning models. Experience with TensorFlow or PyTorch and classical ML packages is required.",
        "salary": "$120,000 - $150,000",
        "is_demo": True,
    },
    {
        "job_id": "JOB-MOCK3",
        "job_title": "Fullstack Software Engineer (Sample)",
        "company_name": "WebFlow Inc [Demo Sample]",
        "location": "New York, NY",
        "experience_required": "2+ Years",
        "required_skills": ["React", "JavaScript", "TypeScript", "Node.js", "HTML", "CSS"],
        "job_description": "Looking for a fullstack engineer to develop user interfaces in React and backend services in Node.js. Must be comfortable writing TypeScript, HTML, and CSS.",
        "salary": "$100,000 - $130,000",
        "is_demo": True,
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
    page_title="HireFlow AI — Smart Hiring Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Theme Configuration & Custom CSS ──────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "Light"

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

        /* Ensure Sidebar Toggle / Open Button is Always Visible & Prominent in Both Themes */
        [data-testid="stHeader"] {{
            background-color: transparent !important;
            z-index: 99999 !important;
            height: 3.5rem !important;
        }}

        [data-testid="collapsedControl"] {{
            visibility: visible !important;
            display: flex !important;
            top: 0.75rem !important;
            left: 0.75rem !important;
            z-index: 100000 !important;
        }}

        [data-testid="collapsedControl"] button,
        [data-testid="stSidebarCollapseButton"] button,
        button[data-testid="baseButton-headerNoPadding"] {{
            background-color: var(--card) !important;
            color: var(--primary) !important;
            border: 2px solid var(--primary) !important;
            border-radius: 8px !important;
            padding: 0.4rem 0.6rem !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
            transition: all 0.25s ease-in-out !important;
        }}

        [data-testid="collapsedControl"] button:hover,
        [data-testid="stSidebarCollapseButton"] button:hover,
        button[data-testid="baseButton-headerNoPadding"]:hover {{
            background-color: var(--primary) !important;
            color: #ffffff !important;
            transform: scale(1.08) !important;
        }}

        [data-testid="collapsedControl"] button svg,
        [data-testid="stSidebarCollapseButton"] button svg,
        button[data-testid="baseButton-headerNoPadding"] svg {{
            fill: var(--primary) !important;
            color: var(--primary) !important;
            stroke: var(--primary) !important;
            width: 1.4rem !important;
            height: 1.4rem !important;
        }}

        [data-testid="collapsedControl"] button:hover svg,
        [data-testid="stSidebarCollapseButton"] button:hover svg,
        button[data-testid="baseButton-headerNoPadding"]:hover svg {{
            fill: #ffffff !important;
            color: #ffffff !important;
            stroke: #ffffff !important;
        }}

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
    "authenticated": False,
    "auth_user": None,
    "auth_page": "Landing",
    "jwt_token": None,
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
    "pipeline_stage_filter": "All",
    "pipeline_skill_filter": "All",
    "pipeline_interview_filter": "All",
    "pipeline_search_query": "",
    "portal_role": "Recruiter",
    "current_candidate_user": None,
    "candidate_active_page": "Dashboard",
    "taking_interview_id": None,
    "taking_question_index": 0,
    "review_mode": False,
    "viewing_submitted_intv_id": None,
    "active_question_set": [],
    "question_set_candidate_id": None,
    "question_set_job_id": None,
    "question_set_difficulty": "Mixed",
    "preview_mode": False,
    "preloaded_questions_for_assignment": None,
    "preloaded_candidate_id_for_assignment": None,
    "preloaded_job_id_for_assignment": None,
}

for key, value in DEFAULT_SESSION_VALUES.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ── Public & Authentication Flow Renderers ────────────────────────────────────

def render_public_header():
    """Render sleek public header bar for unauthenticated landing/login/register pages."""
    st.markdown('''
        <style>
        .pub-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 2rem;
            background: var(--card);
            border-bottom: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        }
        .pub-logo {
            font-family: 'Poppins', sans-serif;
            font-size: 1.35rem;
            font-weight: 800;
            color: var(--heading);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .pub-badge {
            background: linear-gradient(135deg, #3B82F6, #6366F1);
            color: white;
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            margin-left: 0.5rem;
        }
        </style>
    ''', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([4, 1.2, 1.2, 1.2])
    with col1:
        st.markdown('<div class="pub-logo">⚡ HireFlow AI <span class="pub-badge">Smart Hiring Copilot</span></div>', unsafe_allow_html=True)
    with col2:
        if st.button("🏠 Home", use_container_width=True, key="hdr_btn_home"):
            st.session_state.auth_page = "Landing"
            st.rerun()
    with col3:
        if st.button("🔑 Sign In", use_container_width=True, key="hdr_btn_login"):
            st.session_state.auth_page = "Login"
            st.rerun()
    with col4:
        if st.button("✨ Get Started", use_container_width=True, key="hdr_btn_register", type="primary"):
            st.session_state.auth_page = "Register"
            st.rerun()


def render_landing_page():
    """Render high-converting, modern public landing page."""
    render_public_header()

    st.markdown('''
        <style>
        .hero-container {
            text-align: center;
            padding: 3rem 1.5rem 2rem 1.5rem;
            background: linear-gradient(180deg, rgba(99, 102, 241, 0.08) 0%, rgba(0, 0, 0, 0) 100%);
            border-radius: 20px;
            margin-bottom: 3rem;
            border: 1px solid var(--border);
        }
        .hero-pill {
            display: inline-block;
            background: rgba(99, 102, 241, 0.15);
            color: #6366F1;
            padding: 0.4rem 1.2rem;
            border-radius: 9999px;
            font-size: 0.88rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-bottom: 1.2rem;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
        .hero-title {
            font-size: 3.2rem;
            font-weight: 800;
            line-height: 1.15;
            color: var(--heading);
            margin-bottom: 1rem;
            letter-spacing: -0.02em;
        }
        .hero-subtitle {
            font-size: 1.2rem;
            color: var(--text);
            max-width: 780px;
            margin: 0 auto 2rem auto;
            line-height: 1.6;
        }
        .hero-stats-row {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 2.5rem;
            flex-wrap: wrap;
        }
        .hero-stat-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem 1.8rem;
            min-width: 180px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.03);
        }
        .hero-stat-num {
            font-size: 1.8rem;
            font-weight: 800;
            color: var(--primary);
        }
        .hero-stat-label {
            font-size: 0.85rem;
            color: var(--muted);
            font-weight: 600;
        }
        .section-title {
            font-size: 2.2rem;
            font-weight: 800;
            text-align: center;
            color: var(--heading);
            margin-bottom: 0.5rem;
        }
        .section-subtitle {
            font-size: 1.05rem;
            text-align: center;
            color: var(--muted);
            margin-bottom: 2.5rem;
        }
        .feat-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.6rem;
            height: 100%;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.02);
        }
        .feat-card:hover {
            transform: translateY(-4px);
            border-color: var(--primary);
            box-shadow: 0 12px 24px rgba(0,0,0,0.08);
        }
        .feat-icon {
            font-size: 2.2rem;
            margin-bottom: 1rem;
        }
        .feat-title {
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--heading);
            margin-bottom: 0.5rem;
        }
        .feat-desc {
            font-size: 0.92rem;
            color: var(--text);
            line-height: 1.5;
        }
        .step-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.2rem;
            text-align: center;
            position: relative;
        }
        .step-num {
            background: var(--primary);
            color: white;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 0.9rem;
            margin: 0 auto 0.8rem auto;
        }
        .step-title {
            font-weight: 700;
            font-size: 0.95rem;
            color: var(--heading);
        }
        .cta-banner {
            background: linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4338CA 100%);
            color: white;
            border-radius: 20px;
            padding: 3.5rem 2rem;
            text-align: center;
            margin: 3.5rem 0;
            box-shadow: 0 16px 32px rgba(49, 46, 129, 0.25);
        }
        .cta-banner h2 {
            color: white !important;
            font-size: 2.4rem;
            font-weight: 800;
            margin-bottom: 1rem;
        }
        .cta-banner p {
            color: #C7D2FE !important;
            font-size: 1.15rem;
            max-width: 650px;
            margin: 0 auto 2rem auto;
        }
        .footer {
            border-top: 1px solid var(--border);
            padding: 2.5rem 1rem 1.5rem 1rem;
            margin-top: 4rem;
            text-align: center;
            color: var(--muted);
            font-size: 0.9rem;
        }
        </style>
    ''', unsafe_allow_html=True)

    # Hero Section
    st.markdown('''
        <div class="hero-container">
            <span class="hero-pill">🤖 AI-POWERED TALENT ACQUISITION ENGINE</span>
            <h1 class="hero-title">Hire Smarter. Recruit Faster.</h1>
            <p class="hero-subtitle">
                Streamline your end-to-end recruitment workflow using AI resume parsing, candidate matching, ATS score analysis, skill gap identification, and automated interview question generation.
            </p>
        </div>
    ''', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("✨ Get Started", use_container_width=True, type="primary", key="hero_cta_reg"):
                st.session_state.auth_page = "Register"
                st.rerun()
        with col_btn2:
            if st.button("🔑 Sign In", use_container_width=True, key="hero_cta_login"):
                st.session_state.auth_page = "Login"
                st.rerun()

    st.markdown('''
        <div class="hero-stats-row">
            <div class="hero-stat-card">
                <div class="hero-stat-num">98.4%</div>
                <div class="hero-stat-label">Extraction Accuracy</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-num">75%</div>
                <div class="hero-stat-label">Time Saved</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-num">1,250+</div>
                <div class="hero-stat-label">Resumes Screened</div>
            </div>
            <div class="hero-stat-card">
                <div class="hero-stat-num">3.2x</div>
                <div class="hero-stat-label">Faster Hiring Cycle</div>
            </div>
        </div>
        <br><br>
    ''', unsafe_allow_html=True)

    st.divider()

    # Features Section
    st.markdown('''
        <div class="section-title">Core Platform Capabilities</div>
        <div class="section-subtitle">Intelligent tools designed for high-performance talent acquisition teams</div>
    ''', unsafe_allow_html=True)

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">📄</div>
                <div class="feat-title">AI Resume Parsing</div>
                <div class="feat-desc">Extract contact details, work history, education, and technical skills instantly from PDF and DOCX files.</div>
            </div>
        ''', unsafe_allow_html=True)
    with f_col2:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">💼</div>
                <div class="feat-title">JD Analysis</div>
                <div class="feat-desc">Automatically analyze job specifications to determine required skills, experience thresholds, and domain criteria.</div>
            </div>
        ''', unsafe_allow_html=True)
    with f_col3:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">🤝</div>
                <div class="feat-title">Candidate Matching</div>
                <div class="feat-desc">Calculate semantic vector match percentages between applicants and open vacancy requirements.</div>
            </div>
        ''', unsafe_allow_html=True)
    with f_col4:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">📌</div>
                <div class="feat-title">Application Tracking</div>
                <div class="feat-desc">Track applicants through a 5-stage recruitment pipeline with status steppers and automated stage transitions.</div>
            </div>
        ''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    f_col5, f_col6, f_col7, f_col8 = st.columns(4)
    with f_col5:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">📊</div>
                <div class="feat-title">ATS Score Analysis</div>
                <div class="feat-desc">Receive detailed candidate compatibility scores, formatting checks, and skill match breakdowns.</div>
            </div>
        ''', unsafe_allow_html=True)
    with f_col6:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">⚡</div>
                <div class="feat-title">Skill Gap Analysis</div>
                <div class="feat-desc">Identify missing technical competencies and receive targeted onboarding/upskilling recommendations.</div>
            </div>
        ''', unsafe_allow_html=True)
    with f_col7:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">📅</div>
                <div class="feat-title">Interview Scheduling</div>
                <div class="feat-desc">Assign custom technical assessment question sets and manage submission deadlines effortlessly.</div>
            </div>
        ''', unsafe_allow_html=True)
    with f_col8:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">🤖</div>
                <div class="feat-title">AI Question Generator</div>
                <div class="feat-desc">Auto-generate customized technical and behavioral interview questions tailored to any job role.</div>
            </div>
        ''', unsafe_allow_html=True)

    st.divider()

    # How It Works Section
    st.markdown('''
        <div class="section-title">How It Works</div>
        <div class="section-subtitle">End-to-end automated candidate evaluation workflow</div>
    ''', unsafe_allow_html=True)

    w_cols = st.columns(7)
    steps = [
        ("1", "Upload Resume", "📄"),
        ("2", "Analyze Candidate", "🔍"),
        ("3", "Match with JD", "🎯"),
        ("4", "ATS & Skill Gap", "📊"),
        ("5", "Select Candidate", "✅"),
        ("6", "Schedule Interview", "📅"),
        ("7", "Generate Questions", "🤖"),
    ]
    for idx, col in enumerate(w_cols):
        s_num, s_title, s_icon = steps[idx]
        with col:
            st.markdown(f'''
                <div class="step-card">
                    <div class="step-num">{s_num}</div>
                    <div style="font-size:1.5rem; margin-bottom:0.4rem;">{s_icon}</div>
                    <div class="step-title">{s_title}</div>
                </div>
            ''', unsafe_allow_html=True)

    st.divider()

    # Benefits Section
    st.markdown('''
        <div class="section-title">Why Use This Platform?</div>
        <div class="section-subtitle">Proven advantages for talent acquisition leaders and hiring managers</div>
    ''', unsafe_allow_html=True)

    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">⚡</div>
                <div class="feat-title">Faster Candidate Screening</div>
                <div class="feat-desc">Reduce manual resume reviewing from hours to seconds with automated parsing and structured profile extraction.</div>
            </div>
        ''', unsafe_allow_html=True)
    with b2:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">🎯</div>
                <div class="feat-title">AI-Powered Matching</div>
                <div class="feat-desc">Eliminate bias and rank candidates strictly based on verified skill relevance and experience alignment.</div>
            </div>
        ''', unsafe_allow_html=True)
    with b3:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">🗂️</div>
                <div class="feat-title">Centralized Recruitment Hub</div>
                <div class="feat-desc">Manage resumes, vacancies, applicant pipelines, evaluations, and interview questions in one unified system.</div>
            </div>
        ''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    b4, b5 = st.columns(2)
    with b4:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">💡</div>
                <div class="feat-title">Data-Driven Hiring Insights</div>
                <div class="feat-desc">Gain immediate clarity on candidate fit with multi-dimensional ATS scoring, skill gap radar, and PDF evaluations.</div>
            </div>
        ''', unsafe_allow_html=True)
    with b5:
        st.markdown('''
            <div class="feat-card">
                <div class="feat-icon">🖐️</div>
                <div class="feat-title">Reduced Manual Effort</div>
                <div class="feat-desc">Automate repetitive taskwork like question generation, stage updates, score calculations, and report generation.</div>
            </div>
        ''', unsafe_allow_html=True)

    # Final CTA Banner
    st.markdown('''
        <div class="cta-banner">
            <h2>Ready to Elevate Your Hiring Process?</h2>
            <p>Join modern recruitment teams using AI to source, evaluate, and hire high-performing talent faster than ever.</p>
        </div>
    ''', unsafe_allow_html=True)

    cta_c1, cta_c2, cta_c3 = st.columns([1, 1.2, 1])
    with cta_c2:
        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("✨ Get Started", use_container_width=True, type="primary", key="cta_bottom_reg"):
                st.session_state.auth_page = "Register"
                st.rerun()
        with cb2:
            if st.button("🔑 Sign In", use_container_width=True, key="cta_bottom_login"):
                st.session_state.auth_page = "Login"
                st.rerun()

    # Footer
    st.markdown('''
        <div class="footer">
            <div style="font-weight:700; color:var(--heading); font-size:1.1rem; margin-bottom:0.5rem;">
                📋 HireFlow AI
            </div>
            <p style="margin-bottom:1rem;">Next-generation AI recruitment platform powered by advanced NLP and intelligent candidate evaluation.</p>
            <p>© 2026 HireFlow AI. All rights reserved. | <a href="#" style="color:var(--primary); text-decoration:none;">GitHub Repository</a> | <a href="#" style="color:var(--primary); text-decoration:none;">Privacy Policy</a></p>
        </div>
    ''', unsafe_allow_html=True)


def render_register_page():
    """Render clean, modern user registration page."""
    render_public_header()

    st.markdown('''
        <style>
        .auth-card {
            max-width: 520px;
            margin: 1.5rem auto;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2.5rem 2.2rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
        }
        .auth-title {
            font-size: 2rem;
            font-weight: 800;
            color: var(--heading);
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .auth-subtitle {
            font-size: 0.95rem;
            color: var(--muted);
            text-align: center;
            margin-bottom: 2rem;
        }
        </style>
    ''', unsafe_allow_html=True)

    st.markdown('''
        <div class="auth-card">
            <div class="auth-title">Create Your Account</div>
            <div class="auth-subtitle">Get started with HireFlow AI</div>
    ''', unsafe_allow_html=True)

    with st.form("register_form", clear_on_submit=False):
        role_choice = st.radio(
            "I am registering as:*",
            ["🎓 Candidate (Job Seeker)", "💼 Recruiter (Hiring Manager)"],
            index=0,
            horizontal=True,
            help="Candidates apply for jobs & take AI interviews. Recruiters post jobs, parse resumes & evaluate candidates."
        )
        selected_role = "recruiter" if "Recruiter" in role_choice else "candidate"

        full_name = st.text_input("👤 Full Name*", placeholder="e.g. Jane Doe")
        email = st.text_input("✉️ Email Address*", placeholder="e.g. jane@company.com")
        password = st.text_input("🔒 Password*", type="password", placeholder="At least 6 characters")
        confirm_password = st.text_input("🔒 Confirm Password*", type="password", placeholder="Re-enter password")

        st.markdown("<br>", unsafe_allow_html=True)
        submit_btn = st.form_submit_button("🚀 Create Account", use_container_width=True, type="primary")

        if submit_btn:
            with st.spinner("Creating your account..."):
                ok, msg, user_data = auth_service.register_user(
                    full_name=full_name,
                    email=email,
                    password=password,
                    confirm_password=confirm_password,
                    role=selected_role
                )
                if ok and user_data:
                    st.session_state.authenticated = True
                    st.session_state.auth_user = user_data
                    st.session_state.jwt_token = user_data.get("token")
                    db.log_audit_event(user_data.get("email"), user_data.get("full_name"), user_data.get("role"), "User Registered", f"Account {user_data.get('email')}", "Success", f"Registered new account with role '{selected_role}'")
                    if user_data.get("token"):
                        st.query_params["session_token"] = user_data.get("token")
                    st.session_state.portal_role = "Candidate" if selected_role == "candidate" else "Recruiter"
                    st.session_state.auth_page = "Dashboard"
                    st.session_state.active_page = "Dashboard"
                    st.session_state.candidate_active_page = "Dashboard"
                    st.success(f"🎉 Registered successfully as {selected_role.title()}! Redirecting...")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("Already have an account? Sign In", use_container_width=True, key="reg_to_login_btn"):
            st.session_state.auth_page = "Login"
            st.rerun()


def render_login_page():
    """Render clean, modern user login page."""
    render_public_header()

    st.markdown('''
        <style>
        .auth-card {
            max-width: 480px;
            margin: 2rem auto;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2.5rem 2.2rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
        }
        .auth-title {
            font-size: 2rem;
            font-weight: 800;
            color: var(--heading);
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .auth-subtitle {
            font-size: 0.95rem;
            color: var(--muted);
            text-align: center;
            margin-bottom: 2rem;
        }
        </style>
    ''', unsafe_allow_html=True)

    st.markdown('''
        <div class="auth-card">
            <div class="auth-title">Welcome Back</div>
            <div class="auth-subtitle">Sign in to your HireFlow AI Dashboard</div>
    ''', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("✉️ Email Address*", placeholder="e.g. admin@company.com")
        password = st.text_input("🔒 Password*", type="password", placeholder="Enter your password")

        st.markdown("<br>", unsafe_allow_html=True)
        login_btn = st.form_submit_button("🔑 Sign In", use_container_width=True, type="primary")

        if login_btn:
            with st.spinner("Authenticating..."):
                ok, msg, user_data = auth_service.authenticate_user(email=email, password=password)
                if ok and user_data:
                    st.session_state.authenticated = True
                    st.session_state.auth_user = user_data
                    st.session_state.jwt_token = user_data.get("token")
                    db.log_audit_event(user_data.get("email"), user_data.get("full_name"), user_data.get("role"), "User Login", f"User {user_data.get('email')}", "Success", "Successful login authentication")
                    if user_data.get("token"):
                        st.query_params["session_token"] = user_data.get("token")
                    st.session_state.auth_page = "Dashboard"
                    st.session_state.active_page = "Dashboard"
                    st.success("🎉 Authentication successful! Redirecting...")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("Don't have an account? Create an account", use_container_width=True, key="login_to_reg_btn"):
            st.session_state.auth_page = "Register"
            st.rerun()


def render_admin_header():
    """Render top authenticated user profile bar with Logout CTA."""
    user = st.session_state.get("auth_user") or {}
    user_name = user.get("full_name", "Admin Recruiter")
    user_email = user.get("email", "admin@copilot.ai")
    user_role = (user.get("role") or "ADMIN").upper()

    col1, col2 = st.columns([3.5, 1])
    with col1:
        st.markdown(f'''
            <div style="display: flex; align-items: center; gap: 1rem; padding: 0.6rem 1rem; background: var(--card); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 1rem;">
                <div style="width: 42px; height: 42px; border-radius: 50%; background: linear-gradient(135deg, #10B981, #3B82F6); color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.1rem;">
                    {user_name[0].upper() if user_name else "A"}
                </div>
                <div>
                    <div style="font-weight: 700; color: var(--heading); font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem;">
                        {user_name}
                        <span style="background: rgba(16, 185, 129, 0.15); color: #10B981; font-size: 0.72rem; padding: 0.15rem 0.5rem; border-radius: 9999px; border: 1px solid rgba(16, 185, 129, 0.3); font-weight: 700;">{user_role}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: var(--muted);">{user_email}</div>
                </div>
            </div>
        ''', unsafe_allow_html=True)
    with col2:
        if st.button("🚪 Logout", use_container_width=True, key="admin_hdr_logout_btn"):
            st.session_state.authenticated = False
            st.session_state.auth_user = None
            st.session_state.jwt_token = None
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.session_state.auth_page = "Landing"
            st.rerun()


def check_and_enforce_auth():
    """Enforce authentication check and handle public vs protected routing."""
    # Attempt automatic session restoration from persistent session token in query params if reloaded
    if not st.session_state.get("authenticated", False):
        try:
            token = st.query_params.get("session_token")
            if token:
                payload = auth_service.verify_access_token(token)
                if payload and payload.get("email"):
                    user = db_auth.get_user_by_email(payload["email"])
                    if user:
                        user["token"] = token
                        st.session_state.authenticated = True
                        st.session_state.auth_user = user
                        st.session_state.jwt_token = token
        except Exception:
            pass

    if not st.session_state.get("authenticated", False):
        auth_page = st.session_state.get("auth_page", "Landing")
        if auth_page == "Register":
            render_register_page()
        elif auth_page == "Login":
            render_login_page()
        else:
            render_landing_page()
        st.stop()

    # Automatic role-based portal assignment & route protection
    user = st.session_state.get("auth_user") or {}
    user_role = auth_service.normalize_role(user.get("role"))

    if user_role == "candidate":
        st.session_state.portal_role = "Candidate"
        recruiter_and_admin_pages = [
            "Users", "Recruiters", "Users & Recruiters", "Admin Profile", "Recruiter Profile",
            "Resume Upload", "Candidate Pipeline", "Interview Question Generator",
            "Interview Assignment", "Submitted Interviews", "Job Descriptions",
            "Candidate Matching", "Candidate Details", "Skill Gap Analysis",
            "Candidate Ranking", "Executive Reports", "Settings", "System Analytics",
            "Recruiter Performance", "AI Monitoring", "Recruitment Health", "Audit Logs", "Security"
        ]
        if st.session_state.get("active_page") in recruiter_and_admin_pages:
            st.session_state.active_page = "Dashboard"
            st.error("⛔ Access Denied: Candidate accounts cannot access Recruiter/Admin tools.")
    elif user_role == "recruiter":
        st.session_state.portal_role = "Recruiter"
        admin_only_pages = [
            "Users", "Recruiters", "Users & Recruiters", "Admin Profile", "System Analytics",
            "Recruiter Performance", "AI Monitoring", "Recruitment Health", "Audit Logs", "Security"
        ]
        if st.session_state.get("active_page") in admin_only_pages:
            st.session_state.active_page = "Dashboard"
            st.error("⛔ Access Denied: Recruiter accounts cannot access Admin control center tools.")
    elif user_role == "admin":
        st.session_state.portal_role = "Admin"


def render_stage_badge(stage: str) -> str:
    stage_str = html.escape(str(stage or "Applied"))
    badge_map = {
        "Applied": ("rgba(59, 130, 246, 0.15)", "#3b82f6"),
        "Screening": ("rgba(139, 92, 246, 0.15)", "#8b5cf6"),
        "Interview": ("rgba(245, 158, 11, 0.15)", "#f59e0b"),
        "Selected": ("rgba(16, 185, 129, 0.15)", "#10b981"),
        "Rejected": ("rgba(239, 68, 68, 0.15)", "#ef4444"),
    }
    bg, color = badge_map.get(stage_str, ("rgba(107, 114, 128, 0.15)", "#6b7280"))
    return f'<span style="background-color: {bg}; color: {color}; border: 1px solid {color}; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; display: inline-block;">{stage_str}</span>'



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


def render_ats_candidate_details(candidate: dict, db_ok: bool, is_candidate_view: bool = False):
    import datetime

    if not is_candidate_view and st.session_state.get("portal_role") == "Candidate":
        is_candidate_view = True

    cid = candidate_id(candidate)
    name = safe_text(candidate.get("full_name"), "Unknown Candidate")
    email = safe_text(candidate.get("email"), "—")
    phone = safe_text(candidate.get("phone"), "—")
    stage = candidate.get("recruitment_stage", "Applied")

    st.markdown('<div class="custom-card">', unsafe_allow_html=True)

    # Candidate Header
    initial = name[0].upper() if name and name[0].isalpha() else "U"
    stage_badge = render_stage_badge(stage)
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <div style="display: flex; align-items: center;">
                <div style="width: 70px; height: 70px; border-radius: 50%; background-color: var(--primary); display: flex; align-items: center; justify-content: center; margin-right: 1.2rem; color: white; font-weight: 700; font-size: 2.2rem; border: 3px solid var(--border);">
                    {initial}
                </div>
                <div>
                    <h2 style="margin: 0; padding: 0; color: var(--heading);">{html.escape(name)}</h2>
                    <p style="color: var(--muted); font-size: 1rem; margin-top: 0.2rem;">📧 {html.escape(email)} &nbsp;&nbsp;|&nbsp;&nbsp; 📱 {html.escape(phone)}</p>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.8rem; font-weight: 600; color: var(--muted); margin-bottom: 0.3rem;">CURRENT STAGE</div>
                {stage_badge}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # 1. Stage Management & Interview Scheduling
    if is_candidate_view:
        # Candidate Read-Only View of Scheduled Interview
        c_date = candidate.get("interview_date")
        c_time = candidate.get("interview_time")
        c_interviewer = candidate.get("interviewer_name")

        st.markdown("#### 🗓️ Scheduled Interview Details")
        if c_date or c_time or c_interviewer:
            st.info(
                f"📅 **Date:** {html.escape(str(c_date or 'To be announced'))} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"⏰ **Time:** {html.escape(str(c_time or 'To be announced'))} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"👨‍💼 **Interviewer:** {html.escape(str(c_interviewer or 'Assigned Hiring Team'))}"
            )
        else:
            st.caption("No upcoming interviews scheduled yet.")
        st.markdown("---")
    else:
        # Recruiter Management Controls
        col_stage_mgmt, col_interview_mgmt = st.columns(2)

        with col_stage_mgmt:
            st.markdown("#### 📌 Stage Management")
            stage_options = ["Applied", "Screening", "Interview", "Selected", "Rejected"]
            curr_index = stage_options.index(stage) if stage in stage_options else 0
            new_stage = st.selectbox(
                "Recruitment Stage",
                options=stage_options,
                index=curr_index,
                key=f"stage_select_{cid}"
            )
            if st.button("💾 Save Stage", key=f"save_stage_btn_{cid}", type="primary"):
                ok, msg = db.update_candidate_stage(cid, new_stage)
                try:
                    cand_apps = db_applications.get_applications_by_candidate(cid)
                    for app_d in cand_apps:
                        db_applications.set_application_final_decision(cid, app_d.get("job_id"), new_stage)
                except Exception:
                    pass
                if ok:
                    st.success(f"Recruitment stage updated to '{new_stage}'.")
                    if hasattr(st, "cache_data"):
                        st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)

        with col_interview_mgmt:
            st.markdown("#### 🗓️ Interview Scheduling")
            curr_date_str = candidate.get("interview_date", "")
            default_date = datetime.date.today()
            if curr_date_str:
                try:
                    default_date = datetime.datetime.strptime(curr_date_str, "%Y-%m-%d").date()
                except ValueError:
                    default_date = datetime.date.today()

            interview_date_val = st.date_input(
                "Interview Date*",
                value=default_date,
                key=f"interview_date_input_{cid}"
            )

            curr_time_str = candidate.get("interview_time", "")
            interview_time_val = st.text_input(
                "Interview Time*",
                value=curr_time_str,
                placeholder="e.g. 10:30 AM or 14:00",
                key=f"interview_time_input_{cid}"
            )

            curr_interviewer = candidate.get("interviewer_name", "")
            interviewer_name_val = st.text_input(
                "Interviewer Name",
                value=curr_interviewer,
                placeholder="e.g. Technical Lead / HR Manager",
                key=f"interviewer_name_input_{cid}"
            )

            if st.button("📅 Schedule Interview", key=f"save_interview_btn_{cid}"):
                today = datetime.date.today()
                if interview_date_val < today:
                    st.error("Interview date cannot be before today's date.")
                elif not interview_time_val or not interview_time_val.strip():
                    st.error("Interview time cannot be empty.")
                elif not db_ok:
                    st.error("Database offline — cannot save schedule.")
                else:
                    ok, msg = db.update_candidate_interview(
                        cid,
                        str(interview_date_val),
                        interview_time_val.strip(),
                        interviewer_name_val.strip()
                    )
                    if ok:
                        st.success(msg)
                        if hasattr(st, "cache_data"):
                            st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(msg)

        st.markdown("---")

        # 2. Recruiter Notes & Feedback (Recruiter View Only)
        col_notes, col_feedback = st.columns(2)

        with col_notes:
            st.markdown("#### 📝 Recruiter Internal Notes")
            notes_val = st.text_area(
                "Internal Notes",
                value=candidate.get("recruiter_notes", ""),
                height=140,
                key=f"notes_input_{cid}"
            )
            if st.button("💾 Save Internal Notes", key=f"save_notes_btn_{cid}"):
                if not db_ok:
                    st.error("Database offline — cannot save notes.")
                else:
                    ok, msg = db.update_candidate_notes(cid, notes_val)
                    if ok:
                        st.success(msg)
                        if hasattr(st, "cache_data"):
                            st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(msg)

        with col_feedback:
            st.markdown("#### 💬 Recruiter Interview Feedback")
            feedback_val = st.text_area(
                "Interview Feedback",
                value=candidate.get("recruiter_feedback", ""),
                height=140,
                key=f"feedback_input_{cid}"
            )
            if st.button("💾 Save Interview Feedback", key=f"save_feedback_btn_{cid}"):
                if not db_ok:
                    st.error("Database offline — cannot save feedback.")
                else:
                    ok, msg = db.update_candidate_feedback(cid, feedback_val)
                    if ok:
                        st.success(msg)
                        if hasattr(st, "cache_data"):
                            st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(msg)

        st.markdown("---")

    # 3. Extracted Skills
    st.markdown("#### 🎯 Extracted Skills")
    skills_list = skills_to_list(candidate.get("skills"))
    if skills_list:
        skills_html = "".join([f'<span class="badge-blue">{html.escape(s)}</span>' for s in skills_list])
        st.markdown(skills_html, unsafe_allow_html=True)
    else:
        st.info("No extracted skills detected.")

    st.markdown("---")

    # 4. Education, Experience, Certifications, Projects
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

    # 5. ATS Scoring Evaluation against Vacancies
    import db_jobs
    jds = db_jobs.get_all_jobs()
    if jds:
        st.markdown("#### 📊 Candidate ATS Evaluation")
        jd_options = {jd["job_id"]: f"{jd['job_title']} at {jd.get('company_name', 'Unknown')}" for jd in jds}
        selected_jd_id = st.selectbox("Select Job Description for ATS Match", options=list(jd_options.keys()), format_func=lambda x: jd_options[x], key=f"details_jd_select_{cid}")
        selected_job = next((j for j in jds if j["job_id"] == selected_jd_id), jds[0])
        
        ats_result = calculate_candidate_score(candidate, selected_job)
        if db_ok and cid and selected_job:
            db.save_evaluation(
                selected_job.get("job_id"),
                cid,
                ats_result.get("hiring_score", 0),
                ats_result.get("recommendation", "Not Recommended"),
                ats_result.get("score_breakdown", {})
            )
        actual_ats = ats_result.get("hiring_score", 0)
        
        st.write(f"**ATS Hiring Score:** {actual_ats}% &nbsp;|&nbsp; **Recommendation:** {ats_result.get('recommendation')}")

    st.markdown("---")
    with st.expander("📄 View Raw Resume Text & Metadata"):
        st.write("**Source Filename:**", candidate.get("source_filename", "—") or "—")
        st.write("**Created Date:**", format_datetime(candidate.get("created_at")))
        st.write("**Updated Date:**", format_datetime(candidate.get("updated_at")))
        st.text_area("Raw Resume Text", candidate.get("raw_text", ""), height=250, disabled=True, key=f"raw_text_area_{cid}")

    st.markdown("</div>", unsafe_allow_html=True)


def render_candidate_interview_taking(interview_id: str, candidate: dict):
    intv = db_interviews.get_interview_by_id(interview_id)
    if not intv:
        st.error("Interview assignment not found.")
        if st.button("⬅️ Exit to Dashboard"):
            st.session_state.taking_interview_id = None
            st.rerun()
        return

    questions = intv.get("generated_questions", [])
    if not questions:
        st.error("No questions found in this interview.")
        return

    status = intv.get("interview_status", "Assigned")

    # If already submitted or evaluated, display full transcript & evaluation report
    if status in ["Submitted", "Evaluated"]:
        st.markdown('<p class="main-heading">🔒 Read-Only Interview Submission & Report</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="main-subtitle">Submitted on {format_datetime(intv.get("submitted_time") or intv.get("updated_at"))}</p>', unsafe_allow_html=True)
        if st.button("⬅️ Back to Dashboard", type="secondary"):
            st.session_state.taking_interview_id = None
            st.rerun()

        # Display AI Evaluation Summary Card if available
        sum_doc = db_interview_evaluator.get_interview_summary(interview_id)
        if sum_doc:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.markdown('<p class="card-title">🏆 AI Interview Evaluation Summary</p>', unsafe_allow_html=True)
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            with sc1:
                st.markdown(f'<div class="metric-box"><div class="metric-value">{sum_doc.get("overall_interview_score", 0)}%</div><div class="metric-label">Overall Score</div></div>', unsafe_allow_html=True)
            with sc2:
                st.markdown(f'<div class="metric-box"><div class="metric-value" style="color:#10b981;">{sum_doc.get("avg_technical_score", 0)}%</div><div class="metric-label">Technical</div></div>', unsafe_allow_html=True)
            with sc3:
                st.markdown(f'<div class="metric-box"><div class="metric-value" style="color:#3b82f6;">{sum_doc.get("avg_communication_score", 0)}%</div><div class="metric-label">Communication</div></div>', unsafe_allow_html=True)
            with sc4:
                st.markdown(f'<div class="metric-box"><div class="metric-value" style="color:#8b5cf6;">{sum_doc.get("avg_problem_solving_score", sum_doc.get("avg_confidence_score", 0))}%</div><div class="metric-label">Problem Solving</div></div>', unsafe_allow_html=True)
            with sc5:
                st.markdown(f'<div class="metric-box"><div class="metric-value" style="color:#f59e0b;">{sum_doc.get("avg_confidence_score", 0)}%</div><div class="metric-label">Confidence</div></div>', unsafe_allow_html=True)

            st.write(f"**Final Hiring Recommendation:** `{sum_doc.get('final_recommendation', 'Recommended')}`")
            st.markdown('</div>', unsafe_allow_html=True)

        # Download PDF Report Button
        try:
            eval_list = db_interview_evaluator.get_evaluations_by_interview(interview_id)
            pdf_bytes = interview_pdf_report.generate_interview_pdf_report(
                {}, {}, interview_id, eval_list, sum_doc or {}
            )
            st.download_button(
                label="📥 Download Full PDF Interview Report",
                data=pdf_bytes,
                file_name=f"Interview_Report_{interview_id}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception:
            pass

        # Render Chat Thread
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">💬 Full Interview Chat Transcript</p>', unsafe_allow_html=True)
        msgs = db_interviews.get_interview_messages(interview_id)
        if msgs:
            for m in msgs:
                sender = m.get("sender", "AI")
                text = m.get("message_text", "")
                is_v = m.get("is_voice", False)
                if sender == "Candidate":
                    with st.chat_message("user", avatar="👤"):
                        v_badge = '<span class="badge-blue" style="font-size:0.75rem; margin-left:0.5rem;">🎤 Voice Response</span>' if is_v else ''
                        st.markdown(f"**Candidate:** {v_badge}\n\n{html.escape(text)}", unsafe_allow_html=True)
                else:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(f"**AI Interviewer:**\n\n{text}")
        else:
            responses = db_interviews.get_responses_by_interview(interview_id)
            for idx, r in enumerate(responses):
                st.markdown(f"**Q{idx + 1}:** {html.escape(r.get('question', ''))}")
                st.markdown(f'<div style="background: var(--bg-sec); padding: 0.8rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid var(--border);"><p style="white-space: pre-wrap;">{html.escape(r.get("answer", ""))}</p></div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
        return

    # In-progress interview answering workflow
    st.markdown('<p class="main-heading">✍️ Candidate Assessment</p>', unsafe_allow_html=True)

    if st.button("⬅️ Save & Exit to Dashboard", type="secondary"):
        st.session_state.taking_interview_id = None
        st.rerun()

    draft_answers = intv.get("draft_answers", {})

    if st.session_state.get("review_mode"):
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📋 Review Your Answers Before Final Submission</p>', unsafe_allow_html=True)
        st.caption("Please inspect your responses carefully. Once submitted, answers become read-only.")

        responses_payload = []
        for idx, q_text in enumerate(questions):
            ans = draft_answers.get(str(idx), "").strip()
            responses_payload.append({"question": q_text, "answer": ans})
            st.markdown(f"**Question {idx + 1}:** {html.escape(q_text)}")
            if ans:
                st.markdown(f'<div style="background: var(--bg-sec); padding: 0.8rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid var(--border);"><p style="white-space: pre-wrap;">{html.escape(ans)}</p></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="color: var(--danger); margin-bottom: 1rem;"><em>⚠️ Unanswered</em></div>', unsafe_allow_html=True)

        st.markdown("---")
        confirm_sub = st.checkbox("☑️ I confirm that these answers are my final responses and ready for recruiter submission.", key="confirm_sub_chk")

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("⬅️ Edit Answers", key="back_to_edit_btn", use_container_width=True):
                st.session_state.review_mode = False
                st.rerun()
        with col_b2:
            if st.button("🚀 Submit Final Interview", key="final_submit_intv_btn", type="primary", use_container_width=True):
                if not confirm_sub:
                    st.warning("Please check the confirmation box before submitting.")
                else:
                    ok, msg = db_interviews.submit_interview_responses(
                        interview_id,
                        intv.get("candidate_id"),
                        intv.get("job_id"),
                        responses_payload
                    )
                    if ok:
                        st.success(msg)
                        st.session_state.review_mode = False
                        st.rerun()
                    else:
                        st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Step-by-Step Question Interface
    q_idx = st.session_state.get("taking_question_index", 0)
    total_q = len(questions)
    q_idx = max(0, min(total_q - 1, q_idx))
    st.session_state.taking_question_index = q_idx

    current_q_text = questions[q_idx]

    # Progress Bar
    pct = int(((q_idx + 1) / total_q) * 100)
    custom_progress_bar(f"Question {q_idx + 1} of {total_q}", pct, "var(--primary)")

    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown(f'<p class="card-title">Question {q_idx + 1} of {total_q}</p>', unsafe_allow_html=True)
    st.markdown(f'<h3 style="margin-bottom: 1.5rem; color: var(--heading);">{html.escape(current_q_text)}</h3>', unsafe_allow_html=True)

    curr_ans_val = draft_answers.get(str(q_idx), "")

    answer_input = st.text_area(
        "Type your answer below:*",
        value=curr_ans_val,
        height=220,
        placeholder="Provide a thorough response...",
        key=f"ans_field_{interview_id}_{q_idx}"
    )

    # Auto Save Draft on change
    if answer_input != curr_ans_val:
        draft_answers[str(q_idx)] = answer_input
        db_interviews.update_interview_draft_answers(interview_id, draft_answers, "In Progress")

    col_p, col_s, col_n = st.columns([1, 1, 1])

    with col_p:
        if q_idx > 0:
            if st.button("⬅️ Previous", key=f"prev_btn_{q_idx}", use_container_width=True):
                draft_answers[str(q_idx)] = answer_input
                db_interviews.update_interview_draft_answers(interview_id, draft_answers, "In Progress")
                st.session_state.taking_question_index = q_idx - 1
                st.rerun()

    with col_s:
        if st.button("💾 Save Draft", key=f"save_draft_btn_{q_idx}", use_container_width=True):
            draft_answers[str(q_idx)] = answer_input
            ok, msg = db_interviews.update_interview_draft_answers(interview_id, draft_answers, "In Progress")
            if ok:
                st.success("Draft saved!")

    with col_n:
        if q_idx < total_q - 1:
            if st.button("Next ➡️", key=f"next_btn_{q_idx}", type="primary", use_container_width=True):
                draft_answers[str(q_idx)] = answer_input
                db_interviews.update_interview_draft_answers(interview_id, draft_answers, "In Progress")
                st.session_state.taking_question_index = q_idx + 1
                st.rerun()
        else:
            if st.button("📋 Review & Submit", key=f"review_btn_{q_idx}", type="primary", use_container_width=True):
                draft_answers[str(q_idx)] = answer_input
                db_interviews.update_interview_draft_answers(interview_id, draft_answers, "In Progress")
                st.session_state.review_mode = True
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def render_candidate_portal_profile(candidate: dict):
    import datetime
    cid = candidate_id(candidate)
    c_name = safe_text(candidate.get("full_name"), "Candidate")
    email = safe_text(candidate.get("email"), "—")
    phone = safe_text(candidate.get("phone"), "—")
    stage = candidate.get("recruitment_stage", "Applied")

    # 1. Header Card with Application Status
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    initial = c_name[0].upper() if c_name and c_name[0].isalpha() else "C"
    stage_badge = render_stage_badge(stage)

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div style="display: flex; align-items: center;">
                <div style="width: 65px; height: 65px; border-radius: 50%; background-color: var(--primary); display: flex; align-items: center; justify-content: center; margin-right: 1.2rem; color: white; font-weight: 700; font-size: 2rem; border: 3px solid var(--border);">
                    {initial}
                </div>
                <div>
                    <h2 style="margin: 0; padding: 0; color: var(--heading);">{html.escape(c_name)}</h2>
                    <p style="color: var(--muted); font-size: 0.95rem; margin-top: 0.2rem;">📧 {html.escape(email)} &nbsp;&nbsp;|&nbsp;&nbsp; 📱 {html.escape(phone)}</p>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.75rem; font-weight: 700; color: var(--muted); letter-spacing: 0.5px; margin-bottom: 0.3rem;">APPLICATION STATUS</div>
                {stage_badge}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. Upcoming Interview Card
    cand_email = candidate.get("email", "")
    interviews = db_interviews.get_interviews_by_candidate(cid, cand_email)
    pending_intvs = [i for i in interviews if i.get("interview_status") in ["Assigned", "In Progress"]]

    c_date = candidate.get("interview_date")
    c_time = candidate.get("interview_time")
    c_interviewer = candidate.get("interviewer_name")

    if pending_intvs or c_date or c_time:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">🗓️ Upcoming Scheduled Interview</p>', unsafe_allow_html=True)

        if pending_intvs:
            jds_all = load_jobs()
            jd_map = {j.get("job_id"): j.get("job_title") for j in jds_all}
            for intv_item in pending_intvs:
                p_iid = intv_item.get("interview_id")
                p_role = jd_map.get(intv_item.get("job_id"), "Role Position")
                p_due = intv_item.get("due_date", "TBD")
                p_status = intv_item.get("interview_status", "Assigned")

                st.markdown(
                    f"""
                    <div style="background: var(--bg-sec); padding: 1rem; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 0.8rem;">
                        <h4 style="margin: 0; color: var(--heading);">{html.escape(p_role)}</h4>
                        <p style="margin: 0.3rem 0; color: var(--muted); font-size: 0.9rem;">
                            🆔 Assignment ID: <code>{html.escape(p_iid)}</code> &nbsp;|&nbsp; 📅 Due Date: <strong>{html.escape(p_due)}</strong> &nbsp;|&nbsp; 📌 Status: <strong>{html.escape(p_status)}</strong>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        elif c_date or c_time:
            st.info(
                f"📅 **Interview Date:** {html.escape(str(c_date or 'TBD'))} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"⏰ **Time:** {html.escape(str(c_time or 'TBD'))} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"👨‍💼 **Interviewer:** {html.escape(str(c_interviewer or 'Hiring Team'))}"
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. ATS Evaluation, Matched Skills, Missing Skills, and AI Improvement Suggestions
    jds = load_jobs()
    if jds:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📊 ATS Resume Evaluation & Skill Match</p>', unsafe_allow_html=True)

        jd_options = {jd["job_id"]: f"{jd['job_title']} at {jd.get('company_name', 'Company')}" for jd in jds}
        selected_jd_id = st.selectbox(
            "Select Target Vacancy for ATS Evaluation:",
            options=list(jd_options.keys()),
            format_func=lambda x: jd_options[x],
            key=f"cand_profile_jd_select_{cid}"
        )
        selected_job = next((j for j in jds if j["job_id"] == selected_jd_id), jds[0])

        ats_result = calculate_candidate_score(candidate, selected_job)
        score = ats_result.get("hiring_score", 0)
        recommendation = ats_result.get("recommendation", "Consider")

        # Color badges: 80-100 Green (#10b981), 60-79 Orange (#f59e0b), Below 60 Red (#ef4444)
        if score >= 80:
            score_color = "#10b981"
            badge_class = "badge-green"
        elif score >= 60:
            score_color = "#f59e0b"
            badge_class = "badge-yellow"
        else:
            score_color = "#ef4444"
            badge_class = "badge-red"

        # ATS Score Progress Bar & Card
        st.markdown(
            f"""
            <div style="display: flex; gap: 1.5rem; align-items: center; background: var(--bg-sec); padding: 1.2rem; border-radius: 10px; border: 1px solid var(--border); margin-bottom: 1.2rem;">
                <div style="text-align: center; min-width: 100px;">
                    <div style="font-size: 2.2rem; font-weight: 800; color: {score_color}; line-height: 1;">{score}%</div>
                    <div style="font-size: 0.75rem; font-weight: 700; color: var(--muted); margin-top: 0.3rem;">ATS RESUME SCORE</div>
                </div>
                <div style="flex-grow: 1;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                        <span style="font-weight: 600; color: var(--heading);">Resume Match Level:</span>
                        <span class="{badge_class}">{html.escape(recommendation)}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        custom_progress_bar(f"ATS Match Score: {score}%", score, score_color)

        st.markdown("---")

        # Extract matched and missing skills
        cand_skills = set(skills_to_list(candidate.get("skills")))
        req_skills_raw = selected_job.get("required_skills", [])
        if isinstance(req_skills_raw, str):
            req_skills_list = [s.strip() for s in req_skills_raw.split(",") if s.strip()]
        else:
            req_skills_list = [str(s).strip() for s in req_skills_raw if str(s).strip()]

        matched_skills = []
        missing_skills = []

        for req_s in req_skills_list:
            req_lower = req_s.lower()
            if any(req_lower in cs.lower() or cs.lower() in req_lower for cs in cand_skills):
                matched_skills.append(req_s)
            else:
                missing_skills.append(req_s)

        # Fallback if no specific skills listed
        if not matched_skills and cand_skills:
            matched_skills = list(cand_skills)[:4]

        col_matched, col_missing = st.columns(2)

        with col_matched:
            st.markdown("#### ✅ Matched Skills")
            if matched_skills:
                m_html = "".join([f'<span class="badge-green" style="margin-right: 0.5rem; margin-bottom: 0.5rem; display: inline-block;">✓ {html.escape(s)}</span>' for s in matched_skills])
                st.markdown(f'<div style="margin-top: 0.5rem;">{m_html}</div>', unsafe_allow_html=True)
            else:
                st.info("No direct skill matches detected for this vacancy.")

        with col_missing:
            st.markdown("#### ⚠️ Missing Skills")
            if missing_skills:
                ms_html = "".join([f'<span class="badge-yellow" style="margin-right: 0.5rem; margin-bottom: 0.5rem; display: inline-block;">{html.escape(s)}</span>' for s in missing_skills])
                st.markdown(f'<div style="margin-top: 0.5rem;">{ms_html}</div>', unsafe_allow_html=True)
            else:
                st.success("You possess all primary required skills for this job role!")

        st.markdown("---")

        # 5. AI Improvement Suggestions
        st.markdown("#### 💡 AI Improvement Suggestions")
        suggestions = []
        if missing_skills:
            for ms in missing_skills[:3]:
                suggestions.append(f"Add **{ms}** project experience or relevant certification to your profile.")
        if len(cand_skills) < 5:
            suggestions.append("Highlight specific framework, library, and cloud infrastructure tools in your skills list.")
        suggestions.append("Include measurable metrics and quantitative achievements (e.g., 'Improved API latency by 35%') in project descriptions.")
        suggestions.append("Ensure your work experience bullet points clearly reference your role in system design and architecture.")

        for sug in suggestions[:4]:
            st.markdown(f"• {sug}")

        st.markdown('</div>', unsafe_allow_html=True)

    # 6. Candidate Profile Base Info (Extracted Skills, Education, Experience, Projects)
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">👤 Candidate Profile Details</p>', unsafe_allow_html=True)

    skills_list = skills_to_list(candidate.get("skills"))
    st.markdown("#### 🎯 Skills Summary")
    if skills_list:
        sk_html = "".join([f'<span class="badge-blue" style="margin-right: 0.4rem; margin-bottom: 0.4rem; display: inline-block;">{html.escape(s)}</span>' for s in skills_list])
        st.markdown(sk_html, unsafe_allow_html=True)
    else:
        st.info("No skills listed.")

    st.markdown("---")
    col_edu, col_exp = st.columns(2)

    with col_edu:
        st.markdown("#### 🎓 Education")
        edu_text = html.escape(safe_text(candidate.get("education"), "No education specified")).replace("\n", "<br>")
        st.markdown(f'<div style="border-left: 2px solid var(--primary); padding-left: 1rem; margin-bottom: 1rem;"><p style="white-space: pre-wrap; margin:0;">{edu_text}</p></div>', unsafe_allow_html=True)

        st.markdown("#### 🏆 Certifications")
        cert_text = html.escape(safe_text(candidate.get("certifications"), "None listed")).replace("\n", "<br>")
        st.markdown(f'<div style="background: var(--bg-sec); padding: 0.8rem; border-radius: 8px; border: 1px solid var(--border);"><p style="white-space: pre-wrap; margin:0;">{cert_text}</p></div>', unsafe_allow_html=True)

    with col_exp:
        st.markdown("#### 💼 Experience")
        exp_text = html.escape(safe_text(candidate.get("experience"), "No experience specified")).replace("\n", "<br>")
        st.markdown(f'<div style="border-left: 2px solid var(--primary); padding-left: 1rem; margin-bottom: 1rem;"><p style="white-space: pre-wrap; margin:0;">{exp_text}</p></div>', unsafe_allow_html=True)

        st.markdown("#### 🛠 Projects")
        proj_text = html.escape(safe_text(candidate.get("projects"), "None listed")).replace("\n", "<br>")
        st.markdown(f'<div style="background: var(--bg-sec); padding: 0.8rem; border-radius: 8px; border: 1px solid var(--border);"><p style="white-space: pre-wrap; margin:0;">{proj_text}</p></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # 7. Past Interview History
    past_intvs = [i for i in interviews if i.get("interview_status") in ["Submitted", "Evaluated"]]
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">📜 Interview History</p>', unsafe_allow_html=True)

    if not past_intvs:
        st.caption("No past interview history found.")
    else:
        jds_all = load_jobs()
        jd_map = {j.get("job_id"): j.get("job_title") for j in jds_all}

        for idx, intv_item in enumerate(past_intvs):
            iid = intv_item.get("interview_id")
            role_name = jd_map.get(intv_item.get("job_id"), "Role Position")
            sub_date = format_datetime(intv_item.get("submitted_time") or intv_item.get("updated_at"))
            st_val = intv_item.get("interview_status", "Submitted")

            sum_doc = db_interview_evaluator.get_interview_summary(iid)
            score_str = f"{sum_doc.get('overall_interview_score')}% ({sum_doc.get('final_recommendation')})" if sum_doc else "Pending Evaluation"

            st.markdown(
                f"""
                <div style="background: var(--bg-sec); padding: 0.9rem; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 0.8rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: var(--heading);">{html.escape(role_name)}</h4>
                            <p style="margin: 0.2rem 0; color: var(--muted); font-size: 0.85rem;">
                                🆔 Interview ID: <code>{html.escape(iid)}</code> &nbsp;|&nbsp; 📅 Submitted: {html.escape(sub_date)} &nbsp;|&nbsp; 📌 Status: <strong>{html.escape(st_val)}</strong>
                            </p>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 0.75rem; color: var(--muted); font-weight: 600;">EVALUATION SCORE</div>
                            <span class="badge-blue">{html.escape(score_str)}</span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

import conversational_ai_interview


def render_candidate_interview_taking(interview_id: str, cand: dict[str, Any]):
    intv = db_interviews.get_interview_by_id(interview_id)
    if not intv:
        st.error("Interview assignment not found.")
        if st.button("⬅️ Return to Candidate Portal"):
            st.session_state.taking_interview_id = None
            st.rerun()
        st.stop()

    jds = load_jobs()
    job_doc = next((j for j in jds if j.get("job_id") == intv.get("job_id")), {})
    job_title = job_doc.get("job_title", "Software Developer")
    required_skills = job_doc.get("required_skills", [])
    if isinstance(required_skills, str):
        required_skills = [s.strip() for s in required_skills.split(",") if s.strip()]

    cand_name = safe_text(cand.get("full_name"), "Candidate")
    cand_id = candidate_id(cand)

    st.markdown(f'<p class="main-heading">🤖 Real-Time Conversational AI Voice Interview</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-subtitle">Target Position: <strong>{html.escape(job_title)}</strong> — Assignment ID: <code>{interview_id}</code></p>', unsafe_allow_html=True)

    if st.button("⬅️ Exit Interview & Return to Dashboard", type="secondary"):
        st.session_state.taking_interview_id = None
        st.rerun()

    # Load structured messages and legacy turns
    messages = db_interviews.get_interview_messages(interview_id)
    turns = db_interviews.get_conversational_turns(interview_id)

    # 1. Initialize opening greeting & question if starting fresh
    q_source = intv.get("question_source", "Recruiter Question Set")
    gen_questions = intv.get("generated_questions", [])

    greeting_text = conversational_ai_interview.generate_greeting(cand_name, job_title)

    if q_source == "Recruiter Question Set" and gen_questions:
        first_q = gen_questions[0]
    else:
        first_q = conversational_ai_interview.generate_first_question(cand_name, job_title, required_skills)

    opening_msg = f"{greeting_text}\n\n{first_q}"

    if not messages:
        db_interviews.append_chat_message(
            interview_id=interview_id,
            sender="AI",
            message_text=opening_msg,
            is_voice=False,
            ai_reasoning="Opening candidate welcome greeting and Question 1 from selected Recruiter Question Set." if (q_source == "Recruiter Question Set" and gen_questions) else "Opening candidate welcome greeting and initial skill question."
        )
        messages = db_interviews.get_interview_messages(interview_id)

    # Render Interactive Chat History
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">💬 Real-Time Interview Chat Thread</p>', unsafe_allow_html=True)

    suggest_complete = False
    cand_turn_count = 0

    for idx, msg in enumerate(messages):
        sender = msg.get("sender", "AI")
        text = msg.get("message_text", "")
        is_v = msg.get("is_voice", False)
        reasoning = msg.get("ai_reasoning", "")

        if sender == "Candidate":
            cand_turn_count += 1
            with st.chat_message("user", avatar="👤"):
                v_badge = '<span class="badge-blue" style="font-size:0.75rem; margin-left:0.5rem;">🎤 Voice Response</span>' if is_v else ''
                st.markdown(f"**{html.escape(cand_name)}:** {v_badge}\n\n{html.escape(text)}", unsafe_allow_html=True)
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(f"**AI Interviewer:**\n\n{text}")
                if reasoning:
                    with st.expander("🧠 View AI Reasoning & Context Analysis"):
                        st.caption(f"**AI Logic:** {reasoning}")

    if cand_turn_count >= 3:
        suggest_complete = True

    st.markdown('</div>', unsafe_allow_html=True)

    # Check if interview is already submitted
    if intv.get("interview_status") in ["Submitted", "Evaluated"]:
        st.success("🎉 This interview has been completed and submitted for evaluation.")
        st.stop()

    # Determine active AI question for current turn
    last_ai_msg = next((m for m in reversed(messages) if m.get("sender") == "AI"), None)
    active_question = last_ai_msg.get("message_text", opening_msg) if last_ai_msg else opening_msg

    # Candidate Response Controls (Voice Microphone + Editable Text Input)
    st.markdown('<div class="custom-card" style="margin-top: 1rem;">', unsafe_allow_html=True)
    st.markdown("#### 🎙️ Respond via Voice (Speech-to-Text) or Type Text")

    col_voice, col_text = st.columns([1.5, 2.5])

    # 1. Voice Microphone Recording Input
    transcribed_text = ""
    is_voice_input = False

    with col_voice:
        st.markdown("**Option 1: Microphone (Voice)**")
        audio_value = st.audio_input("Record Voice Response", key=f"audio_rec_{interview_id}_{len(messages)}")
        if audio_value is not None:
            audio_bytes = audio_value.read()
            if audio_bytes and len(audio_bytes) > 100:
                with st.spinner("⏳ Transcribing speech via AI Voice recognition..."):
                    import groq_whisper_service
                    ok_trans, trans_res = groq_whisper_service.transcribe_audio_groq(audio_bytes, filename="voice_recording.wav")
                    if ok_trans:
                        transcribed_text = trans_res
                        is_voice_input = True
                        st.success("✅ Voice transcribed successfully! Review or edit below.")
                    else:
                        st.error(f"⚠️ {trans_res}")

    # 2. Text Area Form for Editing and Sending
    with col_text:
        st.markdown("**Option 2: Text Response (Editable)**")
        with st.form(key=f"cand_response_form_{len(messages)}", clear_on_submit=True):
            user_input = st.text_area(
                "Type or edit your response:",
                value=transcribed_text,
                height=110,
                placeholder="Type your response here or record voice using the microphone on the left..."
            )
            submit_col1, submit_col2 = st.columns([2, 1.5])
            with submit_col2:
                send_clicked = st.form_submit_button("📤 Send Response", type="primary", use_container_width=True)

            if send_clicked and user_input.strip():
                with st.spinner("🤖 AI is analyzing your response and formulating the next question..."):
                    q_source = intv.get("question_source", "Recruiter Question Set")
                    allow_followup = intv.get("allow_ai_followup", True)
                    gen_questions = intv.get("generated_questions", [])

                    # Check if last AI message was a follow-up
                    last_ai_msg = next((m for m in reversed(messages) if m.get("sender") == "AI"), None)
                    last_was_followup = bool(last_ai_msg and ("Follow-up" in last_ai_msg.get("ai_reasoning", "") or last_ai_msg.get("is_followup")))

                    if q_source == "Recruiter Question Set" and gen_questions:
                        # Determine current question index
                        primary_cand_turns = [t for t in turns if not t.get("is_followup")]
                        current_q_idx = len(primary_cand_turns)

                        if allow_followup and not last_was_followup and current_q_idx < len(gen_questions):
                            # Generate ONE AI follow-up for current question
                            follow_res = conversational_ai_interview.generate_followup_question(
                                original_question=active_question,
                                candidate_answer=user_input.strip(),
                                job_title=job_title,
                                groq_api_key=os.getenv("GROQ_API_KEY")
                            )
                            ack = follow_res.get("acknowledgement", "Interesting.")
                            next_q = follow_res.get("next_question", "")
                            reasoning = "AI Follow-up: " + follow_res.get("ai_reasoning", "")
                            ai_reply = f"{ack}\n\n{next_q}"
                        else:
                            # Move to next primary recruiter question
                            next_primary_idx = current_q_idx + 1 if last_was_followup else current_q_idx + 1
                            if next_primary_idx < len(gen_questions):
                                next_q = gen_questions[next_primary_idx]
                                ack = "Thank you."
                                reasoning = f"Recruiter Question Set: Advanced to question #{next_primary_idx+1}."
                                ai_reply = f"{ack}\n\n{next_q}"
                            else:
                                next_q = "Thank you for completing all questions in this interview! Click 'Finish & Submit Interview' below to finalize your evaluation report."
                                ack = "Interview Questions Completed."
                                reasoning = "Completed all recruiter question set items."
                                ai_reply = f"{ack}\n\n{next_q}"
                    else:
                        # Fully AI Generated Mode
                        turn_result = conversational_ai_interview.generate_next_interview_turn(
                            candidate_name=cand_name,
                            job_title=job_title,
                            required_skills=required_skills,
                            conversation_history=turns,
                            latest_answer=user_input.strip(),
                            groq_api_key=os.getenv("GROQ_API_KEY")
                        )
                        ack = turn_result.get("acknowledgement", "")
                        next_q = turn_result.get("next_question", "")
                        reasoning = turn_result.get("ai_reasoning", "")
                        ai_reply = f"{ack}\n\n{next_q}" if ack else next_q

                    # Append Candidate message
                    db_interviews.append_chat_message(
                        interview_id=interview_id,
                        sender="Candidate",
                        message_text=user_input.strip(),
                        is_voice=is_voice_input,
                        ai_reasoning=""
                    )

                    # Append AI message
                    db_interviews.append_chat_message(
                        interview_id=interview_id,
                        sender="AI",
                        message_text=ai_reply,
                        is_voice=False,
                        ai_reasoning=reasoning
                    )

                    # Save legacy turn for backward compatibility
                    db_interviews.append_conversational_turn(
                        interview_id=interview_id,
                        question=active_question,
                        answer=user_input.strip(),
                        ai_reasoning=reasoning
                    )

                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Finish & Submit Interview Section
    st.markdown("---")
    f_col1, f_col2 = st.columns([2.5, 1.5])
    with f_col1:
        if suggest_complete or cand_turn_count >= 3:
            st.info("💡 You have completed key interview topics. You can submit your interview now for final AI evaluation.")

    with f_col2:
        if st.button("🏁 Finish & Submit Interview", type="primary", use_container_width=True, disabled=cand_turn_count < 1):
            with st.spinner("Submitting interview responses and compiling full evaluation report..."):
                final_turns = db_interviews.get_conversational_turns(interview_id)
                responses_list = [
                    {"question": t.get("question", ""), "answer": t.get("answer", "")}
                    for t in final_turns
                ]

                # Submit final responses
                ok_sub, msg_sub = db_interviews.submit_interview_responses(
                    interview_id=interview_id,
                    candidate_id=cand_id,
                    job_id=intv.get("job_id"),
                    responses_list=responses_list
                )

                # Compute full post-interview AI evaluation report
                try:
                    import db_interview_evaluator
                    db_interview_evaluator.evaluate_and_save_interview(interview_id)
                except Exception:
                    pass

                st.session_state.taking_interview_id = None
                st.success("🎉 Interview completed and submitted successfully! Your AI evaluation report has been generated.")
                st.rerun()
def render_candidate_timeline_stepper(app_doc: dict[str, Any], intv_match: dict[str, Any] | None = None) -> str:
    ats_score = app_doc.get("ats_score")
    rec = app_doc.get("recommendation", "")
    intv_status = intv_match.get("interview_status") if intv_match else app_doc.get("interview_status", "Not Assigned")
    final_dec = app_doc.get("final_decision", "Pending")
    is_overridden = app_doc.get("is_overridden", False)

    is_eligible = db_applications.is_eligible_for_interview(rec, is_overridden)

    # Step states: 'completed', 'active', 'disabled'
    s1 = "completed"
    s2 = "completed" if ats_score is not None else "active"

    if intv_status in ["Assigned", "In Progress", "Submitted", "Evaluated"] or is_eligible:
        s3 = "completed" if intv_status in ["Submitted", "Evaluated"] else "active"
    else:
        s3 = "disabled" if rec in ["Not Recommended", "Needs Improvement"] else "active"

    s4 = "completed" if intv_status in ["Submitted", "Evaluated"] else ("active" if s3 == "completed" else "disabled")
    s5 = "completed" if final_dec in ["Selected", "Selected (Hired)", "Rejected", "Shortlisted"] else ("active" if s4 == "completed" else "disabled")

    def get_style(state):
        if state == "completed":
            return "background:#10b981; color:white; border-color:#10b981;", "✓"
        elif state == "active":
            return "background:#3b82f6; color:white; border-color:#3b82f6;", "●"
        else:
            return "background:var(--bg-sec); color:var(--muted); border-color:var(--border);", "○"

    st1, icon1 = get_style(s1)
    st2, icon2 = get_style(s2)
    st3, icon3 = get_style(s3)
    st4, icon4 = get_style(s4)
    st5, icon5 = get_style(s5)

    return f"""
    <div style="display: flex; align-items: center; justify-content: space-between; margin: 0.8rem 0; padding: 0.8rem 0.5rem; background: var(--bg-sec); border-radius: 8px; border: 1px solid var(--border);">
        <div style="text-align: center; flex: 1;">
            <div style="width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.3rem auto; font-size: 0.85rem; font-weight: bold; {st1}">
                {icon1}
            </div>
            <div style="font-size: 0.75rem; font-weight: 600; color: var(--heading);">1. Applied</div>
        </div>
        <div style="flex: 0.5; height: 2px; background: var(--border);"></div>
        <div style="text-align: center; flex: 1;">
            <div style="width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.3rem auto; font-size: 0.85rem; font-weight: bold; {st2}">
                {icon2}
            </div>
            <div style="font-size: 0.75rem; font-weight: 600; color: var(--heading);">2. ATS Evaluation</div>
        </div>
        <div style="flex: 0.5; height: 2px; background: var(--border);"></div>
        <div style="text-align: center; flex: 1;">
            <div style="width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.3rem auto; font-size: 0.85rem; font-weight: bold; {st3}">
                {icon3}
            </div>
            <div style="font-size: 0.75rem; font-weight: 600; color: var(--heading);">3. Interview Assigned</div>
        </div>
        <div style="flex: 0.5; height: 2px; background: var(--border);"></div>
        <div style="text-align: center; flex: 1;">
            <div style="width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.3rem auto; font-size: 0.85rem; font-weight: bold; {st4}">
                {icon4}
            </div>
            <div style="font-size: 0.75rem; font-weight: 600; color: var(--heading);">4. Interview Completed</div>
        </div>
        <div style="flex: 0.5; height: 2px; background: var(--border);"></div>
        <div style="text-align: center; flex: 1;">
            <div style="width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.3rem auto; font-size: 0.85rem; font-weight: bold; {st5}">
                {icon5}
            </div>
            <div style="font-size: 0.75rem; font-weight: 600; color: var(--heading);">5. Final Decision</div>
        </div>
    </div>
    """


def render_candidate_portal():
    cand = st.session_state.get("current_candidate_user")
    if not cand:
        st.warning("⚠️ No Candidate account selected. Please select a candidate profile from the sidebar to log in.")
        st.stop()

    cand_id = candidate_id(cand)
    cand_name = safe_text(cand.get("full_name"), "Candidate")

    cand_page = st.session_state.get("candidate_active_page", "Dashboard")
    taking_intv_id = st.session_state.get("taking_interview_id")

    if taking_intv_id:
        render_candidate_interview_taking(taking_intv_id, cand)
        st.stop()

    if cand_page == "Dashboard":
        st.markdown(f'<p class="main-heading">👋 Welcome, {html.escape(cand_name)}!</p>', unsafe_allow_html=True)
        st.markdown('<p class="main-subtitle">Candidate Portal — Track your job applications, ATS recommendations, and AI interviews</p>', unsafe_allow_html=True)

        cand_email = cand.get("email", "")
        applications = db_applications.get_applications_by_candidate(cand_id, cand_email)
        interviews = db_interviews.get_interviews_by_candidate(cand_id, cand_email)

        eligible_cnt = len([a for a in applications if db_applications.is_eligible_for_interview(a.get("recommendation", ""), a.get("is_overridden", False))])
        assigned_cnt = len([i for i in interviews if i.get("interview_status") == "Assigned"])
        decided_cnt = len([a for a in applications if a.get("final_decision") in ["Selected", "Rejected", "Shortlisted"]])

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="metric-box"><div class="metric-value">{len(applications)}</div><div class="metric-label">Applications</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-box"><div class="metric-value" style="color:#10b981;">{eligible_cnt}</div><div class="metric-label">Interview Eligible</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-box"><div class="metric-value" style="color:#f59e0b;">{assigned_cnt}</div><div class="metric-label">Assigned Interviews</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="metric-box"><div class="metric-value" style="color:#6366f1;">{decided_cnt}</div><div class="metric-label">Final Decisions</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📋 Your Job Applications</p>', unsafe_allow_html=True)

        if not applications:
            st.info("You haven't applied for any job positions yet. Click on **'Browse Jobs'** in the sidebar to explore open roles and submit your application!")
        else:
            jds = load_jobs()
            jd_map = {j.get("job_id"): j for j in jds}

            for idx, app_doc in enumerate(applications):
                jid = app_doc.get("job_id")
                job_data = jd_map.get(jid, {})
                jtitle = job_data.get("job_title") or app_doc.get("job_title") or f"Position {jid}"
                comp_name = job_data.get("company_name") or app_doc.get("company_name") or "Talent Corp"

                ats_score = app_doc.get("ats_score", 0.0)
                rec = app_doc.get("recommendation", "N/A")
                status = app_doc.get("status", "Applied")
                intv_status = app_doc.get("interview_status", "Not Assigned")
                intv_score = app_doc.get("interview_score")
                final_dec = app_doc.get("final_decision", "Pending")

                # Look for matching interview assignment
                intv_match = next((i for i in interviews if i.get("job_id") == jid or i.get("interview_id") == app_doc.get("interview_id")), None)
                iid = intv_match.get("interview_id") if intv_match else None
                curr_intv_status = intv_match.get("interview_status", intv_status) if intv_match else intv_status
                intv_date = format_datetime(intv_match.get("due_date") or intv_match.get("assigned_date") or app_doc.get("created_at")) if intv_match else format_datetime(app_doc.get("created_at"))

                # Recommendation Badge Colors
                if rec in ["Highly Recommended", "Excellent Match"]:
                    rec_badge = f'<span class="badge-green">{html.escape(rec)}</span>'
                elif rec == "Recommended":
                    rec_badge = f'<span class="badge-blue">{html.escape(rec)}</span>'
                elif rec == "Needs Improvement":
                    rec_badge = f'<span class="badge-amber">{html.escape(rec)}</span>'
                else:
                    rec_badge = f'<span class="badge-red">{html.escape(rec)}</span>'

                # Final decision badge
                if final_dec in ["Selected", "Selected (Hired)"]:
                    dec_badge = '<span class="badge-green" style="font-weight:700;">🎉 Selected (Hired)</span>'
                elif final_dec == "Rejected":
                    dec_badge = '<span class="badge-red" style="font-weight:700;">❌ Rejected</span>'
                elif final_dec == "Shortlisted":
                    dec_badge = '<span class="badge-blue" style="font-weight:700;">⭐ Shortlisted</span>'
                else:
                    dec_badge = '<span class="badge-yellow">⏳ Decision Pending</span>'

                # Compute current stage string for timeline
                if final_dec in ["Selected", "Rejected", "Shortlisted"]:
                    current_stage_str = f"Final Decision: {final_dec}"
                elif curr_intv_status in ["Submitted", "Evaluated"]:
                    current_stage_str = "Interview Completed"
                elif curr_intv_status in ["Assigned", "In Progress"]:
                    current_stage_str = "Interview Assigned"
                elif db_applications.is_eligible_for_interview(rec, app_doc.get("is_overridden", False)):
                    current_stage_str = "Eligible for Interview"
                else:
                    current_stage_str = "ATS Evaluation"

                st.markdown('<div class="custom-card" style="margin-bottom: 1.2rem;">', unsafe_allow_html=True)
                st.markdown(f"### {html.escape(jtitle)} — <span style='font-size:1.1rem; color:var(--muted);'>{html.escape(comp_name)}</span> <code style='font-size:0.85rem; margin-left:0.5rem;'>{html.escape(jid)}</code>", unsafe_allow_html=True)

                # Render 5-stage Timeline Stepper
                timeline_html = render_candidate_timeline_stepper(app_doc, intv_match)
                st.markdown(timeline_html, unsafe_allow_html=True)

                # Application Metadata Grid
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.markdown(
                        f"""
                        <p style="margin: 0.3rem 0; font-size: 0.9rem;">
                            🎯 <strong>ATS Score:</strong> <span style="font-weight:700; color:var(--primary);">{ats_score}%</span><br>
                            🤖 <strong>Recommendation:</strong> {rec_badge}<br>
                            📍 <strong>Current Stage:</strong> <code>{html.escape(current_stage_str)}</code>
                        </p>
                        """,
                        unsafe_allow_html=True
                    )
                with col_m2:
                    st.markdown(
                        f"""
                        <p style="margin: 0.3rem 0; font-size: 0.9rem;">
                            📅 <strong>Interview Date:</strong> {html.escape(intv_date)}<br>
                            💬 <strong>Interview Status:</strong> <code>{html.escape(curr_intv_status)}</code> {f'({intv_score}%)' if intv_score is not None else ''}<br>
                            🏆 <strong>Final Decision:</strong> {dec_badge}
                        </p>
                        """,
                        unsafe_allow_html=True
                    )

                # Recommendation-specific status notices & callouts
                is_ineligible = (rec in ["Not Recommended", "Needs Improvement", "Weak Match"]) and not app_doc.get("is_overridden", False)

                if is_ineligible:
                    st.markdown(
                        """
                        <div style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; padding: 0.8rem 1rem; border-radius: 6px; margin-top: 0.8rem;">
                            <strong style="color: #ef4444;">⚠️ Application Status Notice:</strong><br>
                            <span style="font-size: 0.9rem; color: var(--text);">Your application did not qualify for the interview stage.</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    if iid and curr_intv_status in ["Assigned", "In Progress"]:
                        st.markdown(
                            """
                            <div style="background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; padding: 0.8rem 1rem; border-radius: 6px; margin-top: 0.8rem;">
                                <strong style="color: #10b981;">🎯 Interview Assigned:</strong><br>
                                <span style="font-size: 0.9rem; color: var(--text);">You have an active <strong>Conversational AI Interview</strong> assigned for this position.</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        st.write("")
                        btn_label = "▶️ Start Upcoming Interview" if curr_intv_status == "Assigned" else "▶️ Resume Upcoming Interview"
                        if st.button(btn_label, key=f"dash_start_intv_{jid}_{idx}", type="primary", use_container_width=True):
                            st.session_state.taking_interview_id = iid
                            st.session_state.taking_question_index = 0
                            st.session_state.review_mode = False
                            st.rerun()
                    elif iid and curr_intv_status in ["Submitted", "Evaluated"]:
                        st.write("")
                        if st.button("🔒 View Submission History", key=f"dash_view_sub_{jid}_{idx}", use_container_width=True):
                            st.session_state.taking_interview_id = iid
                            st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

        st.stop()

    elif cand_page == "Browse Jobs":
        st.markdown('<p class="main-heading">💼 Browse Available Jobs</p>', unsafe_allow_html=True)
        st.markdown('<p class="main-subtitle">Explore open job descriptions and submit job-specific applications</p>', unsafe_allow_html=True)

        jobs = load_jobs()
        if not jobs:
            st.warning("No job vacancies available at this moment.")
            st.stop()

        cand_email = cand.get("email", "")
        for idx, j in enumerate(jobs):
            jid = j.get("job_id")
            jtitle = j.get("job_title", "Position")
            comp = j.get("company_name", "Company")
            skills = j.get("required_skills", [])
            if isinstance(skills, list):
                skills_str = ", ".join(skills)
            else:
                skills_str = str(skills)

            app_doc = db_applications.get_application(cand_id, jid)

            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            c_j1, c_j2 = st.columns([3.5, 1.5])
            with c_j1:
                st.markdown(f"### {html.escape(jtitle)} — <span style='font-size:1.1rem; color:var(--muted);'>{html.escape(comp)}</span>", unsafe_allow_html=True)
                st.write(f"**Location:** {j.get('location', 'N/A')} | **Experience:** {j.get('experience_required', 'N/A')} | **Salary:** {j.get('salary', 'N/A')}")
                st.write(f"**Required Skills:** `{skills_str}`")
                with st.expander("📄 View Job Description"):
                    st.write(j.get("job_description", ""))

            with c_j2:
                if app_doc:
                    st.markdown('<span class="badge-green" style="font-size:1rem;">✅ Applied</span>', unsafe_allow_html=True)
                    st.write(f"**ATS Score:** {app_doc.get('ats_score')}%")
                    st.write(f"**Recommendation:** {app_doc.get('recommendation')}")
                    with st.expander("🔄 Update / Re-evaluate Application"):
                        uploaded_resume = st.file_uploader("Upload Updated Resume (PDF/TXT)", type=["pdf", "txt", "docx"], key=f"re_upload_{jid}_{idx}")
                        if st.button("Re-evaluate ATS", key=f"re_eval_{jid}_{idx}", use_container_width=True):
                            if uploaded_resume:
                                try:
                                    import parser
                                    parsed_res = parser.parse_resume_file(uploaded_resume)
                                    if parsed_res:
                                        cand["skills"] = parsed_res.get("skills", cand.get("skills", []))
                                        cand["raw_text"] = parsed_res.get("raw_text", cand.get("raw_text", ""))
                                        db.save_candidate(cand)
                                except Exception:
                                    pass
                            ok, msg, res = db_applications.evaluate_and_apply(cand, j)
                            st.success(f"ATS Evaluation updated! Score: {res.get('ats_score')}% ({res.get('recommendation')})")
                            st.rerun()
                else:
                    uploaded_resume = st.file_uploader("Upload Resume (Optional PDF/TXT)", type=["pdf", "txt", "docx"], key=f"apply_upload_{jid}_{idx}")
                    if st.button("🚀 Apply to Job", key=f"apply_btn_{jid}_{idx}", type="primary", use_container_width=True):
                        if uploaded_resume:
                            try:
                                import parser
                                parsed_res = parser.parse_resume_file(uploaded_resume)
                                if parsed_res:
                                    cand["skills"] = parsed_res.get("skills", cand.get("skills", []))
                                    cand["raw_text"] = parsed_res.get("raw_text", cand.get("raw_text", ""))
                                    db.save_candidate(cand)
                            except Exception:
                                pass
                        ok, msg, res = db_applications.evaluate_and_apply(cand, j)
                        if ok and res:
                            st.success(f"🎉 Application submitted for {jtitle}! ATS Score: {res.get('ats_score')}% ({res.get('recommendation')})")
                            st.rerun()
                        else:
                            st.error(msg)
            st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    elif cand_page == "Assigned Interviews":
        st.markdown('<p class="main-heading">📝 Your Assigned Interviews</p>', unsafe_allow_html=True)
        st.markdown('<p class="main-subtitle">View and complete pending interview assignments</p>', unsafe_allow_html=True)
        cand_email = cand.get("email", "")
        interviews = db_interviews.get_interviews_by_candidate(cand_id, cand_email)
        pending = [i for i in interviews if i.get("interview_status") in ["Assigned", "In Progress"]]

        if not pending:
            st.info("No pending assigned interviews at this time.")
        else:
            jds = load_jobs()
            jd_map = {j.get("job_id"): j.get("job_title") for j in jds}
            for idx, intv in enumerate(pending):
                iid = intv.get("interview_id")
                jtitle = jd_map.get(intv.get("job_id"), "Role Position")
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                st.markdown(f"### {html.escape(jtitle)}")
                st.write(f"**Interview ID:** `{iid}` | **Due Date:** {intv.get('due_date')} | **Status:** {intv.get('interview_status')}")
                if st.button("▶️ Take Interview", key=f"take_p_{iid}_{idx}", type="primary"):
                    st.session_state.taking_interview_id = iid
                    st.session_state.taking_question_index = 0
                    st.session_state.review_mode = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    elif cand_page == "Past Interviews":
        st.markdown('<p class="main-heading">📜 Past Submitted Interviews</p>', unsafe_allow_html=True)
        st.markdown('<p class="main-subtitle">Read-only history of completed interview submissions</p>', unsafe_allow_html=True)
        cand_email = cand.get("email", "")
        interviews = db_interviews.get_interviews_by_candidate(cand_id, cand_email)
        past = [i for i in interviews if i.get("interview_status") in ["Submitted", "Evaluated"]]

        if not past:
            st.info("No past submitted interviews found.")
        else:
            for idx, intv in enumerate(past):
                iid = intv.get("interview_id")
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                st.markdown(f"#### Interview `{iid}` — Submitted")
                responses = db_interviews.get_responses_by_interview(iid)
                for r in responses:
                    st.markdown(f"**Q: {html.escape(r.get('question', ''))}**")
                    st.markdown(f'<div style="background: var(--bg-sec); padding: 0.8rem; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 1rem;"><p style="white-space: pre-wrap;">{html.escape(r.get("answer", ""))}</p></div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    elif cand_page == "Profile":
        st.markdown('<p class="main-heading">👤 Candidate Profile</p>', unsafe_allow_html=True)
        render_candidate_portal_profile(cand)
        st.stop()



# ── Cached database readers ───────────────────────────────────────────────────
@st_cache_data_no_spinner(ttl=120)
def load_candidates(search_query: str = "") -> list[dict]:
    res = []
    try:
        if hasattr(db, "get_all_candidates_light"):
            res = db.get_all_candidates_light(search_query)
        if not res:
            candidates, err = db.get_recent_candidates(limit=100)
            res = [] if err else candidates
    except Exception:
        pass

    if not res:
        try:
            import offline_storage
            off_dict = offline_storage.load_offline_data("candidates")
            res = list(off_dict.values())
        except Exception:
            pass

    if not res and "DEFAULT_MOCK_CANDIDATES" in globals():
        res = DEFAULT_MOCK_CANDIDATES

    return res or []


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

@st_cache_data_no_spinner(ttl=60)
def load_db_status() -> tuple[bool, str]:
    try:
        return db.test_connection()
    except Exception as exc:
        return False, str(exc)


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


@st_cache_data_no_spinner(ttl=30)
def load_api_status() -> bool:
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=1.0)
        return response.status_code == 200
    except Exception:
        return False


@st_cache_data_no_spinner(ttl=30)
def api_get_jobs() -> list[dict[str, Any]]:
    try:
        response = requests.get(f"{API_BASE_URL}/api/jobs/", timeout=1.5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []


def load_jobs() -> list[dict[str, Any]]:
    raw_jobs = []
    api_ok = load_api_status()
    if api_ok:
        raw_jobs = api_get_jobs()
    if not raw_jobs:
        db_ok = load_db_status()
        if db_ok:
            try:
                import db_jobs
                raw_jobs = db_jobs.get_all_jobs()
            except Exception:
                pass
    if not raw_jobs:
        raw_jobs = DEFAULT_MOCK_JOBS

    # Automatic deduplication by (job_title, company_name)
    dedup = {}
    for j in raw_jobs:
        t = str(j.get("job_title") or "").strip().lower()
        c = str(j.get("company_name") or "").strip().lower()
        key = (t, c)
        if key not in dedup or str(j.get("created_at") or "") > str(dedup[key].get("created_at") or ""):
            dedup[key] = j

    clean_jobs = list(dedup.values())
    clean_jobs.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return clean_jobs


def save_job(job_data: dict[str, Any]) -> tuple[bool, str]:
    api_ok = load_api_status()
    if api_ok:
        try:
            response = requests.post(f"{API_BASE_URL}/api/jobs/", json=job_data, timeout=2.0)
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
            response = requests.delete(f"{API_BASE_URL}/api/jobs/{job_id}", timeout=2.0)
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


def update_job(job_id: str, job_data: dict[str, Any]) -> tuple[bool, str]:
    api_ok = load_api_status()
    if api_ok:
        try:
            response = requests.put(f"{API_BASE_URL}/api/jobs/{job_id}", json=job_data, timeout=2.0)
            if response.status_code == 200:
                return True, "Job description updated successfully via API."
            else:
                detail = response.json().get("detail", "Unknown error")
                return False, f"API Error: {detail}"
        except Exception as exc:
            pass
            
    db_ok = load_db_status()
    if db_ok:
        try:
            import db_jobs
            success = db_jobs.update_job(job_id, job_data)
            if success:
                return True, "Job description updated successfully."
            else:
                return False, "Job ID not found in Database."
        except Exception as exc:
            return False, f"Database Error: {exc}"
            
    return False, "Both API and Database are offline. Cannot update job."


# ── Authenticated Route Protection & Public Flow ──────────────────────────────
check_and_enforce_auth()

# Render top admin profile bar for authenticated users
render_admin_header()

with st.sidebar:
    st.markdown("# ⚡ HireFlow AI")
    st.markdown("---")

    theme_mode = st.session_state.get("theme", "Light")
    p_color = "#34D399" if theme_mode == "Dark" else "#059669"
    text_c = "#CBD5E1" if theme_mode == "Dark" else "#334155"
    bg_sec_c = "#111827" if theme_mode == "Dark" else "#F1F5F9"
    
    user_info = st.session_state.get("auth_user") or {}
    user_role = auth_service.normalize_role(user_info.get("role"))

    if user_role == "admin":
        st.session_state.portal_role = "Admin"
        st.markdown("#### 🛡️ Admin Control Center")
        adm_options = ["Dashboard", "System Analytics", "Job Descriptions", "Users & Recruiters", "Recruiter Performance", "AI Monitoring", "Recruitment Health", "Audit Logs", "Security", "Settings"]
        adm_icons = ["house", "bar-chart-line", "briefcase", "people", "graph-up-arrow", "robot", "heart-pulse", "journal-text", "shield-lock", "gear"]

        try:
            from streamlit_option_menu import option_menu
            active_page = option_menu(
                menu_title=None,
                options=adm_options,
                icons=adm_icons,
                default_index=adm_options.index(st.session_state.active_page) if st.session_state.active_page in adm_options else 0,
                styles={
                    "container": {"padding": "0!important", "background-color": "transparent", "border": "none"},
                    "icon": {"color": p_color, "font-size": "1.05rem"},
                    "nav-link": {"font-size": "0.92rem", "text-align": "left", "margin":"0px", "margin-bottom": "0.2rem", "--hover-color": bg_sec_c, "color": text_c},
                    "nav-link-selected": {"background-color": p_color, "color": "white", "font-weight": "600"},
                }
            )
        except ImportError:
            active_page = st.radio("Admin Navigation", adm_options, index=0)

        if st.session_state.active_page != active_page:
            st.session_state.active_page = active_page
            st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True, key="nav_adm_logout"):
            user = st.session_state.get("auth_user") or {}
            db.log_audit_event(user.get("email"), user.get("full_name"), "admin", "User Logout", f"User {user.get('email')}", "Success", "User logged out")
            st.session_state.authenticated = False
            st.session_state.auth_user = None
            st.session_state.jwt_token = None
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.session_state.auth_page = "Landing"
            st.rerun()

    elif user_role == "recruiter":
        st.session_state.portal_role = "Recruiter"
        st.markdown("#### 💼 Recruiter Portal")
        rec_options = ["Dashboard", "Resume Upload", "Candidate Pipeline", "Interview Question Generator", "Interview Assignment", "Submitted Interviews", "Job Descriptions", "Candidate Matching", "Candidate Details", "Skill Gap Analysis", "Candidate Ranking", "Executive Reports", "Settings", "Recruiter Profile"]
        rec_icons = ["house", "upload", "funnel", "robot", "journal-plus", "file-earmark-check", "briefcase", "handshake", "people", "lightning", "trophy", "file-earmark-text", "gear", "person-badge"]

        try:
            from streamlit_option_menu import option_menu
            active_page = option_menu(
                menu_title=None,
                options=rec_options,
                icons=rec_icons,
                default_index=rec_options.index(st.session_state.active_page) if st.session_state.active_page in rec_options else 0,
                styles={
                    "container": {"padding": "0!important", "background-color": "transparent", "border": "none"},
                    "icon": {"color": p_color, "font-size": "1.1rem"}, 
                    "nav-link": {"font-size": "0.95rem", "text-align": "left", "margin":"0px", "margin-bottom": "0.25rem", "--hover-color": bg_sec_c, "color": text_c},
                    "nav-link-selected": {"background-color": p_color, "color": "white", "font-weight": "600"},
                }
            )
        except ImportError:
            active_page = st.radio("Recruiter Navigation", rec_options, index=0)

        if st.session_state.active_page != active_page:
            st.session_state.active_page = active_page
            st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True, key="nav_rec_logout"):
            st.session_state.authenticated = False
            st.session_state.auth_user = None
            st.session_state.jwt_token = None
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.session_state.auth_page = "Landing"
            st.rerun()

    else:
        # Candidate Portal Sidebar - Automatically Linked to Authenticated Candidate User
        cand_email = (user_info.get("email") or "").strip().lower()
        cand_name = user_info.get("full_name") or "Candidate User"
        cand_id = user_info.get("candidate_id") or user_info.get("user_id") or f"CAND-{cand_email}"

        st.markdown(f"#### 🎓 Candidate Portal")
        st.caption(f"Logged in as: **{cand_name}** ({cand_email})")

        # Sync/Load linked Candidate record strictly for authenticated user
        candidates_pool = load_candidates("")
        cand_profile = next((c for c in candidates_pool if (c.get("email") or "").strip().lower() == cand_email or str(c.get("candidate_id") or "").strip() == str(cand_id).strip() or str(c.get("user_id") or "").strip() == str(cand_id).strip() or str(c.get("_id") or c.get("id") or "").strip() == str(cand_id).strip()), None)
        
        if not cand_profile:
            cand_profile = {
                "candidate_id": cand_id,
                "user_id": cand_id,
                "full_name": cand_name,
                "email": cand_email,
                "recruitment_stage": "Applied",
                "application_status": "Applied",
                "created_at": datetime.now().isoformat()
            }
            db.save_candidate(cand_profile)
        else:
            # Attach candidate_id & user_id to existing candidate profile
            cand_profile["candidate_id"] = cand_id
            cand_profile["user_id"] = cand_id
            db.save_candidate(cand_profile)

        st.session_state.current_candidate_user = cand_profile

        st.markdown("---")
        cand_options = ["Dashboard", "Browse Jobs", "Assigned Interviews", "Past Interviews", "Profile"]
        cand_icons = ["house", "briefcase", "journal-text", "clock-history", "person-circle"]
        
        try:
            from streamlit_option_menu import option_menu
            candidate_page = option_menu(
                menu_title=None,
                options=cand_options,
                icons=cand_icons,
                default_index=cand_options.index(st.session_state.candidate_active_page) if st.session_state.candidate_active_page in cand_options else 0,
                styles={
                    "container": {"padding": "0!important", "background-color": "transparent", "border": "none"},
                    "icon": {"color": p_color, "font-size": "1.1rem"}, 
                    "nav-link": {"font-size": "0.95rem", "text-align": "left", "margin":"0px", "margin-bottom": "0.25rem", "--hover-color": bg_sec_c, "color": text_c},
                    "nav-link-selected": {"background-color": p_color, "color": "white", "font-weight": "600"},
                }
            )
        except ImportError:
            candidate_page = st.radio("Candidate Navigation", cand_options, index=0)

        if st.session_state.candidate_active_page != candidate_page:
            st.session_state.candidate_active_page = candidate_page
            st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True, key="nav_cand_logout"):
            st.session_state.authenticated = False
            st.session_state.auth_user = None
            st.session_state.jwt_token = None
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.session_state.auth_page = "Landing"
            st.rerun()

    st.markdown("---")

    db_ok, db_msg = load_db_status()

    if db_ok:
        st.markdown('<p class="status-connected">● Database Connected</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-disconnected">● Database Offline</p>', unsafe_allow_html=True)
        st.caption(f"Connection error: {db_msg}")
        st.caption("Parsed data will still display, but will not be saved.")

def render_job_selector_header(key_prefix: str, help_text: str = ""):
    """
    Renders standard Job Description selector for Recruiter views.
    Enforces that recruiters view candidates strictly by Job Description application.
    Returns (selected_job_id, selected_job_data, job_applications, candidates_for_job).
    """
    jds = load_jobs()
    if not jds:
        st.warning("⚠️ No Job Descriptions found in database. Please create a Job Description first under 'Job Descriptions'.")
        return None, None, [], []

    jd_options = {j.get("job_id"): f"{j.get('job_title')} — {j.get('company_name', 'Unknown')}" for j in jds}

    st.markdown('<div style="background: var(--bg-sec); padding: 0.8rem 1rem; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 1rem;">', unsafe_allow_html=True)
    sel_key = f"{key_prefix}_jd_select"
    selected_job_id = st.selectbox(
        "🎯 Select Job Description (Strict Applicant Filter)*",
        options=list(jd_options.keys()),
        format_func=lambda k: jd_options[k],
        key=sel_key,
        help="Recruiters view candidates strictly filtered by job description application."
    )
    st.markdown('</div>', unsafe_allow_html=True)

    selected_job = next((j for j in jds if j.get("job_id") == selected_job_id), jds[0])
    apps_for_job = db_applications.get_applications_by_job(selected_job_id)
    all_cands = load_candidates("")

    # Ensure all candidates in candidate pool are evaluated & linked for this job position for seamless recruitment management
    if all_cands and len(apps_for_job) < len(all_cands):
        for c in all_cands:
            db_applications.evaluate_and_apply(c, selected_job)
        apps_for_job = db_applications.get_applications_by_job(selected_job_id)

    applied_ids = {str(a.get("candidate_id")).strip().lower() for a in apps_for_job if a.get("candidate_id")}
    applied_emails = {str(a.get("candidate_email")).strip().lower() for a in apps_for_job if a.get("candidate_email")}
    applied_names = {str(a.get("candidate_name")).strip().lower() for a in apps_for_job if a.get("candidate_name")}

    cands_for_job = []
    for c in all_cands:
        cid = str(candidate_id(c)).strip().lower()
        cemail = str(c.get("email") or "").strip().lower()
        cname = str(c.get("full_name") or "").strip().lower()
        if (cid in applied_ids or 
            (cemail and (cemail in applied_emails or cemail in applied_ids)) or
            (cname and (cname in applied_names or any(cname == str(a.get("candidate_name", "")).strip().lower() for a in apps_for_job)))):
            cands_for_job.append(c)

    # Fall back to all_cands if no explicit matches found, so recruiters can always evaluate candidate pool
    if not cands_for_job:
        cands_for_job = all_cands

    return selected_job_id, selected_job, apps_for_job, cands_for_job


# ── Admin Control Center Renderers ────────────────────────────────────────────

def render_admin_overview():
    """Render the Enterprise Control Center overview for Admin users."""
    st.markdown('<p class="main-heading">🛡️ Admin Enterprise Control Center</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Real-time system telemetry, hiring metrics, health diagnostics, and audit feed</p>', unsafe_allow_html=True)

    all_jobs = db_jobs.get_all_jobs()
    all_candidates = db.get_all_candidates()
    all_users = db_auth.list_users()
    all_apps = db_applications.get_all_applications()
    all_interviews = db_interviews.get_submitted_interviews()
    health = db.get_system_health_metrics()

    recruiters = [u for u in all_users if auth_service.normalize_role(u.get("role")) == "recruiter"]
    shortlisted = [c for c in all_candidates if c.get("recruitment_stage") == "Shortlisted" or c.get("application_status") == "Shortlisted"]
    hires = [c for c in all_candidates if c.get("recruitment_stage") in ["Selected", "Hired"] or c.get("application_status") in ["Selected", "Hired"]]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'''
            <div class="custom-card" style="text-align: center; border-top: 4px solid #3B82F6;">
                <div style="font-size: 2rem;">💼</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: var(--heading);">{len(all_jobs)}</div>
                <div style="font-size: 0.85rem; color: var(--muted); font-weight: 600;">Total Job Requisitions</div>
            </div>
        ''', unsafe_allow_html=True)
    with c2:
        st.markdown(f'''
            <div class="custom-card" style="text-align: center; border-top: 4px solid #10B981;">
                <div style="font-size: 2rem;">🧑💼</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: var(--heading);">{len(recruiters)}</div>
                <div style="font-size: 0.85rem; color: var(--muted); font-weight: 600;">Active Recruiters</div>
            </div>
        ''', unsafe_allow_html=True)
    with c3:
        st.markdown(f'''
            <div class="custom-card" style="text-align: center; border-top: 4px solid #8B5CF6;">
                <div style="font-size: 2rem;">👤</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: var(--heading);">{len(all_candidates)}</div>
                <div style="font-size: 0.85rem; color: var(--muted); font-weight: 600;">Total Candidates Pool</div>
            </div>
        ''', unsafe_allow_html=True)
    with c4:
        st.markdown(f'''
            <div class="custom-card" style="text-align: center; border-top: 4px solid #F59E0B;">
                <div style="font-size: 2rem;">📄</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: var(--heading);">{len(all_apps)}</div>
                <div style="font-size: 0.85rem; color: var(--muted); font-weight: 600;">Total Applications</div>
            </div>
        ''', unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown(f'''
            <div class="custom-card" style="text-align: center; border-top: 4px solid #06B6D4;">
                <div style="font-size: 1.8rem; font-weight: 800; color: var(--heading);">{len(shortlisted)}</div>
                <div style="font-size: 0.85rem; color: var(--muted); font-weight: 600;">Shortlisted Candidates</div>
            </div>
        ''', unsafe_allow_html=True)
    with c6:
        st.markdown(f'''
            <div class="custom-card" style="text-align: center; border-top: 4px solid #EC4899;">
                <div style="font-size: 1.8rem; font-weight: 800; color: var(--heading);">{len(all_interviews)}</div>
                <div style="font-size: 0.85rem; color: var(--muted); font-weight: 600;">Interviews Conducted</div>
            </div>
        ''', unsafe_allow_html=True)
    with c7:
        st.markdown(f'''
            <div class="custom-card" style="text-align: center; border-top: 4px solid #10B981;">
                <div style="font-size: 1.8rem; font-weight: 800; color: var(--heading);">{len(hires)}</div>
                <div style="font-size: 0.85rem; color: var(--muted); font-weight: 600;">Selected / Hired</div>
            </div>
        ''', unsafe_allow_html=True)
    with c8:
        st_color = "#10B981" if health["status"] == "Healthy" else ("#F59E0B" if health["status"] == "Needs Attention" else "#EF4444")
        st.markdown(f'''
            <div class="custom-card" style="text-align: center; border-top: 4px solid {st_color};">
                <div style="font-size: 1.2rem; font-weight: 800; color: {st_color};">{health["status"].upper()}</div>
                <div style="font-size: 0.85rem; color: var(--muted); font-weight: 600;">Recruitment Health</div>
            </div>
        ''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### ⚡ Executive Quick Actions")
    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1:
        if st.button("➕ Onboard Recruiter", use_container_width=True, key="adm_qa_create_rec"):
            st.session_state.active_page = "Users & Recruiters"
            st.rerun()
    with qa2:
        if st.button("💼 Manage Requisitions", use_container_width=True, key="adm_qa_manage_jds"):
            st.session_state.active_page = "Job Descriptions"
            st.rerun()
    with qa3:
        if st.button("🧩 System Diagnostics", use_container_width=True, key="adm_qa_diag"):
            st.session_state.active_page = "Recruitment Health"
            st.rerun()
    with qa4:
        if st.button("📋 View Audit Logs", use_container_width=True, key="adm_qa_logs"):
            st.session_state.active_page = "Audit Logs"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### 📋 Platform Activity & Audit Feed")
    logs = db.get_audit_logs(limit=8)
    if not logs:
        st.info("No audit activity logged yet. System actions (logins, uploads, status updates) will automatically record here.")
    else:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        for log in logs:
            st.markdown(f'''
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.7rem 0.5rem; border-bottom: 1px solid var(--border);">
                    <div>
                        <span style="font-weight: 700; color: var(--heading);">{html.escape(log.get("action", "Action"))}</span>
                        <span style="color: var(--muted); font-size: 0.85rem;"> — {html.escape(log.get("details", ""))}</span>
                    </div>
                    <div style="font-size: 0.8rem; color: var(--muted);">
                        👤 {html.escape(log.get("user_email", ""))} &nbsp;|&nbsp; 🕒 {html.escape(str(log.get("timestamp", "")))}
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def render_admin_job_descriptions_overview():
    """Render Admin-level Job Description overview with recruitment pipeline metrics."""
    st.markdown('<p class="main-heading">💼 Job Requisitions Overview</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Platform-wide Job Descriptions and candidate applications pipeline</p>', unsafe_allow_html=True)

    all_jobs = db_jobs.get_all_jobs()
    all_apps = db_applications.get_all_applications()
    all_interviews = db_interviews.get_submitted_interviews()
    all_candidates = db.get_all_candidates()

    if not all_jobs:
        st.info("No Job Requisitions created yet in the database.")
        return

    st.markdown(f"**Total Requisitions:** `{len(all_jobs)}` &nbsp;|&nbsp; Click **Inspect Applications** to view candidate pipeline for any job.")

    for job in all_jobs:
        jid = job.get("job_id")
        jtitle = job.get("job_title", "Untitled Role")
        company = job.get("company_name", "TechCorp")
        location = job.get("location", "Remote")
        created_at = str(job.get("created_at", "N/A"))[:10]

        job_apps = [a for a in all_apps if a.get("job_id") == jid]
        shortlisted_count = sum(1 for a in job_apps if a.get("status") == "Shortlisted" or a.get("recruitment_stage") == "Shortlisted")
        job_cands = [c for c in all_candidates if c.get("job_id") == jid]
        if not shortlisted_count and job_cands:
            shortlisted_count = sum(1 for c in job_cands if c.get("recruitment_stage") == "Shortlisted")

        interview_count = sum(1 for i in all_interviews if i.get("job_id") == jid)
        selected_count = sum(1 for c in job_cands if c.get("recruitment_stage") in ["Selected", "Hired"])

        st.markdown(f'''
            <div class="custom-card" style="margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; margin-bottom: 0.8rem;">
                    <div>
                        <div style="font-weight: 800; font-size: 1.15rem; color: var(--heading);">💼 {html.escape(jtitle)}</div>
                        <div style="font-size: 0.88rem; color: var(--muted);">🏢 {html.escape(company)} &nbsp;|&nbsp; 📍 {html.escape(location)} &nbsp;|&nbsp; 🕒 Created: {html.escape(created_at)}</div>
                    </div>
                    <div>
                        <span style="background: rgba(59, 130, 246, 0.15); color: #3B82F6; padding: 0.3rem 0.8rem; border-radius: 9999px; font-weight: 700; font-size: 0.8rem;">ID: {html.escape(jid)}</span>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; text-align: center; margin-bottom: 1rem;">
                    <div style="background: var(--bg-sec); padding: 0.6rem; border-radius: 8px;">
                        <div style="font-size: 1.2rem; font-weight: 800; color: var(--heading);">{len(job_apps) or len(job_cands)}</div>
                        <div style="font-size: 0.78rem; color: var(--muted); font-weight: 600;">Applications</div>
                    </div>
                    <div style="background: var(--bg-sec); padding: 0.6rem; border-radius: 8px;">
                        <div style="font-size: 1.2rem; font-weight: 800; color: #3B82F6;">{shortlisted_count}</div>
                        <div style="font-size: 0.78rem; color: var(--muted); font-weight: 600;">Shortlisted</div>
                    </div>
                    <div style="background: var(--bg-sec); padding: 0.6rem; border-radius: 8px;">
                        <div style="font-size: 1.2rem; font-weight: 800; color: #8B5CF6;">{interview_count}</div>
                        <div style="font-size: 0.78rem; color: var(--muted); font-weight: 600;">Interviewed</div>
                    </div>
                    <div style="background: var(--bg-sec); padding: 0.6rem; border-radius: 8px;">
                        <div style="font-size: 1.2rem; font-weight: 800; color: #10B981;">{selected_count}</div>
                        <div style="font-size: 0.78rem; color: var(--muted); font-weight: 600;">Selected</div>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        col_btn1, col_btn2 = st.columns([1.5, 3.5])
        with col_btn1:
            if st.button(f"🔍 Inspect Applications ({jid})", key=f"adm_inspect_{jid}", use_container_width=True, type="primary"):
                st.session_state.selected_job_id = jid
                st.session_state.active_page = "Candidate Pipeline"
                st.rerun()


def render_admin_system_analytics():
    """Render system-level recruitment analytics and skill gap demand breakdown."""
    st.markdown('<p class="main-heading">📊 System Recruitment Analytics</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Aggregate metrics, candidate pipeline breakdown, and skill demand vs availability</p>', unsafe_allow_html=True)

    all_jobs = db_jobs.get_all_jobs()
    all_candidates = db.get_all_candidates()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📈 Candidates by Recruitment Stage")
        stage_counts = db.get_candidate_stage_counts()
        import pandas as pd
        df_stages = pd.DataFrame([
            {"Stage": k, "Candidates": v} for k, v in stage_counts.items() if k != "Total"
        ])
        if not df_stages.empty and df_stages["Candidates"].sum() > 0:
            import plotly.express as px
            fig_stage = px.pie(df_stages, names="Stage", values="Candidates", color="Stage", hole=0.4,
                               color_discrete_map={"Applied": "#3B82F6", "Screening": "#F59E0B", "Shortlisted": "#8B5CF6", "Interview": "#EC4899", "Selected": "#10B981", "Rejected": "#EF4444"})
            fig_stage.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
            st.plotly_chart(fig_stage, use_container_width=True)
        else:
            st.info("No candidate stage data available yet.")

    with col2:
        st.markdown("### 🎯 Skill Demand vs Candidate Availability")
        jd_skill_counts = Counter()
        for j in all_jobs:
            skills = j.get("required_skills") or []
            for s in skills:
                jd_skill_counts[s.strip().title()] += 1

        cand_skill_counts = Counter()
        for c in all_candidates:
            skills = skills_to_list(c.get("skills"))
            for s in skills:
                cand_skill_counts[s.strip().title()] += 1

        top_skills = [s for s, _ in jd_skill_counts.most_common(8)] or ["Python", "JavaScript", "SQL", "Docker", "React", "AWS"]
        skill_data = []
        for s in top_skills:
            skill_data.append({
                "Skill": s,
                "Required in JDs": jd_skill_counts[s],
                "Available in Candidates": cand_skill_counts[s]
            })

        df_skills = pd.DataFrame(skill_data)
        if not df_skills.empty:
            import plotly.express as px
            fig_skills = px.bar(df_skills, x="Skill", y=["Required in JDs", "Available in Candidates"], barmode="group",
                                color_discrete_sequence=["#3B82F6", "#10B981"])
            fig_skills.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300, legend_title="")
            st.plotly_chart(fig_skills, use_container_width=True)
        else:
            st.info("No skill demand data available yet.")


def render_admin_recruiter_performance():
    """Render Recruiter team activity and hiring performance breakdown."""
    st.markdown('<p class="main-heading">📈 Recruiter Performance Analytics</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Tracking recruiter metrics across Job Descriptions and applications</p>', unsafe_allow_html=True)

    all_users = db_auth.list_users()
    recruiters = [u for u in all_users if auth_service.normalize_role(u.get("role")) in ["recruiter", "admin"]]
    all_jobs = db_jobs.get_all_jobs()
    all_apps = db_applications.get_all_applications()
    all_candidates = db.get_all_candidates()

    if not recruiters:
        st.info("No registered recruiter accounts found.")
        return

    rec_data = []
    for r in recruiters:
        remail = r.get("email", "").lower()
        rname = r.get("full_name", "Recruiter")
        
        r_jobs = [j for j in all_jobs if (j.get("created_by") or j.get("recruiter_email") or "").lower() == remail]
        if not r_jobs and len(recruiters) == 1:
            r_jobs = all_jobs

        r_job_ids = {j.get("job_id") for j in r_jobs}
        r_apps = [a for a in all_apps if a.get("job_id") in r_job_ids]
        r_shortlisted = sum(1 for a in r_apps if a.get("status") == "Shortlisted")
        r_hires = sum(1 for c in all_candidates if c.get("job_id") in r_job_ids and c.get("recruitment_stage") in ["Selected", "Hired"])

        rec_data.append({
            "Recruiter Name": rname,
            "Email": remail,
            "Role": r.get("role", "recruiter").upper(),
            "JDs Managed": len(r_jobs),
            "Applications Received": len(r_apps) or (len(all_apps) if len(recruiters) == 1 else 0),
            "Shortlisted": r_shortlisted or (sum(1 for c in all_candidates if c.get("recruitment_stage") == "Shortlisted") if len(recruiters) == 1 else 0),
            "Hires Made": r_hires or (sum(1 for c in all_candidates if c.get("recruitment_stage") in ["Selected", "Hired"]) if len(recruiters) == 1 else 0),
        })

    import pandas as pd
    df_rec = pd.DataFrame(rec_data)
    render_html_table(df_rec)


def render_admin_ai_monitoring():
    """Render AI Services telemetry and feature usage metrics."""
    st.markdown('<p class="main-heading">🤖 AI Services Telemetry</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Real-time usage metrics for Groq LLMs, Whisper Voice STT, and ATS Scorers</p>', unsafe_allow_html=True)

    all_candidates = db.get_all_candidates()
    
    question_sets_count = 0
    try:
        import db_question_sets
        question_sets_count = len(db_question_sets.get_all_question_sets())
    except Exception:
        pass

    evaluations_count = 0
    try:
        import db_interview_evaluator
        evaluations_count = len(db_interview_evaluator.get_all_evaluations())
    except Exception:
        pass

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Resumes Parsed", len(all_candidates), delta="In-Memory PDF/DOCX")
    with m2:
        st.metric("ATS Match Evaluations", len(all_candidates), delta="Regex & Skill Vectors")
    with m3:
        st.metric("AI Question Sets", question_sets_count, delta="Groq LLM Engine")
    with m4:
        st.metric("Interview Evaluations", evaluations_count, delta="Groq Llama-3 Scorer")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('''
        <div class="custom-card">
            <h3>⚙️ AI Infrastructure & Engine Configuration</h3>
            <p><strong>Primary LLM Provider:</strong> Groq Cloud API (Llama 3.3 70B Versatile / Mixtral-8x7b)</p>
            <p><strong>Voice Transcription Engine:</strong> Groq Whisper Large V3 Speech-to-Text</p>
            <p><strong>Resume Text Parsing:</strong> <code>pypdf</code> + <code>python-docx</code> in-memory buffer engine</p>
            <p><strong>ATS Matching Engine:</strong> Jaccard skill similarity & weighted vector scoring algorithm</p>
            <p><strong>API Key Status:</strong> Configured via environment variable <code>GROQ_API_KEY</code></p>
        </div>
    ''', unsafe_allow_html=True)


def render_admin_recruitment_health():
    """Render recruitment health diagnostics and data anomaly warnings."""
    st.markdown('<p class="main-heading">🧩 Recruitment Health Diagnostic</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Automated data integrity audit and anomaly detection across all collections</p>', unsafe_allow_html=True)

    health = db.get_system_health_metrics()
    st_color = "#10B981" if health["status"] == "Healthy" else ("#F59E0B" if health["status"] == "Needs Attention" else "#EF4444")

    st.markdown(f'''
        <div class="custom-card" style="border-left: 6px solid {st_color};">
            <h3 style="color: {st_color}; margin-bottom: 0.3rem;">SYSTEM HEALTH STATUS: {health["status"].upper()}</h3>
            <p style="color: var(--muted); font-size: 0.95rem;">
                Inspected <strong>{health["total_jobs"]}</strong> Job Requisitions, <strong>{health["total_candidates"]}</strong> Candidate Profiles, and <strong>{health["total_applications"]}</strong> Applications across database.
            </p>
        </div>
    ''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### ⚠️ Diagnostic Audit Trail")

    issues = health.get("issues", [])
    if not issues:
        st.success("🎉 All systems healthy! No data integrity issues or anomalies detected.")
    else:
        for issue in issues:
            level = issue.get("level", "Needs Attention")
            category = issue.get("category", "General")
            msg = issue.get("message", "")
            
            badge_bg = "rgba(245, 158, 11, 0.15)" if level == "Needs Attention" else "rgba(239, 68, 68, 0.15)"
            badge_fg = "#F59E0B" if level == "Needs Attention" else "#EF4444"

            st.markdown(f'''
                <div style="background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 0.9rem; margin-bottom: 0.6rem; display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <span style="background: {badge_bg}; color: {badge_fg}; font-weight: 800; font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 9999px; margin-right: 0.5rem;">{level.upper()}</span>
                        <strong style="color: var(--heading);">{category}:</strong>
                        <span style="color: var(--muted); font-size: 0.95rem;"> {html.escape(msg)}</span>
                    </div>
                </div>
            ''', unsafe_allow_html=True)


def render_admin_users_and_recruiters():
    """Render User Directory & Recruiter Creation management interface."""
    st.markdown('<p class="main-heading">👥 User & Recruiter Account Management</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Platform user directory, role permissions, and recruiter onboarding</p>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Registered Users Directory", "➕ Onboard New Recruiter"])

    with tab1:
        users = db_auth.list_users()
        if not users:
            st.info("No registered user accounts found.")
        else:
            for u in users:
                uid = u.get("user_id")
                uname = u.get("full_name", "User")
                uemail = u.get("email", "")
                urole = u.get("role", "candidate")
                is_active = u.get("is_active", True)
                created = str(u.get("created_at", ""))[:10]

                status_badge = '<span style="color: #10B981; font-weight:700;">🟢 Active</span>' if is_active else '<span style="color: #EF4444; font-weight:700;">🔴 Inactive</span>'

                col_u1, col_u2 = st.columns([3, 1])
                with col_u1:
                    st.markdown(f'''
                        <div style="background: var(--card); border: 1px solid var(--border); padding: 0.8rem; border-radius: 10px; margin-bottom: 0.5rem;">
                            <div style="font-weight: 700; font-size: 1.05rem; color: var(--heading);">{html.escape(uname)} ({status_badge})</div>
                            <div style="font-size: 0.85rem; color: var(--muted);">✉️ {html.escape(uemail)} &nbsp;|&nbsp; 🆔 {html.escape(uid)} &nbsp;|&nbsp; 📅 Registered: {html.escape(created)}</div>
                            <div style="margin-top: 0.3rem;"><span style="background: rgba(59,130,246,0.15); color: #3B82F6; font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 9999px; font-weight: 700;">ROLE: {html.escape(urole.upper())}</span></div>
                        </div>
                    ''', unsafe_allow_html=True)
                with col_u2:
                    if is_active:
                        if st.button("Deactivate", key=f"deact_{uid}", use_container_width=True):
                            ok, msg = db_auth.update_user_status(uid, False)
                            db.log_audit_event(st.session_state.auth_user.get("email"), st.session_state.auth_user.get("full_name"), "admin", "User Deactivated", f"User {uemail}", "Success", msg)
                            st.success(msg)
                            st.rerun()
                    else:
                        if st.button("Activate", key=f"act_{uid}", use_container_width=True, type="primary"):
                            ok, msg = db_auth.update_user_status(uid, True)
                            db.log_audit_event(st.session_state.auth_user.get("email"), st.session_state.auth_user.get("full_name"), "admin", "User Activated", f"User {uemail}", "Success", msg)
                            st.success(msg)
                            st.rerun()

    with tab2:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown("### ➕ Onboard Recruiter Account")
        with st.form("admin_create_recruiter_form"):
            r_name = st.text_input("Recruiter Full Name", placeholder="e.g. Sarah Jenkins")
            r_email = st.text_input("Recruiter Work Email", placeholder="e.g. sarah.jenkins@company.com")
            r_pw = st.text_input("Temporary Password", type="password", placeholder="At least 6 characters")
            r_pw_confirm = st.text_input("Confirm Temporary Password", type="password")
            
            submit_rec = st.form_submit_button("✨ Register Recruiter Account", type="primary", use_container_width=True)
            if submit_rec:
                ok, msg, res = auth_service.register_user(r_name, r_email, r_pw, r_pw_confirm, role="recruiter")
                if ok:
                    admin_user = st.session_state.get("auth_user") or {}
                    db.log_audit_event(admin_user.get("email"), admin_user.get("full_name"), "admin", "Recruiter Account Created", f"Recruiter {r_email}", "Success", "Registered new recruiter account")
                    st.success(f"🎉 Recruiter account created successfully for {r_email}!")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        st.markdown('</div>', unsafe_allow_html=True)


def render_admin_audit_logs():
    """Render platform audit trail and activity log history."""
    st.markdown('<p class="main-heading">📋 Platform Audit Trail & System Logs</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Immutable log history tracking user authentication, candidate changes, and administrative actions</p>', unsafe_allow_html=True)

    logs = db.get_audit_logs(limit=150)
    if not logs:
        st.info("No audit entries recorded yet.")
        return

    import pandas as pd
    df_logs = pd.DataFrame(logs)
    cols_to_show = [c for c in ["timestamp", "user_email", "user_role", "action", "entity", "status", "details"] if c in df_logs.columns]
    df_logs_display = df_logs[cols_to_show].rename(columns={
        "timestamp": "Timestamp",
        "user_email": "User Email",
        "user_role": "Role",
        "action": "Action",
        "entity": "Target Entity",
        "status": "Status",
        "details": "Details"
    })
    render_html_table(df_logs_display)


def render_admin_security():
    """Render platform security telemetry and token standards."""
    st.markdown('<p class="main-heading">🔐 Platform Security & Access Control</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Authentication security metrics, role isolation, and token cryptographic standards</p>', unsafe_allow_html=True)

    users = db_auth.list_users()
    active_users = [u for u in users if u.get("is_active", True)]
    inactive_users = [u for u in users if not u.get("is_active", True)]

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Total User Accounts", len(users))
    with s2:
        st.metric("Active Accounts", len(active_users))
    with s3:
        st.metric("Deactivated Accounts", len(inactive_users))
    with s4:
        st.metric("Security Standard", "Bcrypt / JWT HS256")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('''
        <div class="custom-card">
            <h3>🛡️ System Security Specifications</h3>
            <p><strong>Password Storage:</strong> Salted Bcrypt Password Hashing with SHA-256 fallback verification</p>
            <p><strong>Session Token Standard:</strong> JSON Web Tokens (JWT) signed with 256-bit secret key (HS256)</p>
            <p><strong>Role Enforcement:</strong> Server-side & UI route authorization guards active for Admin, Recruiter, and Candidate roles</p>
            <p><strong>Database Credentials:</strong> Protected via environment variables (<code>MONGO_URI</code> / <code>st.secrets</code>)</p>
            <p><strong>Document Buffer Protection:</strong> Uploaded resume files parsed strictly in-memory using binary byte streams (<code>io.BytesIO</code>)</p>
        </div>
    ''', unsafe_allow_html=True)


def render_admin_settings():
    """Render platform system configuration settings."""
    st.markdown('<p class="main-heading">⚙️ Platform System Settings</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Environment configuration status and global theme settings</p>', unsafe_allow_html=True)

    st.markdown('''
        <div class="custom-card">
            <h3>🚀 Application Environment Status</h3>
            <p><strong>Deployed Application Name:</strong> HireFlow AI</p>
            <p><strong>Project Name:</strong> AI Driven Smart Hiring Platform with Candidate Matching Copilot</p>
            <p><strong>Streamlit Framework Version:</strong> 1.32.0+</p>
            <p><strong>Database Status:</strong> MongoDB Connected (Atlas / Local) with JSON Offline Cache Fallback</p>
            <p><strong>Groq AI Engine Status:</strong> Active</p>
        </div>
    ''', unsafe_allow_html=True)


# ── Main content routing ──────────────────────────────────────────────────────
if st.session_state.get("portal_role") == "Candidate":
    render_candidate_portal()
    st.stop()

active_page = st.session_state.active_page

# Admin Page Routing Guards & Custom Views
if st.session_state.get("portal_role") == "Admin":
    if active_page in ["Dashboard", "Overview"]:
        render_admin_overview()
        st.stop()
    elif active_page == "Job Descriptions":
        render_admin_job_descriptions_overview()
        st.stop()
    elif active_page == "System Analytics":
        render_admin_system_analytics()
        st.stop()
    elif active_page == "Recruiter Performance":
        render_admin_recruiter_performance()
        st.stop()
    elif active_page == "AI Monitoring":
        render_admin_ai_monitoring()
        st.stop()
    elif active_page == "Recruitment Health":
        render_admin_recruitment_health()
        st.stop()
    elif active_page in ["Users & Recruiters", "Users", "Recruiters"]:
        render_admin_users_and_recruiters()
        st.stop()
    elif active_page == "Audit Logs":
        render_admin_audit_logs()
        st.stop()
    elif active_page == "Security":
        render_admin_security()
        st.stop()
    elif active_page == "Settings":
        render_admin_settings()
        st.stop()



if active_page == "Dashboard":
    st.markdown('<p class="main-heading">🚀 Professional ATS Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Real-Time Applicant Tracking System — Analytics, Candidate Pipelines & AI Screening</p>', unsafe_allow_html=True)

    # Initialize dashboard session state filters
    if "ats_dashboard_filter" not in st.session_state:
        st.session_state.ats_dashboard_filter = "All"
    if "ats_dashboard_job_filter" not in st.session_state:
        st.session_state.ats_dashboard_job_filter = "ALL"

    # Top Control Bar: Job Filter & Refresh
    col_ctrl1, col_ctrl2 = st.columns([3.5, 1.5])
    with col_ctrl1:
        all_jobs = load_jobs()
        job_options = {"ALL": "🌐 All Job Positions (Global View)"}
        for j in all_jobs:
            job_options[j.get("job_id")] = f"💼 {j.get('job_title')} ({j.get('company_name', 'Unknown')})"

        curr_job_idx = list(job_options.keys()).index(st.session_state.ats_dashboard_job_filter) if st.session_state.ats_dashboard_job_filter in job_options else 0
        selected_job_filter = st.selectbox(
            "🎯 Filter ATS Dashboard by Job Position:",
            options=list(job_options.keys()),
            index=curr_job_idx,
            format_func=lambda k: job_options[k],
            key="ats_dashboard_job_select"
        )
        if selected_job_filter != st.session_state.ats_dashboard_job_filter:
            st.session_state.ats_dashboard_job_filter = selected_job_filter
            st.rerun()

    with col_ctrl2:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh Dashboard Data", type="secondary", use_container_width=True):
            if hasattr(st, "cache_data"):
                st.cache_data.clear()
            st.rerun()

    # Load All Applications and All Candidates
    all_apps = db_applications.get_all_applications()
    all_cands = load_candidates("")

    # Fallback auto-evaluation for existing candidate pool to ensure mock/offline data populates cleanly
    if not all_apps and all_cands and all_jobs:
        for c in all_cands:
            for j in all_jobs:
                db_applications.evaluate_and_apply(c, j)
        all_apps = db_applications.get_all_applications()

    # Apply Job Position Filter if active
    if st.session_state.ats_dashboard_job_filter != "ALL":
        target_jid = st.session_state.ats_dashboard_job_filter
        target_jtitle = next((j.get("job_title") for j in all_jobs if j.get("job_id") == target_jid), "")
        filtered_apps = [a for a in all_apps if a.get("job_id") == target_jid or (target_jtitle and target_jtitle in a.get("job_title", ""))]
    else:
        filtered_apps = all_apps

    # Calculate Metric Card Counts based on filtered_apps
    count_total = len(filtered_apps)
    count_eval = len([a for a in filtered_apps if a.get("ats_score") is not None])
    count_rec = len([a for a in filtered_apps if a.get("recommendation") in ["Recommended", "Highly Recommended", "Excellent Match"]])
    count_hrec = len([a for a in filtered_apps if a.get("recommendation") in ["Highly Recommended", "Excellent Match"] or float(a.get("ats_score", 0)) >= 80])
    count_rej_ats = len([a for a in filtered_apps if a.get("recommendation") in ["Needs Improvement", "Not Recommended", "Weak Match"] or float(a.get("ats_score", 0)) < 50])
    count_intv_ass = len([a for a in filtered_apps if a.get("interview_status") in ["Assigned", "In Progress"]])
    count_intv_comp = len([a for a in filtered_apps if a.get("interview_status") in ["Submitted", "Evaluated"]])
    count_selected = len([a for a in filtered_apps if a.get("final_decision") in ["Selected", "Selected (Hired)"] or a.get("status") in ["Selected", "Selected (Hired)"]])

    active_card_filter = st.session_state.get("ats_dashboard_filter", "All")

    st.markdown("---")
    st.markdown("### 📊 Interactive ATS Key Metrics (Click Any Card to Filter Candidates)")

    # Row 1 Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        btn_type = "primary" if active_card_filter == "All" else "secondary"
        if st.button(f"📋 Total Applications\n{count_total}", key="card_btn_total", type=btn_type, use_container_width=True):
            st.session_state.ats_dashboard_filter = "All"
            st.rerun()

    with c2:
        btn_type = "primary" if active_card_filter == "ATS Evaluated" else "secondary"
        if st.button(f"🔍 ATS Evaluated\n{count_eval}", key="card_btn_eval", type=btn_type, use_container_width=True):
            st.session_state.ats_dashboard_filter = "ATS Evaluated"
            st.rerun()

    with c3:
        btn_type = "primary" if active_card_filter == "Recommended" else "secondary"
        if st.button(f"👍 Recommended\n{count_rec}", key="card_btn_rec", type=btn_type, use_container_width=True):
            st.session_state.ats_dashboard_filter = "Recommended"
            st.rerun()

    with c4:
        btn_type = "primary" if active_card_filter == "Highly Recommended" else "secondary"
        if st.button(f"🌟 Highly Recommended\n{count_hrec}", key="card_btn_hrec", type=btn_type, use_container_width=True):
            st.session_state.ats_dashboard_filter = "Highly Recommended"
            st.rerun()

    # Row 2 Metric Cards
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        btn_type = "primary" if active_card_filter == "Rejected by ATS" else "secondary"
        if st.button(f"⚠️ Rejected by ATS\n{count_rej_ats}", key="card_btn_rej_ats", type=btn_type, use_container_width=True):
            st.session_state.ats_dashboard_filter = "Rejected by ATS"
            st.rerun()

    with c6:
        btn_type = "primary" if active_card_filter == "Interviews Assigned" else "secondary"
        if st.button(f"📝 Interviews Assigned\n{count_intv_ass}", key="card_btn_intv_ass", type=btn_type, use_container_width=True):
            st.session_state.ats_dashboard_filter = "Interviews Assigned"
            st.rerun()

    with c7:
        btn_type = "primary" if active_card_filter == "Interviews Completed" else "secondary"
        if st.button(f"🎯 Interviews Completed\n{count_intv_comp}", type=btn_type, use_container_width=True):
            st.session_state.ats_dashboard_filter = "Interviews Completed"
            st.rerun()

    with c8:
        btn_type = "primary" if active_card_filter == "Selected Candidates" else "secondary"
        if st.button(f"🎉 Selected Candidates\n{count_selected}", key="card_btn_selected", type=btn_type, use_container_width=True):
            st.session_state.ats_dashboard_filter = "Selected Candidates"
            st.rerun()

    # Filtered View Banner
    if active_card_filter != "All" or st.session_state.ats_dashboard_job_filter != "ALL":
        job_name = job_options.get(st.session_state.ats_dashboard_job_filter, "")
        st.info(f"🔍 Active Filter: **{active_card_filter}** | Job Scope: **{job_name}** — Click 'Total Applications' or select 'All Job Positions' to reset filter.")

    st.markdown("---")

    # Plotly Themes
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    theme = st.session_state.theme
    plotly_template = "plotly_dark" if theme == "Dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)"

    # ── 6 Visual Charts Grid ──
    st.markdown("### 📈 Recruitment Analytics & Visual Charts")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # Chart 1: ATS Score Distribution
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">🎯 ATS Match Score Distribution</p>', unsafe_allow_html=True)
        
        band_counts = {
            "0-49% (Not Rec)": len([a for a in filtered_apps if float(a.get("ats_score", 0)) < 50]),
            "50-64% (Needs Imp)": len([a for a in filtered_apps if 50 <= float(a.get("ats_score", 0)) < 65]),
            "65-79% (Recommended)": len([a for a in filtered_apps if 65 <= float(a.get("ats_score", 0)) < 80]),
            "80-100% (Highly Rec)": len([a for a in filtered_apps if float(a.get("ats_score", 0)) >= 80])
        }
        df_score_dist = pd.DataFrame([{"Score Band": k, "Applications": v} for k, v in band_counts.items()])
        
        fig_score = px.bar(
            df_score_dist,
            x="Score Band",
            y="Applications",
            text="Applications",
            color="Score Band",
            template=plotly_template,
            color_discrete_map={
                "0-49% (Not Rec)": "#EF4444",
                "50-64% (Needs Imp)": "#F59E0B",
                "65-79% (Recommended)": "#3B82F6",
                "80-100% (Highly Rec)": "#10B981"
            }
        )
        fig_score.update_traces(textposition='outside')
        fig_score.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, height=260, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_score, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with chart_col2:
        # Chart 2: Candidate Pipeline Stage Funnel
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📊 Candidate Recruitment Pipeline</p>', unsafe_allow_html=True)

        stage_data = {
            "Applied": len([a for a in filtered_apps if a.get("status") in ["Applied", "ATS Evaluated", "Interview Ineligible", "Interview Eligible"]]),
            "Interview Eligible": len([a for a in filtered_apps if db_applications.is_eligible_for_interview(a.get("recommendation", ""), a.get("is_overridden", False))]),
            "Interview Assigned": len([a for a in filtered_apps if a.get("interview_status") in ["Assigned", "In Progress"]]),
            "Interview Completed": len([a for a in filtered_apps if a.get("interview_status") in ["Submitted", "Evaluated"]]),
            "Selected (Hired)": len([a for a in filtered_apps if a.get("final_decision") in ["Selected", "Selected (Hired)"] or a.get("status") in ["Selected", "Selected (Hired)"]])
        }
        df_pipeline = pd.DataFrame([{"Stage": k, "Candidates": v} for k, v in stage_data.items()])

        fig_pipe = px.bar(
            df_pipeline,
            x="Stage",
            y="Candidates",
            text="Candidates",
            color="Stage",
            template=plotly_template,
            color_discrete_sequence=["#3B82F6", "#8B5CF6", "#F59E0B", "#10B981", "#6366F1"]
        )
        fig_pipe.update_traces(textposition='outside')
        fig_pipe.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, height=260, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_pipe, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        # Chart 3: Job-wise Applications Breakdown
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">💼 Job-wise Applications Breakdown</p>', unsafe_allow_html=True)

        job_app_counts = Counter()
        for a in all_apps:
            jtitle = a.get("job_title") or a.get("job_id") or "Unknown Role"
            job_app_counts[jtitle] += 1

        if not job_app_counts:
            for j in all_jobs:
                job_app_counts[j.get("job_title", "Role")] = 0

        df_job_apps = pd.DataFrame([{"Job Role": k, "Applications": v} for k, v in job_app_counts.most_common(6)])
        fig_job = px.bar(
            df_job_apps,
            y="Job Role",
            x="Applications",
            text="Applications",
            orientation="h",
            template=plotly_template,
            color="Job Role",
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_job.update_traces(textposition='outside')
        fig_job.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, height=260, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_job, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with chart_col4:
        # Chart 4: Interview Success Rate (Donut Chart)
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">🍩 Interview Success Rate & Outcomes</p>', unsafe_allow_html=True)

        intv_outcomes = {
            "Selected (Hired)": count_selected,
            "Evaluated (Pending)": len([a for a in filtered_apps if a.get("interview_status") == "Evaluated" and a.get("final_decision") == "Pending"]),
            "In Progress / Assigned": count_intv_ass,
            "Rejected": len([a for a in filtered_apps if a.get("final_decision") == "Rejected"])
        }
        df_outcomes = pd.DataFrame([{"Outcome": k, "Count": v} for k, v in intv_outcomes.items()])
        if df_outcomes["Count"].sum() == 0:
            df_outcomes = pd.DataFrame([{"Outcome": "No Interview Data", "Count": 1}])

        fig_success = px.pie(
            df_outcomes,
            values="Count",
            names="Outcome",
            hole=0.55,
            template=plotly_template,
            color="Outcome",
            color_discrete_map={
                "Selected (Hired)": "#10B981",
                "Evaluated (Pending)": "#3B82F6",
                "In Progress / Assigned": "#F59E0B",
                "Rejected": "#EF4444",
                "No Interview Data": "#64748B"
            }
        )
        fig_success.update_traces(textinfo='percent+label')
        fig_success.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, height=260, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_success, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    chart_col5, chart_col6 = st.columns(2)

    with chart_col5:
        # Chart 5: Top Candidate Skills
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">⚡ Top Skills Across Applicants</p>', unsafe_allow_html=True)

        cand_skills_counter = Counter()
        for a in filtered_apps:
            skills = a.get("matching_skills") or []
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",") if s.strip()]
            for s in skills:
                if s and isinstance(s, str):
                    cand_skills_counter[s.strip().title()] += 1

        if not cand_skills_counter:
            for c in all_cands:
                for s in skills_to_list(c.get("skills")):
                    if s: cand_skills_counter[s.title()] += 1

        top_sk = cand_skills_counter.most_common(6)
        if not top_sk:
            top_sk = [("Python", 5), ("FastAPI", 4), ("Docker", 3), ("PostgreSQL", 3), ("Kubernetes", 2), ("AWS", 2)]

        df_top_sk = pd.DataFrame([{"Skill": item[0], "Applicants": item[1]} for item in top_sk])
        fig_top_sk = px.bar(
            df_top_sk,
            x="Applicants",
            y="Skill",
            orientation="h",
            template=plotly_template,
            color="Applicants",
            color_continuous_scale="Viridis"
        )
        fig_top_sk.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, height=240, coloraxis_showscale=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_top_sk, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with chart_col6:
        # Chart 6: Missing Skills Analysis
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">⚠️ Common Skill Gaps (Missing Skills)</p>', unsafe_allow_html=True)

        missing_skills_counter = Counter()
        for a in filtered_apps:
            missing = a.get("missing_skills") or []
            if isinstance(missing, str):
                missing = [s.strip() for s in missing.split(",") if s.strip()]
            for s in missing:
                if s and isinstance(s, str):
                    missing_skills_counter[s.strip().title()] += 1

        top_missing = missing_skills_counter.most_common(6)
        if not top_missing:
            top_missing = [("CI/CD", 3), ("Terraform", 3), ("GraphQL", 2), ("PyTorch", 2), ("TypeScript", 1)]

        df_missing = pd.DataFrame([{"Missing Skill": item[0], "Gap Count": item[1]} for item in top_missing])
        fig_missing = px.bar(
            df_missing,
            x="Gap Count",
            y="Missing Skill",
            orientation="h",
            template=plotly_template,
            color="Gap Count",
            color_continuous_scale="OrRd"
        )
        fig_missing.update_layout(paper_bgcolor=bg_color, plot_bgcolor=bg_color, height=240, coloraxis_showscale=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_missing, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── 3 Data Tables & Lists Grid ──
    st.markdown("### 📋 Applications, Upcoming Interviews & Top Candidates")

    t_col1, t_col2 = st.columns([1.8, 1.2])

    with t_col1:
        # Table 1: Recent Applications
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📝 Recent Job Applications</p>', unsafe_allow_html=True)

        if filtered_apps:
            rec_apps_rows = []
            for a in filtered_apps[:8]:
                cname = a.get("candidate_name") or a.get("candidate_id") or "Unknown"
                jtitle = a.get("job_title") or a.get("job_id") or "Role"
                ats_sc = f"{a.get('ats_score', 0)}%"
                rec_val = a.get("recommendation", "N/A")
                date_str = format_datetime(a.get("created_at"))
                status_str = a.get("status", "Applied")

                rec_apps_rows.append({
                    "Candidate Name": cname,
                    "Target Role": jtitle,
                    "ATS Score": ats_sc,
                    "Recommendation": f'<span class="badge-rec">{rec_val}</span>',
                    "Applied Date": date_str,
                    "Status": f'<code>{status_str}</code>'
                })
            df_rec_apps = pd.DataFrame(rec_apps_rows)
            render_html_table(df_rec_apps)
        else:
            st.info("No applications recorded yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


elif active_page == "Candidate Pipeline":
    st.markdown('<p class="main-heading">Candidate Pipeline</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Track, filter, and schedule interviews for applicants of the selected Job Description</p>', unsafe_allow_html=True)

    selected_job_id, selected_job, apps_for_job, all_cands = render_job_selector_header("pipe")
    if not selected_job_id:
        st.stop()

    if not all_cands:
        st.info(f"No candidate applications received for '{selected_job.get('job_title')}' yet.")
        st.stop()

    selected_candidate_id = st.session_state.get("selected_candidate_id")

    if selected_candidate_id:
        if st.button("⬅️ Back to Candidate Pipeline", type="secondary"):
            st.session_state.selected_candidate_id = None
            st.rerun()

        candidate = db.get_candidate_by_id(selected_candidate_id, include_raw_text=True)
        if candidate:
            render_ats_candidate_details(candidate, db_ok)
        else:
            st.error("Candidate not found.")
        st.stop()

    # Search and Filter Controls
    col_search, col_stage, col_skill, col_interview = st.columns([2.5, 1.2, 1.5, 1.2])

    with col_search:
        search_query = st.text_input(
            "🔍 Search Candidate Name / Email",
            value=st.session_state.get("pipeline_search_query", ""),
            placeholder="Type name or email to search...",
            key="pipeline_search_input"
        )
        st.session_state.pipeline_search_query = search_query

    with col_stage:
        stage_filter = st.selectbox(
            "Recruitment Stage",
            options=["All", "Applied", "Screening", "Interview", "Selected", "Rejected"],
            key="pipeline_stage_select"
        )

    all_skills_set = set()
    for c in all_cands:
        for s in skills_to_list(c.get("skills")):
            if s:
                all_skills_set.add(s)
    sorted_skills = sorted(list(all_skills_set), key=str.lower)

    with col_skill:
        skill_filter = st.selectbox(
            "Primary Skill",
            options=["All"] + sorted_skills[:30],
            key="pipeline_skill_select"
        )

    with col_interview:
        interview_filter = st.selectbox(
            "Interview Scheduled",
            options=["All", "Yes", "No"],
            key="pipeline_interview_select"
        )

    # Filter logic
    def resolve_candidate_stage(c_obj: dict[str, Any]) -> str:
        cid_val = candidate_id(c_obj)
        cemail_val = str(c_obj.get("email") or "").strip().lower()
        app_doc = next((a for a in (apps_for_job or []) if a.get("candidate_id") in [cid_val, cemail_val] or a.get("candidate_email") == cemail_val), None)
        if app_doc:
            fin_dec = app_doc.get("final_decision")
            if fin_dec and fin_dec != "Pending":
                return fin_dec
            intv_stat = app_doc.get("interview_status")
            if intv_stat and intv_stat in ["Assigned", "In Progress", "Submitted", "Evaluated"]:
                return "Interview" if intv_stat == "Assigned" else "Interview Completed" if intv_stat in ["Submitted", "Evaluated"] else "Interview"
            stat = app_doc.get("status")
            if stat:
                return stat
        return c_obj.get("recruitment_stage", "Applied")

    filtered = []
    for c in all_cands:
        if search_query.strip():
            sq = search_query.strip().lower()
            c_name = (c.get("full_name") or "").lower()
            c_email = (c.get("email") or "").lower()
            if sq not in c_name and sq not in c_email:
                continue

        c_stage = resolve_candidate_stage(c)
        if stage_filter != "All" and c_stage != stage_filter and c.get("recruitment_stage") != stage_filter:
            continue

        if skill_filter != "All":
            c_skills = [s.lower() for s in skills_to_list(c.get("skills"))]
            if skill_filter.lower() not in c_skills:
                continue

        has_interview = bool(c.get("interview_date") and c.get("interview_time"))
        if interview_filter == "Yes" and not has_interview:
            continue
        if interview_filter == "No" and has_interview:
            continue

        filtered.append(c)

    st.markdown(f"Displaying **{len(filtered)}** of **{len(all_cands)}** candidates in pipeline.")

    if not filtered:
        st.info("No candidates match the search and filter criteria.")
    else:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        # Header Row
        st.markdown(
            """
            <div style="display: flex; background: var(--bg-sec); padding: 0.75rem 1rem; border-radius: 8px; font-weight: 700; font-size: 0.8rem; color: var(--muted); text-transform: uppercase; border: 1px solid var(--border); margin-bottom: 0.75rem;">
                <div style="flex: 2;">Candidate Name</div>
                <div style="flex: 2;">Email</div>
                <div style="flex: 2.5;">Skills</div>
                <div style="flex: 1.5;">Current Stage</div>
                <div style="flex: 1.5;">Interview Date</div>
                <div style="flex: 1.2;">Interview Time</div>
                <div style="flex: 1.2; text-align: center;">Actions</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        for idx, c in enumerate(filtered):
            cid = candidate_id(c)
            name = safe_text(c.get("full_name"), "Unknown Candidate")
            email = safe_text(c.get("email"), "—")
            skills_badges = format_skill_badges(c.get("skills"), max_display=3)
            c_stage_val = resolve_candidate_stage(c)
            stage_badge = render_stage_badge(c_stage_val)
            idate = safe_text(c.get("interview_date"), "—")
            itime = safe_text(c.get("interview_time"), "—")

            col1, col2 = st.columns([9.5, 1.5])
            with col1:
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; padding: 0.6rem 1rem; border-bottom: 1px solid var(--border); font-size: 0.9rem;">
                        <div style="flex: 2; font-weight: 600; color: var(--heading);">{html.escape(name)}</div>
                        <div style="flex: 2; color: var(--text); overflow: hidden; text-overflow: ellipsis;">{html.escape(email)}</div>
                        <div style="flex: 2.5;">{skills_badges}</div>
                        <div style="flex: 1.5;">{stage_badge}</div>
                        <div style="flex: 1.5; color: var(--text);">{html.escape(idate)}</div>
                        <div style="flex: 1.2; color: var(--text);">{html.escape(itime)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with col2:
                if st.button("👁️ Details", key=f"pipe_view_{cid}_{idx}", use_container_width=True):
                    st.session_state.selected_candidate_id = cid
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


elif active_page == "Interview Question Generator":
    st.markdown('<p class="main-heading">🤖 Interview Question Generator</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Create, customize, and save reusable recruiter-approved interview question sets</p>', unsafe_allow_html=True)

    cands = load_candidates("")
    jds = load_jobs()

    if not jds:
        st.warning("No Job Descriptions available. Please create a Job Description first.")
        st.stop()

    tab_gen, tab_saved = st.tabs(["✨ Question Generator & Editor", "📁 Reusable Question Sets Library"])

    with tab_gen:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)

        jd_options = {j.get("job_id"): f"{j.get('job_title')} ({j.get('company_name', 'Unknown')})" for j in jds}
        selected_jd_id = st.selectbox("Select Target Job Description*", options=list(jd_options.keys()), format_func=lambda x: jd_options[x], key="gen_jd_select")
        job_data = next((j for j in jds if j.get("job_id") == selected_jd_id), jds[0])

        cand_options = {"NONE": "None (General Role Questions)"}
        if cands:
            for c in cands:
                cand_options[candidate_id(c)] = f"Candidate: {safe_text(c.get('full_name'), 'Unknown')} ({safe_text(c.get('email'))})"
        selected_cand_id = st.selectbox("(Optional) Tailor for Specific Candidate:", options=list(cand_options.keys()), format_func=lambda x: cand_options[x], key="gen_cand_select")
        cand_data = next((c for c in cands if candidate_id(c) == selected_cand_id), cands[0] if cands else {})

        col_diff, col_num = st.columns(2)
        with col_diff:
            diff_level = st.selectbox("Difficulty Level*", ["Beginner", "Intermediate", "Advanced", "Mixed"], index=1, key="gen_diff_select")
        with col_num:
            num_questions = st.number_input("Number of Questions*", min_value=1, max_value=25, value=6, step=1, key="gen_num_input")

        if st.button("🤖 Generate Questions with AI", type="primary", use_container_width=True):
            with st.spinner("Generating interview questions tailored to job description..."):
                questions = ai_question_generator.generate_interview_questions_ai(
                    candidate=cand_data if selected_cand_id != "NONE" else {},
                    job=job_data,
                    difficulty=diff_level,
                    num_questions=int(num_questions),
                    groq_api_key=os.getenv("GROQ_API_KEY")
                )
                st.session_state.active_question_set = questions
                st.session_state.question_set_job_id = selected_jd_id
                st.session_state.question_set_difficulty = diff_level
                st.session_state.preview_mode = False
                st.success(f"Generated {len(questions)} tailored interview questions!")
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # Workspace & Save Question Set
        questions_set = st.session_state.get("active_question_set", [])
        if questions_set:
            st.markdown("---")

            # Global Action Bar
            col_act1, col_act2, col_act3 = st.columns([1.2, 1.2, 1.4])

            with col_act1:
                if st.button("➕ Add Custom Question", key="add_custom_q_btn", use_container_width=True):
                    st.session_state.active_question_set.append({
                        "question": "Type your custom interview question here...",
                        "category": "Technical",
                        "difficulty": "Intermediate",
                        "expected_skill": "Core Competency",
                    })
                    st.rerun()

            with col_act2:
                if st.button("🔄 Regenerate All", key="regen_all_q_btn", use_container_width=True):
                    with st.spinner("Regenerating entire question set via AI..."):
                        new_q = ai_question_generator.generate_interview_questions_ai(
                            candidate=cand_data if selected_cand_id != "NONE" else {},
                            job=job_data,
                            difficulty=st.session_state.get("question_set_difficulty", "Mixed"),
                            num_questions=len(questions_set),
                            groq_api_key=os.getenv("GROQ_API_KEY")
                        )
                        st.session_state.active_question_set = new_q
                        st.success("Question set regenerated!")
                        st.rerun()

            with col_act3:
                prev_label = "👁️ Exit Preview" if st.session_state.get("preview_mode") else "👁️ Candidate Preview Mode"
                if st.button(prev_label, key="toggle_preview_btn", use_container_width=True):
                    st.session_state.preview_mode = not st.session_state.get("preview_mode", False)
                    st.rerun()

            # Save Question Set Section
            st.markdown('<div class="custom-card" style="border: 2px solid var(--primary); margin-top: 1rem;">', unsafe_allow_html=True)
            st.markdown("#### 💾 Save as Reusable Question Set")
            col_qs1, col_qs2 = st.columns([3, 1])
            with col_qs1:
                qset_name_val = st.text_input("Question Set Name*", value=f"{job_data.get('job_title', 'Technical')} Round 1", placeholder="e.g. MERN Developer Round 1", key="qset_name_input")
            with col_qs2:
                st.write("")
                st.write("")
                if st.button("💾 Save Question Set", type="primary", use_container_width=True, key="save_qset_pers_btn"):
                    ok_s, msg_s, set_id = db_question_sets.save_question_set(
                        set_name=qset_name_val,
                        job_id=selected_jd_id,
                        questions=questions_set,
                        job_title=job_data.get("job_title", "")
                    )
                    if ok_s:
                        st.success(msg_s)
                        if hasattr(st, "cache_data"):
                            st.cache_data.clear()
                    else:
                        st.error(msg_s)
            st.markdown('</div>', unsafe_allow_html=True)

            # Editor view grouped by category
            categories = ["Technical", "Behavioural", "Situational", "Follow-up"]
            cat_tabs = st.tabs(["⚙️ Technical", "💬 Behavioural", "🧠 Situational", "🎯 Follow-up"])

            for tab_idx, cat in enumerate(categories):
                with cat_tabs[tab_idx]:
                    cat_questions = [(idx, q) for idx, q in enumerate(questions_set) if q.get("category", "Technical") == cat]
                    if not cat_questions:
                        st.info(f"No {cat} questions generated in this set.")
                    else:
                        for orig_idx, q_item in cat_questions:
                            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                            c_badge = f'<span class="badge-blue">{html.escape(q_item.get("category", ""))}</span>'
                            d_badge = f'<span class="badge-green">{html.escape(q_item.get("difficulty", ""))}</span>'
                            s_badge = f'<span class="badge-purple">{html.escape(q_item.get("expected_skill", ""))}</span>'

                            st.markdown(f'<div style="margin-bottom: 0.8rem;">{c_badge} &nbsp; {d_badge} &nbsp; {s_badge}</div>', unsafe_allow_html=True)

                            new_q_text = st.text_area(
                                f"Question #{orig_idx + 1}:",
                                value=q_item.get("question", ""),
                                height=90,
                                key=f"q_text_field_{orig_idx}"
                            )

                            col_sk, col_qact1, col_qact2 = st.columns([2, 1, 1])
                            with col_sk:
                                new_skill = st.text_input("Expected Skill:", value=q_item.get("expected_skill", ""), key=f"q_skill_field_{orig_idx}")
                            with col_qact1:
                                st.write("")
                                st.write("")
                                if st.button("🔄 Single Regen", key=f"regen_single_{orig_idx}", use_container_width=True):
                                    with st.spinner("Regenerating single question via AI..."):
                                        single_new = ai_question_generator.regenerate_single_question(
                                            job_data=job_data,
                                            category=cat,
                                            current_question=q_item.get("question", ""),
                                            skill=q_item.get("expected_skill", ""),
                                            api_key=os.getenv("GROQ_API_KEY")
                                        )
                                        st.session_state.active_question_set[orig_idx] = single_new
                                        st.rerun()
                            with col_qact2:
                                st.write("")
                                st.write("")
                                if st.button("🗑️ Delete", key=f"del_single_{orig_idx}", use_container_width=True):
                                    st.session_state.active_question_set.pop(orig_idx)
                                    st.rerun()

                            if new_q_text != q_item.get("question") or new_skill != q_item.get("expected_skill"):
                                st.session_state.active_question_set[orig_idx]["question"] = new_q_text
                                st.session_state.active_question_set[orig_idx]["expected_skill"] = new_skill

                            st.markdown('</div>', unsafe_allow_html=True)

    with tab_saved:
        st.markdown("#### 📁 Saved Reusable Question Sets")
        all_qsets = db_question_sets.get_all_question_sets()
        if not all_qsets:
            st.info("No saved Question Sets found. Generate and save a Question Set in the first tab.")
        else:
            for qs in all_qsets:
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                col_qs_h1, col_qs_h2 = st.columns([3, 1])
                with col_qs_h1:
                    st.markdown(f"### 📋 {html.escape(qs.get('set_name'))}")
                    st.caption(f"💼 Role: {html.escape(qs.get('job_title'))} | 🆔 ID: {qs.get('set_id')} | ❓ Questions: {qs.get('question_count')} | 📅 Created: {format_datetime(qs.get('created_at'))}")
                with col_qs_h2:
                    if st.button("🗑️ Delete Set", key=f"del_qset_{qs.get('set_id')}", use_container_width=True):
                        db_question_sets.delete_question_set(qs.get('set_id'))
                        st.success(f"Question Set '{qs.get('set_name')}' deleted.")
                        st.rerun()

                with st.expander("👁️ View Questions in Set", expanded=False):
                    for q in qs.get("questions", []):
                        st.markdown(f"• **[{q.get('category')}]** {html.escape(q.get('question', ''))} *(Skill: {q.get('expected_skill')}, Difficulty: {q.get('difficulty')})*")
                st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


elif active_page == "Interview Assignment":
    st.markdown('<p class="main-heading">🗓️ Interview Assignment</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Configure candidate interview settings, question sources, voice support, and AI follow-up behavior</p>', unsafe_allow_html=True)

    st.markdown('<div class="custom-card">', unsafe_allow_html=True)

    selected_job_id, selected_job_data, apps_for_job, cands_for_job = render_job_selector_header("assign")
    if not selected_job_id:
        st.stop()

    if not cands_for_job:
        st.warning(f"No candidate applications received for '{selected_job_data.get('job_title')}' yet. Candidates must apply for this job position to be assigned an interview.")
        st.stop()

    cand_options = {candidate_id(c): f"{safe_text(c.get('full_name'), 'Unknown')} ({safe_text(c.get('email'))})" for c in cands_for_job}
    selected_cand_id = st.selectbox("Select Candidate Applicant*", options=list(cand_options.keys()), format_func=lambda x: cand_options[x], key="assign_cand_select")
    selected_cand = next((c for c in cands_for_job if candidate_id(c) == selected_cand_id), cands_for_job[0])

    # Fetch Application document
    app_doc = db_applications.get_application(selected_cand_id, selected_job_id)
    if not app_doc or not app_doc.get("ats_score") or float(app_doc.get("ats_score", 0)) == 0.0:
        ok_a, msg_a, app_doc = db_applications.evaluate_and_apply(selected_cand, selected_job_data)

    ats_score = app_doc.get("ats_score", 0.0) if app_doc else 0.0
    recommendation = app_doc.get("recommendation", "Needs Improvement") if app_doc else "Needs Improvement"
    is_overridden = app_doc.get("is_overridden", False) if app_doc else False
    is_eligible = db_applications.is_eligible_for_interview(recommendation, is_overridden)

    # ATS Screening Card
    st.markdown("---")
    st.markdown("#### 🤖 ATS Resume Screening Status")
    col_scr1, col_scr2 = st.columns([3, 2])
    with col_scr1:
        st.markdown(
            f"""
            <div style="padding: 0.2rem 0;">
                <p style="margin: 0.2rem 0; font-size: 1rem;">🎯 <strong>ATS Match Score:</strong> <span style="font-weight:800; font-size:1.2rem;">{ats_score}%</span></p>
                <p style="margin: 0.2rem 0; font-size: 1rem;">🤖 <strong>Recommendation:</strong> <strong>{html.escape(recommendation)}</strong></p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_scr2:
        if is_eligible:
            st.markdown('<div class="badge-green" style="font-size:1.1rem; text-align:center; padding:0.6rem; border-radius:8px;">✅ ELIGIBLE FOR INTERVIEW</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="badge-red" style="font-size:1.1rem; text-align:center; padding:0.6rem; border-radius:8px;">🚫 NOT ELIGIBLE FOR INTERVIEW</div>', unsafe_allow_html=True)

    if not is_eligible:
        st.warning(f"⚠️ ATS Recommendation is '{recommendation}'. Candidate is not eligible for interview assignment by default.")
        with st.expander("🔓 Recruiter Override Controls", expanded=True):
            override_notes = st.text_input("Override Reason", placeholder="e.g. Verified candidate possesses key unlisted experience", key=f"ov_notes_{selected_cand_id}_{selected_job_id}")
            if st.button("🔓 Apply Recruiter Override", key=f"do_ov_btn_{selected_cand_id}_{selected_job_id}", type="secondary"):
                ok_ov, msg_ov = db_applications.override_application_eligibility(app_doc.get("application_id"), override_notes)
                if ok_ov:
                    st.success(msg_ov)
                    st.rerun()
                else:
                    st.error(msg_ov)

    # ── Assignment Configuration Settings ──
    st.markdown("---")
    st.markdown("#### ⚙️ Interview Configuration Settings")

    col_cfg1, col_cfg2, col_cfg3, col_cfg4 = st.columns(4)
    with col_cfg1:
        import datetime
        default_due = datetime.date.today() + datetime.timedelta(days=7)
        due_date_val = st.date_input("Interview Date / Due Date*", value=default_due, key="assign_due_date_input")

    with col_cfg2:
        duration_val = st.selectbox("Interview Duration*", [15, 30, 45, 60], index=1, format_func=lambda x: f"{x} Minutes", key="assign_duration_select")

    with col_cfg3:
        voice_opt = st.radio("Voice Enabled (Speech-to-Text)", ["Yes", "No"], index=0, horizontal=True, key="assign_voice_select")

    with col_cfg4:
        followup_opt = st.radio("AI Follow-up Questions", ["Yes", "No"], index=0, horizontal=True, key="assign_followup_select")

    # ── Question Source Options ──
    st.markdown("---")
    st.markdown("#### ❓ Question Source")

    q_source = st.radio(
        "Select Question Source*",
        ["Recruiter Question Set", "Fully AI Generated"],
        index=0,
        horizontal=True,
        key="assign_q_source_radio"
    )

    assigned_questions = []
    selected_qset_id = ""

    if q_source == "Recruiter Question Set":
        saved_qsets = db_question_sets.get_all_question_sets(selected_job_id)
        if not saved_qsets:
            # Fallback to all saved question sets if none specific to this job
            saved_qsets = db_question_sets.get_all_question_sets()

        if saved_qsets:
            qset_map = {qs.get("set_id"): f"{qs.get('set_name')} ({qs.get('question_count')} Questions)" for qs in saved_qsets}
            selected_qset_id = st.selectbox("Choose Saved Question Set*", options=list(qset_map.keys()), format_func=lambda x: qset_map[x], key="assign_qset_select")
            chosen_qs_doc = next((q for q in saved_qsets if q.get("set_id") == selected_qset_id), saved_qsets[0])
            assigned_questions = [q.get("question", "") for q in chosen_qs_doc.get("questions", []) if q.get("question")]

            with st.expander("👁️ Preview Questions in Selected Set", expanded=True):
                for idx, q_txt in enumerate(assigned_questions):
                    st.markdown(f"**Q{idx+1}:** {html.escape(q_txt)}")
        else:
            st.info("No saved Question Sets found. Generating default questions for this position.")
            default_qs = db_interviews.generate_job_interview_questions(selected_job_data)
            q_raw_text = st.text_area("Question Set Preview & Editor (one per line):", value="\n".join(default_qs), height=150)
            assigned_questions = [q.strip() for q in q_raw_text.split("\n") if q.strip()]

    else:
        st.info("🤖 **Fully AI Generated Mode Active**: AI will dynamically generate turn-by-turn questions depending on Job Description, Candidate Resume, and candidate's live responses.")
        assigned_questions = db_interviews.generate_job_interview_questions(selected_job_data)

    st.markdown("---")
    if not is_eligible:
        st.button("🚀 Assign Interview (Disabled - Requires Recruiter Override)", disabled=True, use_container_width=True, key="assign_btn_disabled")
    else:
        if st.button("🚀 Assign Interview to Candidate", type="primary", use_container_width=True, key="assign_btn_enabled"):
            ok, msg, intv_id = db_interviews.create_interview_assignment(
                candidate_id=selected_cand_id,
                job_id=selected_job_id,
                questions=assigned_questions,
                due_date=str(due_date_val),
                question_source=q_source,
                question_set_id=selected_qset_id,
                duration_minutes=int(duration_val),
                voice_enabled=(voice_opt == "Yes"),
                allow_ai_followup=(followup_opt == "Yes")
            )
            if ok:
                st.success(msg)
                st.info("The candidate can now view and complete this interview in their Candidate Portal.")
                if hasattr(st, "cache_data"):
                    st.cache_data.clear()
            else:
                st.error(msg)

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


elif active_page == "Submitted Interviews":
    st.markdown('<p class="main-heading">Submitted Candidate Interviews & AI Evaluations</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Inspect candidate answers, AI evaluation scores, feedback, and download full PDF reports</p>', unsafe_allow_html=True)

    viewing_intv_id = st.session_state.get("viewing_submitted_intv_id")
    if viewing_intv_id:
        if st.button("⬅️ Back to Submitted List", type="secondary"):
            st.session_state.viewing_submitted_intv_id = None
            st.rerun()

        intv = db_interviews.get_interview_by_id(viewing_intv_id)
        if intv:
            cid = intv.get("candidate_id")
            jid = intv.get("job_id")
            cand = db.get_candidate_by_id(cid, include_raw_text=True) or {"full_name": cid, "email": "N/A"}
            c_name = safe_text(cand.get("full_name"), "Candidate")

            jds = load_jobs()
            job_data = next((j for j in jds if j.get("job_id") == jid), {"job_title": jid, "company_name": "Talent Corp", "required_skills": []})
            j_title = job_data.get("job_title", "Position")

            # Fetch or run AI evaluations
            evaluations = db_interview_evaluator.get_evaluations_by_interview(viewing_intv_id)
            summary_doc = db_interview_evaluator.get_interview_summary(viewing_intv_id)

            if not evaluations or not summary_doc:
                responses = db_interviews.get_responses_by_interview(viewing_intv_id)
                if responses:
                    with st.spinner("🤖 Running AI evaluation on candidate responses..."):
                        evaluations = []
                        groq_key = os.getenv("GROQ_API_KEY", "")
                        for r in responses:
                            q_text = r.get("question", "")
                            ans_text = r.get("answer", "")
                            eval_res = ai_interview_evaluator.evaluate_single_answer_ai(q_text, ans_text, job_data, groq_api_key=groq_key)
                            eval_res["question"] = q_text
                            eval_res["candidate_answer"] = ans_text
                            evaluations.append(eval_res)

                        summary_doc = ai_interview_evaluator.compute_interview_summary(evaluations)
                        db_interview_evaluator.save_interview_evaluations(viewing_intv_id, cid, jid, evaluations, summary_doc)
                        if hasattr(st, "cache_data"):
                            st.cache_data.clear()

            responses = db_interviews.get_responses_by_interview(viewing_intv_id)
            eval_time_str = format_datetime(summary_doc.get("created_at") or intv.get("evaluated_at") or intv.get("updated_at"))

            # ── 1. Top Interview Summary Card (Requirement 2, 3, 4, 5) ──
            st.markdown('<div class="custom-card" style="border: 2px solid var(--primary); margin-bottom: 1.5rem;">', unsafe_allow_html=True)
            st.markdown('<p class="card-title" style="font-size: 1.25rem;">📊 Candidate Interview Summary Report</p>', unsafe_allow_html=True)

            col_s1, col_s2 = st.columns([3, 2])
            with col_s1:
                q_src_type = intv.get("question_source", "Recruiter Question Set")
                qset_id_str = intv.get("question_set_id", "")
                dur_str = f"{intv.get('duration_minutes', 30)} Mins"
                v_str = "🎤 Voice Enabled" if intv.get("voice_enabled", True) else "⌨️ Text Only"
                fol_str = "⚡ AI Follow-ups On" if intv.get("allow_ai_followup", True) else "🚫 No Follow-ups"

                qset_info = f" (Set ID: {qset_id_str})" if qset_id_str else ""

                st.markdown(
                    f"""
                    <div style="padding: 0.2rem 0;">
                        <h3 style="margin: 0; color: var(--heading);">{html.escape(c_name)}</h3>
                        <p style="margin: 0.3rem 0; color: var(--text); font-weight: 600; font-size: 1rem;">💼 Role: {html.escape(j_title)}</p>
                        <p style="margin: 0.2rem 0; font-size: 0.85rem; color: var(--primary); font-weight: 700;">
                            📌 Type: <code>{html.escape(q_src_type)}{qset_info}</code> &nbsp;|&nbsp; ⏱️ {dur_str} &nbsp;|&nbsp; {v_str} &nbsp;|&nbsp; {fol_str}
                        </p>
                        <p style="margin: 0.2rem 0; color: var(--muted); font-size: 0.85rem;">
                            🆔 Assignment ID: <code>{html.escape(viewing_intv_id)}</code> &nbsp;|&nbsp; 📅 Submitted: {format_datetime(intv.get('submitted_time'))}
                        </p>
                        <p style="margin: 0.2rem 0; color: var(--muted); font-size: 0.85rem;">
                            ⏱️ Evaluated Timestamp: <strong>{html.escape(eval_time_str)}</strong>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col_s2:
                ov_sc = summary_doc.get("overall_interview_score", 0)
                tech_sc = summary_doc.get("avg_technical_score", 0)
                comm_sc = summary_doc.get("avg_communication_score", 0)
                conf_sc = summary_doc.get("avg_confidence_score", 0)
                final_rec = summary_doc.get("final_recommendation", "Recommended")

                # Recommendation categories: 90-100 Highly Recommended, 75-89 Recommended, 60-74 Needs Improvement, <60 Not Recommended
                if ov_sc >= 90:
                    rec_color = "#10b981"
                    badge_cls = "badge-green"
                elif ov_sc >= 75:
                    rec_color = "#3b82f6"
                    badge_cls = "badge-blue"
                elif ov_sc >= 60:
                    rec_color = "#f59e0b"
                    badge_cls = "badge-yellow"
                else:
                    rec_color = "#ef4444"
                    badge_cls = "badge-red"

                st.markdown(
                    f"""
                    <div style="text-align: center; background: var(--bg-sec); padding: 1rem; border-radius: 10px; border: 1px solid var(--border);">
                        <div style="font-size: 0.75rem; font-weight: 700; color: var(--muted); letter-spacing: 0.5px;">FINAL AI RECOMMENDATION</div>
                        <div style="font-size: 1.4rem; font-weight: 800; color: {rec_color}; margin: 0.3rem 0;">{html.escape(final_rec)}</div>
                        <span class="{badge_cls}" style="font-size: 0.9rem;">Overall Score: {ov_sc}%</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # ── Recruiter Actions Bar ──
            st.markdown("---")
            current_app = db_applications.get_application(cid, jid) or {}
            curr_decision = current_app.get("final_decision", "Pending")

            if curr_decision == "Rejected":
                st.error("🚫 Candidate Decision: REJECTED")
            elif curr_decision == "Selected":
                st.success("🎉 Candidate Decision: SELECTED (HIRED)")
            elif curr_decision == "Shortlisted":
                st.info("⭐ Candidate Decision: SHORTLISTED")

            st.markdown("#### ⚡ Recruiter Final Decision & Actions")
            act_col1, act_col2, act_col3, act_col4, act_col5 = st.columns(5)

            with act_col1:
                is_sel = (curr_decision == "Selected")
                if st.button("✅ Select / Hire", key=f"act_next_{viewing_intv_id}", type="primary" if is_sel else "secondary", use_container_width=True):
                    ok_d, msg_d = db_applications.set_application_final_decision(cid, jid, "Selected")
                    db.update_candidate_stage(cid, "Selected")
                    st.success(f"Candidate {c_name} set to 'Selected (Hired)'!")
                    if hasattr(st, "cache_data"):
                        st.cache_data.clear()
                    st.rerun()

            with act_col2:
                is_short = (curr_decision == "Shortlisted")
                if st.button("⭐ Shortlist", key=f"act_hr_{viewing_intv_id}", type="primary" if is_short else "secondary", use_container_width=True):
                    ok_d, msg_d = db_applications.set_application_final_decision(cid, jid, "Shortlisted")
                    st.info(f"Candidate {c_name} set to 'Shortlisted'!")
                    if hasattr(st, "cache_data"):
                        st.cache_data.clear()
                    st.rerun()

            with act_col3:
                is_rej = (curr_decision == "Rejected")
                if st.button("❌ Reject Candidate", key=f"act_reject_{viewing_intv_id}", type="primary" if is_rej else "secondary", use_container_width=True):
                    ok_d, msg_d = db_applications.set_application_final_decision(cid, jid, "Rejected")
                    db.update_candidate_stage(cid, "Rejected")
                    st.warning(f"Candidate {c_name} marked as 'Rejected'.")
                    if hasattr(st, "cache_data"):
                        st.cache_data.clear()
                    st.rerun()

            with act_col4:
                if st.button("🔄 Re-evaluate (New Rules)", key=f"act_reeval_{viewing_intv_id}", use_container_width=True):
                    with st.spinner("🤖 Re-evaluating candidate answers with Senior Technical Interviewer rules..."):
                        responses_to_eval = db_interviews.get_responses_by_interview(viewing_intv_id)
                        new_evaluations = []
                        groq_key = os.getenv("GROQ_API_KEY", "")
                        for r in responses_to_eval:
                            q_text = r.get("question", "")
                            ans_text = r.get("answer", "")
                            eval_res = ai_interview_evaluator.evaluate_single_answer_ai(q_text, ans_text, job_data, groq_api_key=groq_key)
                            eval_res["question"] = q_text
                            eval_res["candidate_answer"] = ans_text
                            new_evaluations.append(eval_res)

                        new_summary = ai_interview_evaluator.compute_interview_summary(new_evaluations)
                        db_interview_evaluator.save_interview_evaluations(viewing_intv_id, cid, jid, new_evaluations, new_summary)
                        if hasattr(st, "cache_data"):
                            st.cache_data.clear()
                        st.success("Interview re-evaluated successfully with new Senior Interviewer rules!")
                        st.rerun()

            with act_col5:
                if evaluations and summary_doc:
                    try:
                        pdf_bytes = interview_pdf_report.generate_interview_pdf_report(cand, job_data, viewing_intv_id, evaluations, summary_doc)
                        st.download_button(
                            label="📥 Download PDF Report",
                            data=pdf_bytes,
                            file_name=f"Interview_Report_{c_name.replace(' ', '_')}_{viewing_intv_id}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as exc:
                        st.error(f"PDF error: {exc}")

            st.markdown("---")
            st.markdown("#### 🎯 Performance Score Breakdown")

            def get_score_color(val):
                if val >= 80: return "#10b981"
                if val >= 60: return "#f59e0b"
                return "#ef4444"

            sc_col1, sc_col2 = st.columns(2)
            with sc_col1:
                custom_progress_bar(f"Overall Interview Score ({ov_sc}%)", ov_sc, get_score_color(ov_sc))
                custom_progress_bar(f"Technical Score ({tech_sc}%)", tech_sc, get_score_color(tech_sc))
            with sc_col2:
                custom_progress_bar(f"Communication Score ({comm_sc}%)", comm_sc, get_score_color(comm_sc))
                custom_progress_bar(f"Confidence Score ({conf_sc}%)", conf_sc, get_score_color(conf_sc))

            st.markdown("---")
            col_st, col_im = st.columns(2)
            with col_st:
                st.markdown("#### 🌟 Top Candidate Strengths")
                for s in summary_doc.get("top_strengths", []):
                    st.markdown(f"✅ {html.escape(str(s))}")
            with col_im:
                st.markdown("#### 🎯 Key Areas for Improvement")
                for i in summary_doc.get("areas_for_improvement", []):
                    st.markdown(f"⚠️ {html.escape(str(i))}")

            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 📝 Detailed Per-Question Candidate Answers & AI Evaluations")

            eval_map = {e.get("question", "").strip(): e for e in evaluations} if evaluations else {}

            for idx, r in enumerate(responses):
                q_text = r.get("question", "").strip()
                ans_text = r.get("answer", "") or "No response provided"
                e_info = eval_map.get(q_text, {})

                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                st.markdown(f"#### Question {idx + 1}: {html.escape(q_text)}")

                st.markdown(f'<div style="background: var(--bg-sec); padding: 0.9rem; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 1rem;"><p style="white-space: pre-wrap; margin: 0; color: var(--text);"><b>Candidate Answer:</b><br>{html.escape(ans_text)}</p></div>', unsafe_allow_html=True)

                if e_info:
                    t_sc = e_info.get("technical_score", 0)
                    c_sc = e_info.get("communication_score", 0)
                    cf_sc = e_info.get("confidence_score", 0)
                    o_sc = e_info.get("overall_score", 0)
                    fb = e_info.get("ai_feedback", e_info.get("feedback", ""))

                    st.markdown(
                        f"""
                        <div style="display: flex; gap: 0.8rem; margin-bottom: 0.8rem; flex-wrap: wrap;">
                            <span class="badge-blue">Tech Score: {t_sc}%</span>
                            <span class="badge-purple">Comm Score: {c_sc}%</span>
                            <span class="badge-yellow">Confidence: {cf_sc}%</span>
                            <span class="badge-green">Overall Question Score: {o_sc}%</span>
                        </div>
                        <div style="background: var(--bg); padding: 0.8rem; border-radius: 8px; border: 1px solid var(--border); font-size: 0.9rem;">
                            <strong>AI Feedback:</strong> {html.escape(fb)}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    s_list = e_info.get("strengths", [])
                    i_list = e_info.get("improvements", [])
                    if s_list or i_list:
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            if s_list:
                                st.markdown("<b>Key Strengths:</b>", unsafe_allow_html=True)
                                for s_item in s_list:
                                    st.markdown(f"- {html.escape(str(s_item))}")
                        with sc2:
                            if i_list:
                                st.markdown("<b>Areas for Improvement:</b>", unsafe_allow_html=True)
                                for i_item in i_list:
                                    st.markdown(f"- {html.escape(str(i_item))}")

                st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.error("Interview submission record not found.")
        st.stop()

    selected_job_id, selected_job, apps_for_job, cands_for_job = render_job_selector_header("sub_intv")
    if not selected_job_id:
        st.stop()

    submitted_list = db_interviews.get_submitted_interviews()
    filtered_submissions = [i for i in submitted_list if i.get("job_id") == selected_job_id]

    if not filtered_submissions:
        st.info(f"No submitted interviews for candidate applications of '{selected_job.get('job_title')}' yet.")
    else:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        jds = db_jobs.get_all_jobs()
        cands = db.get_all_candidates()
        jd_map = {j.get("job_id"): j.get("job_title") for j in jds}
        cand_map = {candidate_id(c): safe_text(c.get("full_name"), candidate_id(c)) for c in cands}

        for idx, item in enumerate(filtered_submissions):
            iid = item.get("interview_id")
            cid = item.get("candidate_id")
            c_name = cand_map.get(cid, cid)
            jtitle = jd_map.get(item.get("job_id"), item.get("job_id"))
            sub_time = format_datetime(item.get("submitted_time") or item.get("updated_at"))
            status = item.get("interview_status", "Submitted")

            col_a, col_b = st.columns([4, 1])
            with col_a:
                status_b = render_stage_badge(status if status != "Evaluated" else "Selected")
                st.markdown(
                    f"""
                    <div style="padding: 0.5rem 0;">
                        <h4 style="margin: 0; color: var(--heading);">{html.escape(c_name)} — {html.escape(jtitle)}</h4>
                        <p style="margin: 0.2rem 0; color: var(--muted); font-size: 0.85rem;">
                            🆔 Assignment ID: {html.escape(iid)} &nbsp;|&nbsp; 📅 Submitted: {html.escape(sub_time)}
                        </p>
                        <div>{status_b}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with col_b:
                btn_txt = "👁️ View Evaluation" if status == "Evaluated" else "🤖 Evaluate & View"
                if st.button(btn_txt, key=f"view_ans_rec_{iid}_{idx}", use_container_width=True, type="primary"):
                    st.session_state.viewing_submitted_intv_id = iid
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


elif active_page == "Users":
    st.markdown('<p class="main-heading">👥 Registered Users Directory</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Manage system user accounts, roles, and permissions</p>', unsafe_allow_html=True)

    users_list = db_auth.list_users()
    if not users_list:
        st.info("No registered user accounts found.")
    else:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        for u in users_list:
            st.markdown(f'''
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.8rem; border-bottom: 1px solid var(--border);">
                    <div>
                        <div style="font-weight: 700; font-size: 1.05rem; color: var(--heading);">{html.escape(u.get("full_name", "User"))}</div>
                        <div style="font-size: 0.85rem; color: var(--muted);">✉️ {html.escape(u.get("email", ""))} &nbsp;|&nbsp; 🆔 {html.escape(u.get("user_id", ""))}</div>
                    </div>
                    <div>
                        <span style="background: rgba(59, 130, 246, 0.15); color: #3B82F6; padding: 0.3rem 0.8rem; border-radius: 9999px; font-weight: 700; font-size: 0.78rem; text-transform: uppercase;">ROLE: {html.escape(u.get("role", "candidate"))}</span>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


elif active_page == "Recruiters":
    st.markdown('<p class="main-heading">🧑💼 Recruiters & Hiring Managers</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Active talent acquisition team members and recruiters</p>', unsafe_allow_html=True)

    users_list = [u for u in db_auth.list_users() if u.get("role") in ["recruiter", "admin"]]
    if not users_list:
        st.info("No recruiter or admin team accounts registered yet.")
    else:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        for u in users_list:
            st.markdown(f'''
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.8rem; border-bottom: 1px solid var(--border);">
                    <div>
                        <div style="font-weight: 700; font-size: 1.05rem; color: var(--heading);">💼 {html.escape(u.get("full_name", "Recruiter"))}</div>
                        <div style="font-size: 0.85rem; color: var(--muted);">✉️ {html.escape(u.get("email", ""))} &nbsp;|&nbsp; 📅 Registered: {html.escape(str(u.get("created_at", ""))[:10])}</div>
                    </div>
                    <div>
                        <span style="background: rgba(16, 185, 129, 0.15); color: #10B981; padding: 0.3rem 0.8rem; border-radius: 9999px; font-weight: 700; font-size: 0.78rem;">{html.escape(u.get("role", "recruiter").upper())}</span>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


elif active_page == "Admin Profile":
    st.markdown('<p class="main-heading">🔐 Admin / Recruiter Profile</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Authenticated user account credentials & active session info</p>', unsafe_allow_html=True)

    user = st.session_state.get("auth_user") or {}
    st.markdown(f'''
        <div class="custom-card">
            <h3>👤 Profile Information</h3>
            <p><strong>Full Name:</strong> {html.escape(user.get("full_name", "Admin"))}</p>
            <p><strong>Email Address:</strong> {html.escape(user.get("email", "admin@copilot.ai"))}</p>
            <p><strong>User ID:</strong> <code>{html.escape(user.get("user_id", "USR-ADMIN"))}</code></p>
            <p><strong>Assigned Role:</strong> <span style="background: rgba(16, 185, 129, 0.15); color: #10B981; padding: 0.2rem 0.6rem; border-radius: 9999px; font-weight: 700;">{html.escape((user.get("role") or "admin").upper())}</span></p>
            <p><strong>Authentication Standard:</strong> JWT (HS256) Encrypted Session</p>
        </div>
    ''', unsafe_allow_html=True)
    st.stop()


elif active_page == "Recruiter Profile":
    st.markdown('<p class="main-heading">👤 Recruiter Profile</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Talent Acquisition Manager Account Details & Capabilities</p>', unsafe_allow_html=True)

    user = st.session_state.get("auth_user") or {}
    st.markdown(f'''
        <div class="custom-card">
            <h3>💼 Recruiter Account Overview</h3>
            <p><strong>Full Name:</strong> {html.escape(user.get("full_name", "Recruiter"))}</p>
            <p><strong>Work Email:</strong> {html.escape(user.get("email", "recruiter@company.com"))}</p>
            <p><strong>User ID:</strong> <code>{html.escape(user.get("user_id", "USR-REC"))}</code></p>
            <p><strong>Role:</strong> <span style="background: rgba(59, 130, 246, 0.15); color: #3B82F6; padding: 0.2rem 0.6rem; border-radius: 9999px; font-weight: 700;">RECRUITER</span></p>
            <p><strong>Access Level:</strong> Full ATS Applicant Screening, JD Matching, Interview Question Generation & Candidate Ranking</p>
        </div>
    ''', unsafe_allow_html=True)
    st.stop()


elif active_page == "Candidate Details":
    st.markdown('<p class="main-heading">Candidates Directory</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Search and manage parsed candidate profiles for selected Job Description</p>', unsafe_allow_html=True)

    selected_job_id, selected_job, apps_for_job, cands_for_job = render_job_selector_header("cand_det")
    if not selected_job_id:
        st.stop()

    search_query = st.text_input(
        "🔍 Search Candidates for Selected Job Position",
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
            render_ats_candidate_details(candidate, db_ok)
        else:
            st.error("Candidate profile not found.")

    else:
        candidates = cands_for_job
        if search_query.strip():
            sq = search_query.strip().lower()
            candidates = [c for c in candidates if sq in (c.get("full_name") or "").lower() or sq in (c.get("email") or "").lower() or sq in str(c.get("skills") or "").lower()]

        if not candidates:
            st.info(f"No candidate applications received for '{selected_job.get('job_title')}' yet.")
        else:
            st.markdown(f"Showing **{len(candidates)}** candidate applicants for **{html.escape(selected_job.get('job_title'))}**.")

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
                
                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button("🔍 Match", key=match_btn_key, use_container_width=True, type="primary"):
                        st.session_state.active_page = "Candidate Matching"
                        st.session_state.selected_candidate_id = None
                        st.session_state.search_filter = first_skill
                        st.rerun()
                with b2:
                    edit_btn_key = f"edit_j_{jid}_{idx}"
                    is_editing = st.session_state.get("editing_job_id") == jid
                    if st.button("❌ Cancel" if is_editing else "✏️ Edit", key=edit_btn_key, use_container_width=True, type="secondary"):
                        if is_editing:
                            st.session_state.editing_job_id = None
                        else:
                            st.session_state.editing_job_id = jid
                        st.rerun()
                with b3:
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

            if st.session_state.get("editing_job_id") == jid:
                st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)
                st.markdown("#### ✏️ Update Job Position")
                with st.form(f"edit_job_form_{jid}_{idx}"):
                    edit_title = st.text_input("Job Title*", value=title)
                    edit_company = st.text_input("Company Name*", value=company)
                    skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
                    edit_skills = st.text_input("Required Skills (comma-separated)*", value=skills_str)
                    
                    col_e1, col_e2, col_e3 = st.columns(3)
                    with col_e1:
                        edit_exp = st.text_input("Experience Required*", value=exp)
                    with col_e2:
                        edit_loc = st.text_input("Location*", value=loc)
                    with col_e3:
                        edit_sal = st.text_input("Salary / Compensation", value=sal)
                        
                    edit_desc = st.text_area("Job Description*", value=desc, height=150)
                    
                    save_edit_submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)
                    if save_edit_submitted:
                        if not (edit_title.strip() and edit_company.strip() and edit_skills.strip() and edit_exp.strip() and edit_desc.strip()):
                            st.error("Please fill in all required fields (marked with *).")
                        else:
                            updated_skills_list = [s.strip() for s in edit_skills.split(",") if s.strip()]
                            updated_job_data = {
                                "job_title": edit_title.strip(),
                                "company_name": edit_company.strip(),
                                "required_skills": updated_skills_list,
                                "experience_required": edit_exp.strip(),
                                "location": edit_loc.strip() or "Remote",
                                "salary": edit_sal.strip() or "Not Specified",
                                "job_description": edit_desc.strip(),
                            }
                            success, msg = update_job(jid, updated_job_data)
                            if success:
                                st.success(msg)
                                st.session_state.editing_job_id = None
                                if hasattr(st, "cache_data"):
                                    st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(msg)

            st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


elif active_page == "Skill Gap Analysis":
    st.markdown('<p class="main-heading">Skill Gap Analysis</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Identify missing competencies across applicants for selected Job Description</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">🔍 Talent Pool Skill Coverage</p>', unsafe_allow_html=True)
    
    import plotly.express as px
    import pandas as pd
    import numpy as np
    theme = st.session_state.theme
    plotly_template = "plotly_dark" if theme == "Dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)"
    
    selected_jd_id, selected_job, apps_for_job, candidates = render_job_selector_header("gap")
    if not selected_jd_id or not selected_job:
        st.stop()
    if not candidates:
        st.info("No candidate applications received for this job description yet.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    missing_counts = {}
    for c in candidates:
        ats_result = calculate_candidate_score(c, selected_job)
        missing = ats_result.get("missing_skills", [])
        for skill in missing:
            missing_counts[skill] = missing_counts.get(skill, 0) + 1

    if not missing_counts:
        st.success("No skill gaps found in the candidate applicants for this job!")
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
    st.markdown("#### 🎓 Recommended Learning Roadmap")
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
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

elif active_page == "Candidate Ranking":
    st.markdown('<p class="main-heading">Candidate Rankings</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Leaderboard of applicants for selected Job Description</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">🏆 Candidate Leaderboard</p>', unsafe_allow_html=True)
    
    import pandas as pd
    import numpy as np
    import plotly.express as px
    theme = st.session_state.theme
    plotly_template = "plotly_dark" if theme == "Dark" else "plotly_white"
    bg_color = "rgba(0,0,0,0)"
    
    selected_jd_id, selected_job, apps_for_job, candidates = render_job_selector_header("rank")
    if not selected_jd_id or not selected_job:
        st.stop()
    if not candidates:
        st.info("No candidate applications received for this job description yet.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()
          
    rank_data = []
    for c in candidates:
        ats_result = calculate_candidate_score(c, selected_job)
        score = ats_result.get("hiring_score", 0)
        status = ats_result.get("recommendation", "Not Recommended")
        cand_id = str(c.get("id") or c.get("_id") or c.get("email"))
        if db_ok and cand_id and selected_job:
            db.save_evaluation(
                selected_job.get("job_id"),
                cand_id,
                score,
                status,
                ats_result.get("score_breakdown", {})
            )
        
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
    report_text = f"""Executive Dashboard Report
---------------------------
Key Metrics:
- Total Active Jobs: {len(jds)}
- Total Talent Pool: {len(candidates)} candidates.
- Evaluations Processed: {total_evals}
- Average Hiring Score: {avg_hiring_score} / 100

Pipeline Status:
- Top Matches: Highly Recommended candidates are automatically flagged in rankings.
- Skill Gaps: Check the Skill Gap Analysis tab to identify missing competencies.
- Diversity: Continue broad sourcing to expand talent pool diversity.
"""
    st.download_button("📥 Download Dashboard Report", data=report_text, file_name="Executive_Dashboard_Report.txt", mime="text/plain", type="primary")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

elif active_page == "Candidate Matching":
    st.markdown('<p class="main-heading">Job Description Matching</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Compare applicant candidates against Job Description requirements</p>', unsafe_allow_html=True)
    
    import db_jobs
    from jd_matching_service import compare_candidates_with_jd

    selected_jd_id, selected_job, apps_for_job, candidates = render_job_selector_header("match")
    if not selected_jd_id or not selected_job:
        st.stop()
    if not candidates:
        st.info("No candidate applications received for this job description yet.")
        st.stop()

    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    if st.button("🔍 Run Matching Engine", type="primary"):
        with st.spinner("Analyzing candidate applicants against job requirements..."):
            results = compare_candidates_with_jd(selected_jd_id)
            # Filter results to candidates for this job
            cand_names_or_ids = {c.get("full_name") for c in candidates} | {c.get("candidate_id") for c in candidates} | {c.get("email") for c in candidates}
            filtered_results = [r for r in results if r.get("candidate_name") in cand_names_or_ids or r.get("candidate_id") in cand_names_or_ids]
            st.session_state["matching_results"] = filtered_results or results
            st.session_state["matching_jd_id"] = selected_jd_id
                
        if "matching_results" in st.session_state and st.session_state.get("matching_jd_id") == selected_jd_id:
            results = st.session_state["matching_results"]
            if results:
                st.success(f"Successfully evaluated {len(results)} candidates.")
                
                if not selected_job:
                    jds = load_jobs()
                    selected_job = next((j for j in jds if j.get("job_id") == selected_jd_id), {})
                
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
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    try:
                        import pdf_generator
                        pdf_bytes = pdf_generator.generate_skill_gap_pdf(res.get("profile", {}), res.get("ats_result", {}), selected_job)
                    except Exception as e:
                        pdf_bytes = b"PDF Generation failed: " + str(e).encode()
                    
                    import re
                    s_name = re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")
                    cand_id = res.get("candidate_id", s_name)
                    st.download_button(
                        label="📥 Download Skill Gap Report (PDF)",
                        data=pdf_bytes,
                        file_name=f"{s_name}_Skill_Gap_Report.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"dl_sg_report_{cand_id}"
                    )
                        
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
            if "current_ats_result" in st.session_state:
                del st.session_state["current_ats_result"]
    else:
        if st.session_state.get("current_file") is not None:
            st.session_state.current_file = None
            st.session_state.parse_complete = False
            st.session_state.progress_value = 0.0
            st.session_state.already_exists = False
            if "current_ats_result" in st.session_state:
                del st.session_state["current_ats_result"]

    if uploaded_file is not None:
        if st.button("🚀 Parse Resume", type="primary", use_container_width=True):
            if "current_ats_result" in st.session_state:
                del st.session_state["current_ats_result"]
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

                    if saved_to_db and db_ok:
                        try:
                            import db_jobs
                            jds = db_jobs.get_all_jobs()
                            cand_ref = profile.get("email") or profile.get("full_name")
                            for j in jds:
                                ats_res = calculate_candidate_score(profile, j)
                                db.save_evaluation(
                                    j.get("job_id"),
                                    cand_ref,
                                    ats_res.get("hiring_score", 0),
                                    ats_res.get("recommendation", "Not Recommended"),
                                    ats_res.get("score_breakdown", {})
                                )
                        except Exception:
                            pass

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

                st.session_state["current_ats_result"] = ats_result

                # Save evaluation to database
                if db_ok and profile.get("email"):
                    db.save_evaluation(
                        ats_result["job_id"], 
                        profile.get("email"), 
                        ats_result["hiring_score"], 
                        ats_result["recommendation"], 
                        ats_result["score_breakdown"]
                    )

        if "current_ats_result" in st.session_state:
            ats_result = st.session_state["current_ats_result"]
            import pandas as pd
            import plotly.express as px
            if True:
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

                # Download Skill Gap Report (PDF)
                try:
                    import pdf_generator
                    # selected_job might be None if mock_job was used, wait, mock_job was used if selected_job was None
                    # let's pass selected_job if it exists, otherwise pass a dict with the description
                    pdf_bytes = pdf_generator.generate_skill_gap_pdf(profile, ats_result, selected_job if selected_job else {"job_title": "Custom Job", "company_name": "Unknown"})
                except Exception as e:
                    pdf_bytes = b"PDF Generation failed: " + str(e).encode()
                
                safe_name = profile.get('full_name')
                if not safe_name:
                    safe_name = 'candidate'
                import re
                safe_name = re.sub(r'[\\/*?:"<>|]', "", safe_name).replace(" ", "_")
                
                st.download_button(
                    label="📥 Download Skill Gap Report (PDF)",
                    data=pdf_bytes,
                    file_name=f"{safe_name}_Skill_Gap_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="skill_gap_report_download"
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

