from fpdf import FPDF
from datetime import datetime

class PDF(FPDF):
    def header(self):
        pass

    def footer(self):
        pass

def sanitize(text):
    if not isinstance(text, str):
        text = str(text)
    # Replace common non-latin1 characters
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2022': '-', '\u200b': '',
        '\u2713': 'v', '\u2717': 'x', '\u25cf': '-'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Fallback for any other unicode characters
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_skill_gap_pdf(profile, ats_result, selected_job):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    def title_section(title):
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 8, sanitize("========================================="), new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.cell(0, 8, sanitize(title), new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.cell(0, 8, sanitize("========================================="), new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.ln(2)

    # Main Header
    title_section("AI Recruitment Skill Gap Report")

    # Candidate Information
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 6, sanitize("Candidate Information"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, sanitize("---------------------"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, sanitize(f"Name: {profile.get('full_name', 'Unknown')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, sanitize(f"Email: {profile.get('email', 'N/A')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Job Information
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 6, sanitize("Job Information"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, sanitize("---------------"), new_x="LMARGIN", new_y="NEXT")
    
    if selected_job:
        job_title = selected_job.get("job_title", "Custom Job")
        company = selected_job.get("company_name", "Unknown Company")
        req_exp = selected_job.get("experience_required", "Not specified")
    else:
        job_title = "Custom Text Match"
        company = "Unknown"
        req_exp = "Not specified"

    pdf.cell(0, 6, sanitize(f"Job Title: {job_title}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, sanitize(f"Company: {company}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Hiring Results
    title_section("HIRING RESULTS")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, sanitize(f"Hiring Score: {ats_result.get('hiring_score', 0)}/100"), new_x="LMARGIN", new_y="NEXT")
    skill_match = ats_result.get("score_breakdown", {}).get("skill_match", 0)
    pdf.cell(0, 6, sanitize(f"Skill Match: {skill_match}%"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, sanitize(f"Skill Gap: {max(0, 100 - skill_match)}%"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, sanitize("Recommendation:"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, sanitize(str(ats_result.get("recommendation", "N/A"))), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Skill Comparison
    title_section("SKILL COMPARISON")
    
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, sanitize("Matched Skills"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, sanitize("--------------"), new_x="LMARGIN", new_y="NEXT")
    matched = ats_result.get("matched_skills", [])
    if matched:
        for sk in matched:
            pdf.cell(0, 6, sanitize(f"v {sk}"), new_x="LMARGIN", new_y="NEXT") # v instead of checkmark
    else:
        pdf.cell(0, 6, sanitize("None"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, sanitize("Missing Skills"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, sanitize("--------------"), new_x="LMARGIN", new_y="NEXT")
    missing = ats_result.get("missing_skills", [])
    if missing:
        for sk in missing:
            pdf.cell(0, 6, sanitize(f"x {sk}"), new_x="LMARGIN", new_y="NEXT") # x instead of cross
    else:
        pdf.cell(0, 6, sanitize("None"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, sanitize("Additional Skills"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, sanitize("-----------------"), new_x="LMARGIN", new_y="NEXT")
    extra = ats_result.get("extra_skills", [])
    if extra:
        for sk in extra[:10]:
            pdf.cell(0, 6, sanitize(f"+ {sk}"), new_x="LMARGIN", new_y="NEXT")
        if len(extra) > 10:
            pdf.cell(0, 6, sanitize(f"+ ...and {len(extra)-10} more"), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 6, sanitize("None"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Experience
    title_section("EXPERIENCE ANALYSIS")
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, sanitize("Required Experience:"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, sanitize(req_exp), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, sanitize("Candidate Experience:"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    
    cand_exp = profile.get("experience")
    if cand_exp is None:
        cand_exp = "No experience found"
    else:
        cand_exp = str(cand_exp).strip()
        if not cand_exp:
            cand_exp = "No experience found"
    
    # Simple truncate to first few lines to not mess up PDF too much
    cand_exp_lines = cand_exp.split('\n')
    for line in cand_exp_lines[:5]: # Max 5 lines
        pdf.multi_cell(0, 6, sanitize(line))
    pdf.ln(5)

    # Recommendations
    title_section("RECOMMENDATIONS")
    pdf.set_font("helvetica", "", 11)
    if missing:
        pdf.cell(0, 6, sanitize("The candidate is missing the following skills:"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        for sk in missing:
            pdf.cell(0, 6, sanitize(f"- {sk}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 6, sanitize("Suggested Learning:"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 11)
        pdf.ln(2)
        recs = ats_result.get("recommendations", [])
        if recs:
            for r in recs:
                pdf.multi_cell(0, 6, sanitize(f"- {r}"))
        else:
            pdf.cell(0, 6, sanitize("General study on missing skills recommended."), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 6, sanitize("Candidate profile is well aligned with the job description."), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    title_section("REPORT GENERATED BY")
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, sanitize("AI Recruitment Talent Management Copilot"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    date_str = datetime.now().strftime("%d %B %Y")
    pdf.cell(0, 6, sanitize(f"Generated On: {date_str}"), new_x="LMARGIN", new_y="NEXT")
    
    # fpdf2 output() returns a bytearray
    return bytes(pdf.output())
