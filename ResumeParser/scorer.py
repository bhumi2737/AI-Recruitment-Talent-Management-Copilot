import re


SKILL_ALIASES = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "reactjs": "React",
    "react.js": "React",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
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
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "express": "Express",
    "rest api": "REST API",
    "api": "REST API",
    "dsa": "DSA",
    "oop": "OOP",
    "streamlit": "Streamlit",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "nlp": "NLP",
}


SKILL_KEYWORDS = list(SKILL_ALIASES.keys())


def normalize_skill(skill):
    if not skill:
        return ""

    skill = str(skill).strip().lower()
    return SKILL_ALIASES.get(skill, skill.title())


def extract_skills_from_text(text):
    if not text:
        return []

    text = text.lower()
    found_skills = set()

    for skill in SKILL_KEYWORDS:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text):
            found_skills.add(normalize_skill(skill))

    return sorted(found_skills)


def normalize_candidate_skills(skills):
    if not skills:
        return []

    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    return sorted(set(normalize_skill(skill) for skill in skills if skill))


def calculate_profile_completeness(profile):
    fields = [
        "full_name",
        "email",
        "phone",
        "skills",
        "education",
        "experience",
        "projects",
        "certifications",
    ]

    filled = 0

    for field in fields:
        value = profile.get(field)

        if isinstance(value, list) and len(value) > 0:
            filled += 1
        elif isinstance(value, str) and value.strip():
            filled += 1

    return round((filled / len(fields)) * 100)


def calculate_ats_score(profile, job_description):
    candidate_skills = normalize_candidate_skills(profile.get("skills", []))
    required_skills = extract_skills_from_text(job_description)

    candidate_set = set(candidate_skills)
    required_set = set(required_skills)

    matched_skills = sorted(candidate_set.intersection(required_set))
    missing_skills = sorted(required_set.difference(candidate_set))

    if required_skills:
        skill_match_percent = round((len(matched_skills) / len(required_skills)) * 100)
    else:
        skill_match_percent = 0

    profile_completeness = calculate_profile_completeness(profile)

    contact_score = 10 if profile.get("email") and profile.get("phone") else 5
    education_score = 10 if profile.get("education") else 0
    experience_score = 10 if profile.get("experience") else 0
    project_score = 10 if profile.get("projects") else 0

    skill_score = round(skill_match_percent * 0.60)
    completeness_score = round(profile_completeness * 0.10)

    ats_score = skill_score + completeness_score + contact_score + education_score + experience_score + project_score
    ats_score = min(100, ats_score)

    recommendations = []

    if missing_skills:
        recommendations.append(
            "Improve job match by adding or learning: " + ", ".join(missing_skills[:6])
        )

    if not profile.get("projects"):
        recommendations.append("Add project details to improve ATS score.")

    if not profile.get("experience"):
        recommendations.append("Add internship or work experience details if available.")

    if not profile.get("certifications"):
        recommendations.append("Add relevant certifications to strengthen the profile.")

    if ats_score >= 80:
        verdict = "Strong Match"
    elif ats_score >= 60:
        verdict = "Moderate Match"
    else:
        verdict = "Weak Match"

    return {
        "ats_score": ats_score,
        "verdict": verdict,
        "candidate_skills": candidate_skills,
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "skill_match_percent": skill_match_percent,
        "profile_completeness": profile_completeness,
        "recommendations": recommendations,
    }