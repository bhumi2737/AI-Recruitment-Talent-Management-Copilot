"""
AI Recruitment & Talent Management Copilot
Milestone 1: Resume Parser and Candidate Profiling
Streamlit dashboard application.
"""

import time

import streamlit as st

import database as db
from parser import calculate_extraction_accuracy, parse_resume

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
        /* Global background */
        .stApp {
            background-color: #f0f2f6;
        }

        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
        }

        [data-testid="stSidebar"] .stMarkdown h1 {
            font-size: 1.25rem;
            color: #1e40af;
            font-weight: 700;
        }

        /* Main heading */
        .main-heading {
            font-size: 2rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 0.25rem;
        }

        .main-subtitle {
            font-size: 1rem;
            color: #64748b;
            margin-bottom: 1.5rem;
        }

        /* White card containers */
        .custom-card {
            background: #ffffff;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
            border: 1px solid #e2e8f0;
            margin-bottom: 1rem;
        }

        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 1rem;
        }

        /* Skill badges */
        .skill-badge {
            display: inline-block;
            background-color: #dbeafe;
            color: #1e40af;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 500;
            margin: 0.2rem 0.25rem 0.2rem 0;
        }

        /* Profile field labels */
        .field-label {
            font-size: 0.75rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.15rem;
        }

        .field-value {
            font-size: 0.95rem;
            color: #1e293b;
            margin-bottom: 0.75rem;
        }

        /* Metric boxes in progress card */
        .metric-box {
            background: #f8fafc;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            text-align: center;
            border: 1px solid #e2e8f0;
        }

        .metric-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #1e40af;
        }

        .metric-label {
            font-size: 0.75rem;
            color: #64748b;
            margin-top: 0.15rem;
        }

        /* Sidebar nav items */
        .nav-item {
            padding: 0.5rem 0.75rem;
            border-radius: 8px;
            margin-bottom: 0.25rem;
            color: #475569;
            font-size: 0.9rem;
        }

        .nav-item-active {
            background-color: #eff6ff;
            color: #1e40af;
            font-weight: 600;
        }

        /* Status badges */
        .status-connected {
            color: #16a34a;
            font-size: 0.85rem;
        }

        .status-disconnected {
            color: #dc2626;
            font-size: 0.85rem;
        }

        /* Hide default Streamlit upload label spacing */
        [data-testid="stFileUploader"] {
            border: 2px dashed #cbd5e1;
            border-radius: 8px;
            padding: 0.5rem;
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
    st.session_state.last_accuracy = 0.0
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None

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

    # Database connection status
    db_ok, db_msg = db.test_connection()
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

# ── Upload card ───────────────────────────────────────────────────────────────
with col_upload:
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">📤 Upload Resume</p>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose a resume file",
        type=["pdf", "docx"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        st.session_state.uploaded_filename = uploaded_file.name
        st.success(f"📄 **{uploaded_file.name}**")
    else:
        st.info("Supported formats: **PDF**, **DOCX**")

    st.markdown("</div>", unsafe_allow_html=True)

# ── Parsing progress card ─────────────────────────────────────────────────────
with col_progress:
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">⚡ Parsing Progress</p>', unsafe_allow_html=True)

    accuracy = st.session_state.last_accuracy

    progress_value = min(st.session_state.processed_count / max(st.session_state.processed_count, 1), 1.0)
    if st.session_state.processed_count == 0:
        progress_value = 0.0

    st.progress(progress_value, text=f"Processing status: {int(progress_value * 100)}%")

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{st.session_state.processed_count}</div>'
            f'<div class="metric-label">Resumes Processed</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{accuracy}%</div>'
            f'<div class="metric-label">Extraction Accuracy</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{st.session_state.profiles_created}</div>'
            f'<div class="metric-label">Profiles Created</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

# ── Process uploaded file ─────────────────────────────────────────────────────
if uploaded_file is not None:
    if st.button("🚀 Parse Resume", type="primary", use_container_width=True):
        with st.spinner("Parsing resume…"):
            progress_bar = st.progress(0)
            for step in range(1, 6):
                time.sleep(0.15)
                progress_bar.progress(step * 20)

            try:
                file_bytes = uploaded_file.read()
                profile = parse_resume(file_bytes, uploaded_file.name)
                accuracy = calculate_extraction_accuracy(profile)

                st.session_state.last_profile = profile
                st.session_state.last_accuracy = accuracy
                st.session_state.processed_count += 1

                # Save to database if connected
                if db_ok:
                    success, msg, _ = db.save_candidate(profile)
                    if success:
                        st.session_state.profiles_created += 1
                        st.success(msg)
                    else:
                        st.warning(msg)
                else:
                    st.warning("Database offline — profile parsed but not saved.")

                progress_bar.progress(100)

            except Exception as exc:
                st.error(f"Parsing failed: {exc}")

# ── Extracted profile card ────────────────────────────────────────────────────
if st.session_state.last_profile:
    profile = st.session_state.last_profile

    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">👤 Extracted Candidate Profile</p>', unsafe_allow_html=True)

    info_col1, info_col2, info_col3 = st.columns(3)
    with info_col1:
        st.markdown(
            f'<p class="field-label">Full Name</p><p class="field-value">{profile["full_name"]}</p>',
            unsafe_allow_html=True,
        )
    with info_col2:
        st.markdown(
            f'<p class="field-label">Email</p><p class="field-value">{profile["email"] or "—"}</p>',
            unsafe_allow_html=True,
        )
    with info_col3:
        st.markdown(
            f'<p class="field-label">Phone</p><p class="field-value">{profile["phone"] or "—"}</p>',
            unsafe_allow_html=True,
        )

    # Skills as blue badges
    st.markdown('<p class="field-label">Skills</p>', unsafe_allow_html=True)
    if profile["skills"]:
        badges_html = "".join(
            f'<span class="skill-badge">{skill}</span>' for skill in profile["skills"]
        )
        st.markdown(badges_html, unsafe_allow_html=True)
    else:
        st.markdown('<p class="field-value">No skills detected</p>', unsafe_allow_html=True)

    st.markdown("---")

    detail_col1, detail_col2 = st.columns(2)
    with detail_col1:
        st.markdown("**🎓 Education**")
        st.text(profile["education"] or "Not found")
        st.markdown("**🏆 Certifications**")
        st.text(profile["certifications"] or "Not found")
    with detail_col2:
        st.markdown("**💼 Work Experience**")
        st.text(profile["experience"] or "Not found")
        st.markdown("**🛠 Projects**")
        st.text(profile["projects"] or "Not found")

    st.markdown("</div>", unsafe_allow_html=True)

# ── Recently processed candidates table ───────────────────────────────────────
st.markdown('<div class="custom-card">', unsafe_allow_html=True)
st.markdown('<p class="card-title">🕐 Recently Processed Candidates</p>', unsafe_allow_html=True)

if db_ok:
    candidates, err = db.get_recent_candidates(limit=10)
    if err:
        st.warning(f"Could not load candidates: {err}")
    elif candidates:
        table_data = [
            {
                "ID": c["id"],
                "Name": c["full_name"],
                "Email": c["email"] or "—",
                "Phone": c["phone"] or "—",
                "Skills": c["skills"] or "—",
                "Added": c["created_at"].strftime("%Y-%m-%d %H:%M") if c["created_at"] else "—",
            }
            for c in candidates
        ]
        st.dataframe(table_data, use_container_width=True, hide_index=True)
    else:
        st.info("No candidates in the database yet. Upload a resume to get started!")
else:
    if st.session_state.last_profile:
        p = st.session_state.last_profile
        st.dataframe(
            [{
                "Name": p["full_name"],
                "Email": p.get("email", "—"),
                "Phone": p.get("phone", "—"),
                "Skills": ", ".join(p.get("skills", [])),
                "Status": "Parsed (not saved — DB offline)",
            }],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Database is offline. Upload and parse a resume to preview results here.")

st.markdown("</div>", unsafe_allow_html=True)
