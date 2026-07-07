"""
AI Recruitment & Talent Management Copilot
Milestone 1: Resume Parser and Candidate Profiling
Streamlit dashboard application.
"""

import html
import time

import streamlit as st

import database as db
from parser import parse_resume, calculate_extraction_accuracy

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

        /* Style Streamlit buttons inside sidebar as flat list navigation items */
        [data-testid="stSidebar"] button[data-testid^="stBaseButton-"] {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #334155 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            padding: 0.5rem 0.75rem !important;
            border-radius: 8px !important;
            margin-bottom: 0.25rem !important;
            display: flex !important;
            width: 100% !important;
            font-size: 0.9rem !important;
            font-weight: 500 !important;
        }

        [data-testid="stSidebar"] button[data-testid^="stBaseButton-"]:hover {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
        }

        [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
            background-color: #eff6ff !important;
            color: #1e40af !important;
            font-weight: 600 !important;
        }
        
        [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {
            background-color: #eff6ff !important;
            color: #1e40af !important;
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
if "already_exists" not in st.session_state:
    st.session_state.already_exists = False
if "recent_candidates" not in st.session_state:
    st.session_state.recent_candidates = []
if "active_page" not in st.session_state:
    st.session_state.active_page = "Resume Upload"
if "selected_candidate_id" not in st.session_state:
    st.session_state.selected_candidate_id = None
if "search_filter" not in st.session_state:
    st.session_state.search_filter = ""


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
        is_active = (st.session_state.active_page == label)
        if st.button(
            f"{icon}  {label}",
            key=f"nav_btn_{label}",
            use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            st.session_state.active_page = label
            if label == "Candidates":
                st.session_state.selected_candidate_id = None
            st.rerun()

    st.markdown("---")

    db_ok, _ = db.test_connection()
    if db_ok:
        st.markdown('<p class="status-connected">● Database Connected</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-disconnected">● Database Offline</p>', unsafe_allow_html=True)
        st.caption("Parsed data will still display, but won't be saved.")

# ── Main content routing ──────────────────────────────────────────────────────
active_page = st.session_state.active_page

if active_page == "Dashboard":
    st.markdown('<p class="main-heading">Recruitment Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">AI Resume Parsing & Talent Pipeline Overview</p>', unsafe_allow_html=True)
    
    # metrics
    total_candidates = db.get_candidate_count()
    all_candidates = db.get_all_candidates()
    
    skills_count = {}
    for c in all_candidates:
        c_skills = [s.strip() for s in c["skills"].split(",") if s.strip()]
        for s in c_skills:
            skills_count[s] = skills_count.get(s, 0) + 1
            
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{total_candidates}</div>'
            f'<div class="metric-label">Total Candidates</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        completeness_list = []
        for c in all_candidates:
            fields = ["full_name", "email", "phone", "education", "experience", "skills"]
            filled = sum(1 for field in fields if c.get(field))
            completeness_list.append((filled / len(fields)) * 100)
        avg_completeness = round(sum(completeness_list) / len(completeness_list), 1) if completeness_list else 0
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{avg_completeness}%</div>'
            f'<div class="metric-label">Average Profile Completeness</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{len(skills_count)}</div>'
            f'<div class="metric-label">Unique Skills Extracted</div></div>',
            unsafe_allow_html=True,
        )
        
    st.markdown("---")
    
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📊 Top Pipeline Skills</p>', unsafe_allow_html=True)
        if skills_count:
            import pandas as pd
            sorted_skills = sorted(skills_count.items(), key=lambda x: x[1], reverse=True)[:8]
            df_skills = pd.DataFrame(sorted_skills, columns=["Skill", "Count"])
            st.bar_chart(df_skills.set_index("Skill"), color="#1e40af")
        else:
            st.info("No candidates inside database. Parse resumes to populate the dashboard metrics!")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_right:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">🕐 Recent Activity</p>', unsafe_allow_html=True)
        if all_candidates:
            for idx, c in enumerate(all_candidates[:5]):
                st.markdown(
                    f"**{c['full_name']}** was parsed & registered.<br>"
                    f"<span style='font-size:0.8rem; color:#64748b;'>{c.get('email', 'No email')}</span>",
                    unsafe_allow_html=True
                )
                created_str = c.get('created_at').strftime('%Y-%m-%d %H:%M') if c.get('created_at') else 'Unknown'
                st.caption(f"Added: {created_str}")
                if idx < len(all_candidates[:5]) - 1:
                    st.markdown("---")
        else:
            st.info("No activity yet.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.stop()

elif active_page == "Candidates":
    st.markdown('<p class="main-heading">Candidates Directory</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Search and manage parsed candidate profiles</p>', unsafe_allow_html=True)
    
    if st.session_state.get("selected_candidate_id"):
        candidate_id = st.session_state.selected_candidate_id
        all_c = db.get_all_candidates()
        candidate = next((c for c in all_c if c["id"] == candidate_id), None)
        
        if candidate:
            if st.button("⬅️ Back to Candidates List", type="secondary"):
                st.session_state.selected_candidate_id = None
                st.rerun()
                
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.markdown(f'<p class="card-title">👤 Candidate Profile: {html.escape(candidate["full_name"])}</p>', unsafe_allow_html=True)
            
            c_col1, c_col2, c_col3 = st.columns(3)
            with c_col1:
                st.markdown(f'<p class="field-label">Full Name</p><p class="field-value">{html.escape(candidate["full_name"])}</p>', unsafe_allow_html=True)
            with c_col2:
                st.markdown(f'<p class="field-label">Email</p><p class="field-value">{html.escape(candidate["email"] or "—")}</p>', unsafe_allow_html=True)
            with c_col3:
                st.markdown(f'<p class="field-label">Phone</p><p class="field-value">{html.escape(candidate["phone"] or "—")}</p>', unsafe_allow_html=True)
                
            st.markdown('<p class="field-label">Skills</p>', unsafe_allow_html=True)
            if candidate["skills"]:
                badges = "".join(f'<span class="skill-badge">{html.escape(s.strip())}</span>' for s in candidate["skills"].split(","))
                st.markdown(badges, unsafe_allow_html=True)
            else:
                st.markdown('<p class="field-value">No skills detected</p>', unsafe_allow_html=True)
                
            st.markdown("---")
            
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                render_section_block("🎓", "Education", candidate["education"])
                render_section_block("🏆", "Certifications", candidate["certifications"])
            with d_col2:
                render_section_block("💼", "Work Experience", candidate["experience"])
                render_section_block("🛠", "Projects", candidate["projects"])
                
            st.markdown("---")
            with st.expander("📄 View Raw Resume Text"):
                st.text_area("Raw Text Content", candidate["raw_text"], height=300, disabled=True)
                
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.error("Candidate not found.")
            if st.button("⬅️ Back to Candidates List", type="primary"):
                st.session_state.selected_candidate_id = None
                st.rerun()
    else:
        default_search = st.session_state.get("search_filter", "")
        search_query = st.text_input("🔍 Search Candidates", value=default_search, placeholder="Type name, email, skills, education, or work history...")
        st.session_state.search_filter = ""
        
        candidates = db.get_all_candidates(search_query)
        
        if candidates:
            st.markdown(f"Showing **{len(candidates)}** candidates matching your search.")
            for c in candidates:
                with st.container():
                    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                    col_c1, col_c2 = st.columns([4, 1])
                    with col_c1:
                        st.markdown(f"### {html.escape(c['full_name'])}")
                        st.markdown(f"📧 **Email:** {html.escape(c['email'] or '—')} &nbsp;&nbsp;&nbsp;&nbsp; 📞 **Phone:** {html.escape(c['phone'] or '—')}")
                        c_skills = [s.strip() for s in c["skills"].split(",") if s.strip()]
                        skills_badges = "".join(f'<span class="skill-badge">{html.escape(s)}</span>' for s in c_skills[:6])
                        if len(c_skills) > 6:
                            skills_badges += f'<span class="skill-badge">+{len(c_skills)-6} more</span>'
                        st.markdown(skills_badges, unsafe_allow_html=True)
                    with col_c2:
                        st.write("")
                        st.write("")
                        if st.button("👁️ View Profile", key=f"view_c_{c['id']}", use_container_width=True):
                            st.session_state.selected_candidate_id = c["id"]
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No candidates found matching the search criteria.")
            
    st.stop()

elif active_page == "Job Postings":
    st.markdown('<p class="main-heading">Job Postings</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Manage open vacancies and match candidate profiles</p>', unsafe_allow_html=True)
    
    jobs = [
        {
            "title": "Senior Python Backend Engineer",
            "department": "Engineering",
            "skills": ["Python", "Fastapi", "Docker", "Postgresql", "Rest Api"],
            "experience": "5+ Years",
        },
        {
            "title": "Data Scientist / ML Practitioner",
            "department": "AI & Insights",
            "skills": ["Python", "Tensorflow", "Pytorch", "Machine Learning", "Scikit-Learn"],
            "experience": "3+ Years",
        },
        {
            "title": "Fullstack Software Engineer (React/Node)",
            "department": "Engineering",
            "skills": ["React", "Javascript", "Typescript", "Node.js", "Html", "Css"],
            "experience": "2+ Years",
        }
    ]
    
    for idx, job in enumerate(jobs):
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        col_j1, col_j2 = st.columns([3, 1])
        with col_j1:
            st.markdown(f"### {job['title']}")
            st.markdown(f"**Department:** {job['department']} &nbsp;&nbsp;&nbsp;&nbsp; **Experience Required:** {job['experience']}")
            badges = "".join(f'<span class="skill-badge">{s}</span>' for s in job["skills"])
            st.markdown(badges, unsafe_allow_html=True)
        with col_j2:
            st.write("")
            st.write("")
            if st.button("🔍 Match Candidates", key=f"match_j_{idx}", use_container_width=True):
                st.session_state.active_page = "Candidates"
                st.session_state.selected_candidate_id = None
                st.session_state.search_filter = job["skills"][0]
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.stop()

elif active_page == "Analytics":
    st.markdown('<p class="main-heading">Pipeline Analytics</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Talent intake metrics and funnel analysis</p>', unsafe_allow_html=True)
    
    import pandas as pd
    import numpy as np
    
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📈 Talent Intake Trend (Last 7 Days)</p>', unsafe_allow_html=True)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=7)
        data = pd.DataFrame(np.random.randint(2, 10, size=(7, 1)), index=dates, columns=["Candidates Registered"])
        st.line_chart(data, color="#1e40af")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_a2:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">🎯 Extraction completeness funnel</p>', unsafe_allow_html=True)
        stages = ["Uploaded Resumes", "Parsed Successfully", "Saved in MongoDB", "Matched Vacancy"]
        counts = [100, 95, 80, 45]
        df_funnel = pd.DataFrame(counts, index=stages, columns=["Count"])
        st.bar_chart(df_funnel, color="#0f172a")
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.stop()

elif active_page == "Settings":
    st.markdown('<p class="main-heading">Settings</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Configure application settings and connections</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">⚙️ Parser Settings</p>', unsafe_allow_html=True)
    st.toggle("Enable Regex Name Heuristics", value=True)
    st.toggle("Enable Automated Skills Extractor", value=True)
    st.selectbox("Resume OCR Parsing engine", ["pypdf (native metadata text extraction)", "tesseract (OCR scan mode - Disabled in M1)"])
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.stop()

# ── Main content (Resume Upload page) ───────────────────────────────────────────
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
        st.session_state.already_exists = False
else:
    if st.session_state.get("current_file") is not None:
        st.session_state.current_file = None
        st.session_state.parse_complete = False
        st.session_state.progress_value = 0.0
        st.session_state.already_exists = False

# ── Process uploaded file ─────────────────────────────────────────────────────
if uploaded_file is not None:
    if st.button("🚀 Parse Resume", type="primary", use_container_width=True):
        with st.spinner("Parsing resume…"):
            try:
                file_bytes = uploaded_file.read()
                profile = parse_resume(file_bytes, uploaded_file.name)

                saved_to_db = False
                already_exists = False
                if db_ok:
                    success, msg, _ = db.save_candidate(profile)
                    if success:
                        saved_to_db = True
                        st.session_state.parse_msg = msg
                    else:
                        st.session_state.parse_msg = msg
                        if "already exists" in msg.lower():
                            already_exists = True
                else:
                    st.session_state.parse_msg = "Database offline — profile parsed but not saved."

                # Update dashboard metrics after successful parse
                st.session_state.last_profile = profile
                st.session_state.parse_complete = True
                st.session_state.progress_value = 1.0
                st.session_state.processed_count = 1
                st.session_state.last_accuracy = int(calculate_extraction_accuracy(profile))
                st.session_state.profiles_created = 1 if saved_to_db else 0
                st.session_state.saved_to_db = saved_to_db
                st.session_state.already_exists = already_exists

                # Track status text for recently processed table
                if already_exists:
                    status_text = "Already Exists"
                elif saved_to_db:
                    status_text = "Saved"
                else:
                    status_text = "Parsed (not saved)"

                # Track for recently processed table
                st.session_state.recent_candidates.insert(
                    0,
                    {
                        "Name": profile["full_name"],
                        "Email": profile.get("email") or "—",
                        "Phone": profile.get("phone") or "—",
                        "Skills": ", ".join(profile.get("skills", [])) or "—",
                        "Status": status_text,
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
        elif st.session_state.get("already_exists"):
            st.warning(st.session_state.get("parse_msg", "Candidate already exists in the database."))
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
