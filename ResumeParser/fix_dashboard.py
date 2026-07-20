import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

dashboard_start = content.find('    # Mock additional stats required by user')
dashboard_end = content.find('    st.stop()\n\n\nelif active_page == "Candidate Details":')

new_dashboard = '''    import database as db_stats
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
            st.markdown(f\'\'\'<div class="metric-box" style="padding: 1rem 0.5rem;"><div class="metric-value" style="font-size: 1.4rem;">{val}</div><div class="metric-label" style="font-size: 0.7rem;">{label}</div></div>\'\'\', unsafe_allow_html=True)

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
        st.markdown(\'<div class="custom-card">\', unsafe_allow_html=True)
        st.markdown(\'<p class="card-title">📈 Hiring Score Trend</p>\', unsafe_allow_html=True)
        
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
        st.plotly_chart(fig1, use_container_width=True, config={\'displayModeBar\': False})
        st.markdown("</div>", unsafe_allow_html=True)
        
    with c2:
        st.markdown(\'<div class="custom-card">\', unsafe_allow_html=True)
        st.markdown(\'<p class="card-title">🎯 Recommendation Status</p>\', unsafe_allow_html=True)
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
        fig2.update_traces(textposition=\'inside\', textinfo=\'percent+label\')
        st.plotly_chart(fig2, use_container_width=True, config={\'displayModeBar\': False})
        st.markdown("</div>", unsafe_allow_html=True)

    c3, c4 = st.columns([2, 1])
    with c3:
        st.markdown(\'<div class="custom-card">\', unsafe_allow_html=True)
        st.markdown(\'<p class="card-title">👥 Recent Candidates</p>\', unsafe_allow_html=True)
        recent_candidates = load_candidates("")[:6]
        if recent_candidates:
            df_recent = pd.DataFrame([{
                "Candidate Name": c.get("full_name", "Unknown"),
                "Email": c.get("email", ""),
                "Parsed Date": format_datetime(c.get("updated_at") or c.get("created_at")),
                "Status": \'<span class="badge-rec">Saved</span>\'
            } for c in recent_candidates])
            render_html_table(df_recent)
        else:
            st.markdown(\'<div class="empty-state"><div class="empty-state-icon">👥</div><div class="empty-state-text">No Candidates Found</div></div>\', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with c4:
        st.markdown(\'<div class="custom-card">\', unsafe_allow_html=True)
        st.markdown(\'<p class="card-title">🏆 Top Ranked Candidates</p>\', unsafe_allow_html=True)
        if evals:
            top_evals = sorted(evals, key=lambda x: x.get("hiring_score", 0), reverse=True)[:5]
            for idx, e in enumerate(top_evals):
                cand = db_stats.get_candidate_by_id(e.get("candidate_id", ""))
                name = cand.get("full_name", "Unknown") if cand else "Unknown"
                initial = name[0].upper() if name else "U"
                score = e.get("hiring_score", 0)
                st.markdown(f\'\'\'
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
                    <div style="display: flex; align-items: center;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background-color: var(--primary); display: flex; align-items: center; justify-content: center; margin-right: 0.8rem; color: white; font-weight: bold; font-size: 0.9rem;">
                            {initial}
                        </div>
                        <div style="font-size: 0.9rem; font-weight: 600; color: var(--text);">{html.escape(name)}</div>
                    </div>
                    <div style="font-weight: 700; color: var(--primary);">{score}%</div>
                </div>
                \'\'\', unsafe_allow_html=True)
        else:
            st.markdown(\'<div class="empty-state"><div class="empty-state-icon">🏆</div><div class="empty-state-text">No Rankings Yet</div></div>\', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
'''

if dashboard_start != -1 and dashboard_end != -1:
    new_file = content[:dashboard_start] + new_dashboard + content[dashboard_end:]
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_file)
    print("Dashboard replaced successfully.")
else:
    print("Could not find start/end anchors.", dashboard_start, dashboard_end)
