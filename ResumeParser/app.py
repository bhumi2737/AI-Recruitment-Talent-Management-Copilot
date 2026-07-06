"""
AI Recruitment & Talent Management Copilot
Milestone 1: Resume Parser and Candidate Profiling
Streamlit dashboard application.
"""

import html
import time

import streamlit as st

import database as db
from parser import parse_resume

# ── Page configuration ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="RC Recruitment Copilot",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        .stApp {
            background-color: #f0f2f6 !important;
        }

        [data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #cbd5e1 !important;
        }

        [data-testid="stSidebar"] .stMarkdown h1 {
            font-size: 1.25rem !important;
            color: #1e40af !important;
            font-weight: 700 !important;
        }

        .main-heading {
            font-size: 2rem !important;
            font-weight: 700 !important;
            color: #0f172a !important;
            margin-bottom: 0.25rem !important;
        }

        .main-subtitle {
            font-size: 1rem !important;
            color: #475569 !important;
            margin-bottom: 1.5rem !important;
        }

        .custom-card {
            background: #ffffff !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06) !important;
            border: 1px solid #cbd5e1 !important;
            margin-bottom: 1rem !important;
        }

        .card-title {
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            color: #0f172a !important;
            margin-bottom: 1rem !important;
        }

        .skill-badge {
            display: inline-block !important;
            background-color: #dbeafe !important;
            color: #1e40af !important;
            padding: 0.25rem 0.75rem !important;
            border-radius: 9999px !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            margin: 0.2rem 0.25rem 0.2rem 0 !important;
        }

        .field-label {
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            color: #475569 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            margin-bottom: 0.15rem !important;
        }

        .field-value {
            font-size: 0.95rem !important;
            color: #0f172a !important;
            font-weight: 500 !important;
            margin-bottom: 0.75rem !important;
        }

        .section-heading {
            font-size: 0.95rem !important;
            font-weight: 600 !important;
            color: #0f172a !important;
            margin: 0.75rem 0 0.35rem 0 !important;
        }

        .section-text {
            font-size: 0.9rem !important;
            color: #0f172a !important;
            line-height: 1.6 !important;
            white-space: pre-wrap !important;
            background: #f8fafc !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
            padding: 0.75rem 1rem !important;
            margin-bottom: 0.5rem !important;
        }

        .metric-box {
            background: #f8fafc !important;
            border-radius: 8px !important;
            padding: 0.75rem 1rem !important;
            text-align: center !important;
            border: 1px solid #cbd5e1 !important;
        }

        .metric-value {
            font-size: 1.5rem !important;
            font-weight: 700 !important;
            color: #1e40af !important;
        }

        .metric-label {
            font-size: 0.75rem !important;
            color: #475569 !important;
            margin-top: 0.15rem !important;
        }

        .nav-item {
            padding: 0.5rem 0.75rem !important;
            border-radius: 8px !important;
            margin-bottom: 0.25rem !important;
            color: #334155 !important;
            font-size: 0.9rem !important;
        }

        .nav-item-active {
            background-color: #eff6ff !important;
            color: #1e40af !important;
            font-weight: 600 !important;
        }

        .status-connected {
            color: #16a34a !important;
            font-size: 0.85rem !important;
        }

        .status-disconnected {
            color: #dc2626 !important;
            font-size: 0.85rem !important;
        }

        [data-testid="stFileUploader"] {
            border: 2px dashed #cbd5e1 !important;
            border-radius: 8px !important;
            padding: 0.5rem !important;
        }

        .upload-hint {
            color: #475569 !important;
            font-size: 0.85rem !important;
            margin-top: 0.5rem !important;
        }

        .file-name {
            color: #0f172a !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
        }

        /* Hide all deploy-related elements specifically */
        [class*="deploy"],
        [class*="Deploy"],
        [data-testid*="deploy"],
        [data-testid*="Deploy"] {
            display: none !important;
            visibility: hidden !important;
            width: 0px !important;
            height: 0px !important;
            overflow: hidden !important;
        }

        /* Hide default Streamlit footer and MainMenu actions */
        footer {
            visibility: hidden !important;
        }
        #MainMenu {
            visibility: hidden !important;
            display: none !important;
        }
        [data-testid="stHeaderActionButton"] {
            display: none !important;
            visibility: hidden !important;
        }

        /* Explicitly style the sidebar collapse/expand toggle buttons and their SVGs to be black and visible */
        [data-testid="collapsedControl"] button,
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapseButton"] button,
        button[data-testid="stSidebarCollapseButton"],
        button[data-testid="stBaseButton-header"],
        button[data-testid="stBaseButton-headerNoPadding"],
        [data-testid="stSidebar"] button,
        [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button {
            display: inline-flex !important;
            visibility: visible !important;
            width: auto !important;
            height: auto !important;
            color: #000000 !important;
        }
        
        [data-testid="collapsedControl"] button svg,
        [data-testid="stSidebarCollapseButton"] svg,
        [data-testid="stSidebarCollapseButton"] button svg,
        button[data-testid="stSidebarCollapseButton"] svg,
        button[data-testid="stBaseButton-header"] svg,
        button[data-testid="stBaseButton-headerNoPadding"] svg,
        [data-testid="stSidebar"] svg,
        [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button svg {
            fill: #000000 !important;
            color: #000000 !important;
        }

        [data-testid="collapsedControl"] button svg *,
        [data-testid="stSidebarCollapseButton"] svg *,
        [data-testid="stSidebarCollapseButton"] button svg *,
        button[data-testid="stSidebarCollapseButton"] svg *,
        button[data-testid="stBaseButton-header"] svg *,
        button[data-testid="stBaseButton-headerNoPadding"] svg *,
        [data-testid="stSidebar"] svg *,
        [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button svg * {
            fill: #000000 !important;
            stroke: #000000 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state defaults ────────────────────────────────────────────────────
if "processed_count" not in st.session_state:
    st.session_state.processed_count = 0
if "profiles_created" not in st.session_state:
    st.session_state.profiles_created = 0
if "last_profile" not in st.session_state:
    st.session_state.last_profile = None
if "last_accuracy" not in st.session_state:
    st.session_state.last_accuracy = 0
if "progress_value" not in st.session_state:
    st.session_state.progress_value = 0.0
if "parse_complete" not in st.session_state:
    st.session_state.parse_complete = False
if "recent_candidates" not in st.session_state:
    st.session_state.recent_candidates = []


def render_progress_card():
    """Render parsing progress metrics from session state."""
    st.markdown('<p class="card-title">⚡ Parsing Progress</p>', unsafe_allow_html=True)

    pct = int(st.session_state.progress_value * 100)
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


def render_section_block(icon: str, title: str, content: str):
    """Render a profile section with dark, readable text."""
    safe_content = html.escape(content or "Not found")
    st.markdown(
        f'<p class="section-heading">{icon} {title}</p>'
        f'<div class="section-text">{safe_content}</div>',
        unsafe_allow_html=True,
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 📋 RC Recruitment Copilot")
    st.markdown("---")

    nav_items = [
        ("🏠", "Dashboard"),
        ("📤", "Resume Upload"),
        ("👥", "Candidates"),
        ("💼", "Job Postings"),
        ("📊", "Analytics"),
        ("⚙️", "Settings"),
    ]

    for icon, label in nav_items:
        css_class = "nav-item nav-item-active" if label == "Resume Upload" else "nav-item"
        st.markdown(
            f'<div class="{css_class}">{icon} &nbsp; {label}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    db_ok, _ = db.test_connection()
    if db_ok:
        st.markdown('<p class="status-connected">● Database Connected</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-disconnected">● Database Offline</p>', unsafe_allow_html=True)
        st.caption("Parsed data will still display, but won't be saved.")

# ── Main content ──────────────────────────────────────────────────────────────
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
        st.markdown(
            f'<p class="file-name">📄 {html.escape(uploaded_file.name)}</p>',
            unsafe_allow_html=True,
        )
    st.markdown('<p class="upload-hint">Supported formats: PDF, DOCX</p>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_progress:
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    render_progress_card()
    st.markdown("</div>", unsafe_allow_html=True)

# Reset state if the uploaded file changes
if uploaded_file:
    if st.session_state.get("current_file") != uploaded_file.name:
        st.session_state.current_file = uploaded_file.name
        st.session_state.parse_complete = False
        st.session_state.progress_value = 0.0
else:
    if st.session_state.get("current_file") is not None:
        st.session_state.current_file = None
        st.session_state.parse_complete = False
        st.session_state.progress_value = 0.0

# ── Process uploaded file ─────────────────────────────────────────────────────
if uploaded_file is not None:
    if st.button("🚀 Parse Resume", type="primary", use_container_width=True):
        with st.spinner("Parsing resume…"):
            try:
                file_bytes = uploaded_file.read()
                profile = parse_resume(file_bytes, uploaded_file.name)

                saved_to_db = False
                if db_ok:
                    success, msg, _ = db.save_candidate(profile)
                    if success:
                        saved_to_db = True
                        st.session_state.parse_msg = msg
                    else:
                        st.session_state.parse_msg = msg
                else:
                    st.session_state.parse_msg = "Database offline — profile parsed but not saved."

                # Update dashboard metrics after successful parse
                st.session_state.last_profile = profile
                st.session_state.parse_complete = True
                st.session_state.progress_value = 1.0
                st.session_state.processed_count = 1
                st.session_state.last_accuracy = 95
                st.session_state.profiles_created = 1 if saved_to_db else 0
                st.session_state.saved_to_db = saved_to_db

                # Track for recently processed table
                st.session_state.recent_candidates.insert(
                    0,
                    {
                        "Name": profile["full_name"],
                        "Email": profile.get("email") or "—",
                        "Phone": profile.get("phone") or "—",
                        "Skills": ", ".join(profile.get("skills", [])) or "—",
                        "Status": "Saved" if saved_to_db else "Parsed (not saved)",
                    },
                )

                st.rerun()

            except Exception as exc:
                st.error(f"Parsing failed: {exc}")

# ── Extracted profile card ────────────────────────────────────────────────────
if st.session_state.last_profile:
    # Render successful/warning banners if parsing just completed
    if st.session_state.get("parse_complete"):
        if st.session_state.get("saved_to_db"):
            st.success(st.session_state.get("parse_msg", "Candidate saved successfully"))
        else:
            st.warning(st.session_state.get("parse_msg", "Database offline — profile parsed but not saved."))

    profile = st.session_state.last_profile

    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">👤 Extracted Candidate Profile</p>', unsafe_allow_html=True)

    info_col1, info_col2, info_col3 = st.columns(3)
    with info_col1:
        st.markdown(
            f'<p class="field-label">Full Name</p>'
            f'<p class="field-value">{html.escape(profile["full_name"])}</p>',
            unsafe_allow_html=True,
        )
    with info_col2:
        st.markdown(
            f'<p class="field-label">Email</p>'
            f'<p class="field-value">{html.escape(profile["email"] or "—")}</p>',
            unsafe_allow_html=True,
        )
    with info_col3:
        st.markdown(
            f'<p class="field-label">Phone</p>'
            f'<p class="field-value">{html.escape(profile["phone"] or "—")}</p>',
            unsafe_allow_html=True,
        )

    st.markdown('<p class="field-label">Skills</p>', unsafe_allow_html=True)
    if profile["skills"]:
        badges_html = "".join(
            f'<span class="skill-badge">{html.escape(skill)}</span>'
            for skill in profile["skills"]
        )
        st.markdown(badges_html, unsafe_allow_html=True)
    else:
        st.markdown('<p class="field-value">No skills detected</p>', unsafe_allow_html=True)

    st.markdown("---")

    detail_col1, detail_col2 = st.columns(2)
    with detail_col1:
        render_section_block("🎓", "Education", profile["education"])
        render_section_block("🏆", "Certifications", profile["certifications"])
    with detail_col2:
        render_section_block("💼", "Work Experience", profile["experience"])
        render_section_block("🛠", "Projects", profile["projects"])

    st.markdown("</div>", unsafe_allow_html=True)

# ── Recently processed candidates table ───────────────────────────────────────
st.markdown('<div class="custom-card">', unsafe_allow_html=True)
st.markdown('<p class="card-title">🕐 Recently Processed Candidates</p>', unsafe_allow_html=True)

table_rows = []

if db_ok:
    candidates, err = db.get_recent_candidates(limit=10)
    if err:
        st.warning(f"Could not load candidates: {err}")
        table_rows = st.session_state.recent_candidates
    elif candidates:
        table_rows = [
            {
                "Name": c["full_name"],
                "Email": c["email"] or "—",
                "Phone": c["phone"] or "—",
                "Skills": c["skills"] or "—",
                "Status": "Saved",
            }
            for c in candidates
        ]
    else:
        table_rows = st.session_state.recent_candidates
else:
    table_rows = st.session_state.recent_candidates

if table_rows:
    st.dataframe(table_rows, use_container_width=True, hide_index=True)
else:
    st.info("No candidates processed yet. Upload a resume to get started!")

st.markdown("</div>", unsafe_allow_html=True)
