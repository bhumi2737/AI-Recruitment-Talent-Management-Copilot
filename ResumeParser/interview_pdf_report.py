"""
PDF Report Generator for AI Candidate Interview Evaluation
------------------------------------------------------------
Generates a downloadable PDF report containing candidate info, job role,
per-question candidate answers, AI evaluation scores, feedback, and summary report.
"""

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_interview_pdf_report(
    candidate_data: dict[str, Any],
    job_data: dict[str, Any],
    interview_id: str,
    evaluations_list: list[dict[str, Any]],
    summary_data: dict[str, Any]
) -> bytes:
    """
    Generates a PDF document in bytes buffer for Streamlit download button.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    primary_color = colors.HexColor("#0f172a")
    secondary_color = colors.HexColor("#3b82f6")
    accent_color = colors.HexColor("#10b981")
    text_color = colors.HexColor("#334155")
    bg_light = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#e2e8f0")

    # Custom Paragraph Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=primary_color,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=15,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=secondary_color,
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=text_color,
    )

    question_style = ParagraphStyle(
        "QuestionText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=15,
        textColor=primary_color,
        spaceAfter=4,
    )

    answer_style = ParagraphStyle(
        "AnswerText",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6,
    )

    story = []

    # 1. Header Title
    story.append(Paragraph("AI Candidate Interview Evaluation Report", title_style))
    story.append(Paragraph(f"Assignment ID: <strong>{interview_id}</strong> &nbsp;|&nbsp; Talent Acquisition Copilot", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=secondary_color, spaceAfter=15))

    # 2. Candidate & Vacancy Overview Card
    cand_name = candidate_data.get("full_name", "Candidate")
    cand_email = candidate_data.get("email", "N/A")
    job_title = job_data.get("job_title", "Position")
    company = job_data.get("company_name", "Talent Corp")

    overview_data = [
        [
            Paragraph(f"<b>Candidate:</b> {cand_name}", body_style),
            Paragraph(f"<b>Target Role:</b> {job_title}", body_style),
        ],
        [
            Paragraph(f"<b>Email:</b> {cand_email}", body_style),
            Paragraph(f"<b>Company:</b> {company}", body_style),
        ],
    ]

    t_overview = Table(overview_data, colWidths=[270, 270])
    t_overview.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_light),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_overview)
    story.append(Spacer(1, 15))

    # 3. Overall Summary Metrics Card
    overall_score = summary_data.get("overall_interview_score", 0)
    tech_score = summary_data.get("avg_technical_score", 0)
    comm_score = summary_data.get("avg_communication_score", 0)
    conf_score = summary_data.get("avg_confidence_score", 0)
    final_rec = summary_data.get("final_recommendation", "Recommended")

    story.append(Paragraph("Overall Interview Performance Summary", section_heading))

    summary_table_data = [
        [
            Paragraph("<b>Overall Score</b>", body_style),
            Paragraph("<b>Technical Score</b>", body_style),
            Paragraph("<b>Communication</b>", body_style),
            Paragraph("<b>Confidence</b>", body_style),
            Paragraph("<b>Final Recommendation</b>", body_style),
        ],
        [
            Paragraph(f"<font size=14 color='#3b82f6'><b>{overall_score}%</b></font>", body_style),
            Paragraph(f"<font size=12><b>{tech_score}%</b></font>", body_style),
            Paragraph(f"<font size=12><b>{comm_score}%</b></font>", body_style),
            Paragraph(f"<font size=12><b>{conf_score}%</b></font>", body_style),
            Paragraph(f"<font size=11 color='#10b981'><b>{final_rec}</b></font>", body_style),
        ]
    ]

    t_summary = Table(summary_table_data, colWidths=[108, 108, 108, 108, 108])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), bg_light),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 12))

    # Top Strengths and Improvements
    strengths = summary_data.get("top_strengths", [])
    improvements = summary_data.get("areas_for_improvement", [])

    str_bullets = "<br/>".join([f"• {s}" for s in strengths]) if strengths else "• Satisfactory response performance."
    imp_bullets = "<br/>".join([f"• {i}" for i in improvements]) if improvements else "• Continue building practical experience."

    si_data = [
        [Paragraph("<b>Top Strengths</b>", body_style), Paragraph("<b>Areas for Improvement</b>", body_style)],
        [Paragraph(str_bullets, body_style), Paragraph(imp_bullets, body_style)]
    ]
    t_si = Table(si_data, colWidths=[270, 270])
    t_si.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), bg_light),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_si)
    story.append(Spacer(1, 18))

    # 4. Per-Question Detailed Breakdown
    story.append(Paragraph("Detailed Per-Question AI Evaluation", section_heading))
    story.append(HRFlowable(width="100%", thickness=1, color=border_color, spaceAfter=10))

    for idx, e in enumerate(evaluations_list):
        q_num = idx + 1
        q_text = e.get("question", "")
        c_ans = e.get("candidate_answer", e.get("answer", "")) or "No answer provided."
        q_tech = e.get("technical_score", 0)
        q_comm = e.get("communication_score", 0)
        q_conf = e.get("confidence_score", 0)
        q_over = e.get("overall_score", 0)
        feedback = e.get("ai_feedback", e.get("feedback", ""))

        story.append(Paragraph(f"<b>Question {q_num}:</b> {q_text}", question_style))
        story.append(Paragraph(f"<b>Candidate Answer:</b> {c_ans}", answer_style))

        q_scores_text = f"<b>Scores:</b> Overall: <b>{q_over}%</b> | Tech: {q_tech}% | Comm: {q_comm}% | Conf: {q_conf}%"
        story.append(Paragraph(q_scores_text, body_style))

        if feedback:
            story.append(Paragraph(f"<b>AI Feedback:</b> {feedback}", body_style))

        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=0.5, color=border_color, spaceAfter=10))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
