"""
ATS Matching Module
--------------------
Handles candidate-to-job matching, skill gap analysis, and keyword-based ATS score calculations.
"""

import re
from typing import Any
from scorer import normalize_skill, normalize_candidate_skills, calculate_profile_completeness, extract_skills_from_text

# Common English stop words to exclude from keyword extraction
STOP_WORDS = {
    "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "arent",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "cant", "cannot", "could", "couldnt", "did", "didnt", "do", "does", "doesnt", "doing", "dont",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadnt", "has", "hasnt", "have",
    "havent", "having", "he", "hed", "hell", "hes", "her", "here", "heres", "hers", "herself", "him",
    "himself", "his", "how", "hows", "i", "id", "ill", "im", "ive", "if", "in", "into", "is", "isnt",
    "it", "its", "itself", "lets", "me", "more", "most", "mustnt", "my", "myself", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "shant", "she", "shed", "shell", "shes", "should", "shouldnt", "so", "some",
    "such", "than", "that", "thats", "the", "their", "theirs", "them", "themselves", "then", "there",
    "theres", "these", "they", "theyd", "theyll", "theyre", "theyve", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "wasnt", "we", "wed", "well", "were", "weve", "werent",
    "what", "whats", "when", "whens", "where", "wheres", "which", "while", "who", "whos", "whom",
    "why", "whys", "with", "wont", "would", "wouldnt", "you", "youd", "youll", "youre", "youve", "your",
    "yours", "yourself", "yourselves", "development", "management", "experience", "required", "skills",
    "candidate", "company", "working", "role", "team", "project"
}


def extract_keywords_from_text(text: str, top_n: int = 25) -> list[str]:
    """
    Extracts significant non-skill keywords from a text block
    (e.g., job description) to use in scoring.
    """
    if not text:
        return []
    
    # Lowercase, find all alphabetical words of length >= 4
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    
    # Filter out stop words
    filtered_words = [w for w in words if w not in STOP_WORDS]
    
    # Count frequencies
    freq: dict[str, int] = {}
    for w in filtered_words:
        freq[w] = freq.get(w, 0) + 1
        
    # Sort by frequency descending
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [item[0] for item in sorted_words[:top_n]]


def check_experience_match(candidate_exp_text: str, jd_exp_text: str) -> tuple[float, str]:
    """
    Evaluates if candidate experience text meets the job's experience requirements.
    Returns (score_multiplier 0.0 - 1.0, feedback_message).
    """
    if not jd_exp_text:
        return 1.0, "No specific experience duration required."
        
    # Try to extract required years of experience from JD text (e.g. "5+ Years", "3 years", "5-7 Years")
    jd_nums = [int(n) for n in re.findall(r"\b\d+\b", jd_exp_text)]
    if not jd_nums:
        return 1.0, "Experience alignment: Moderate match."
        
    req_years = min(jd_nums)  # take the lower bound, e.g., 5 from 5-7
    
    # Try to extract candidate's years of experience from their experience details
    cand_nums = [int(n) for n in re.findall(r"\b\d+\b", candidate_exp_text or "")]
    if not cand_nums:
        # Check if experience is empty
        if not candidate_exp_text:
            return 0.0, f"Experience alignment: Job requires {req_years}+ years, but candidate profile has no experience section."
        return 0.7, f"Experience alignment: Years of experience not explicitly verified; manual review recommended."
        
    cand_years = max(cand_nums)
    
    # Allow some buffer for mentions of years in education
    if cand_years > 20: # Cap it if they mention graduation years like 2018, 2022
        # Clean graduation years
        cand_years_cleaned = [n for n in cand_nums if n < 20]
        cand_years = max(cand_years_cleaned) if cand_years_cleaned else 2
        
    if cand_years >= req_years:
        return 1.0, f"Experience alignment: Strong match ({cand_years} years detected, meets {req_years}+ years requirement)."
    elif cand_years >= req_years - 2:
        return 0.75, f"Experience alignment: Candidate has {cand_years} years, slightly under the requested {req_years}+ years."
    else:
        return 0.4, f"Experience alignment: Candidate has {cand_years} years, which is significantly below the requested {req_years}+ years."


def calculate_candidate_score(candidate: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluates a candidate profile against a structured Job Description.
    Calculates detailed ATS score, skill match %, missing skills, and recommendations.
    """
    job_id = job.get("job_id", "Unknown Job")

    # 1. Skill Match Calculations
    candidate_skills = normalize_candidate_skills(candidate.get("skills", []))
    
    # Retrieve job required skills
    job_skills_raw = job.get("required_skills") or []
    if isinstance(job_skills_raw, str):
        job_skills_raw = [s.strip() for s in job_skills_raw.split(",") if s.strip()]
        
    required_skills = [normalize_skill(s) for s in job_skills_raw if s]
    
    # Fallback to text extraction if no required skills are defined in the list
    if not required_skills:
        required_skills = extract_skills_from_text(job.get("job_description", ""))
        
    candidate_set = set(candidate_skills)
    required_set = set(required_skills)
    
    matched_skills = sorted(list(candidate_set.intersection(required_set)))
    missing_skills = sorted(list(required_set.difference(candidate_set)))
    extra_skills = sorted(list(candidate_set.difference(required_set)))
    
    if required_skills:
        skill_match_percent = round((len(matched_skills) / len(required_skills)) * 100)
        # Ensure we don't return 0 if there are matched skills
        if len(matched_skills) > 0 and skill_match_percent == 0:
            skill_match_percent = 1
    else:
        skill_match_percent = 100 # No skills required -> 100% skill match by default
        
    # 2. Keyword Context Match (used for project relevance)
    jd_keywords = extract_keywords_from_text(job.get("job_description", ""))
    
    # 3. Experience Match
    exp_multiplier, exp_feedback = check_experience_match(
        candidate.get("experience", ""), 
        job.get("experience_required", "")
    )
    experience_match_percent = round(exp_multiplier * 100)

    # 4. Education Match
    education_match_percent = 100 if candidate.get("education") else 0

    # 5. Project Relevance
    projects_text = candidate.get("projects", "").lower()
    if not projects_text:
        project_relevance_percent = 0
    else:
        if jd_keywords:
            proj_matches = [kw for kw in jd_keywords if re.search(r"\b" + re.escape(kw) + r"\b", projects_text)]
            project_relevance_percent = round((len(proj_matches) / len(jd_keywords)) * 100)
            project_relevance_percent = min(100, max(50, project_relevance_percent * 2)) # scale up slightly if they have projects
        else:
            project_relevance_percent = 100

    # 6. Certification Match
    cert_text = candidate.get("certifications", "").lower()
    if not cert_text:
        certification_match_percent = 0
    else:
        if required_skills:
            cert_matches = [sk for sk in required_skills if re.search(r"\b" + re.escape(sk.lower()) + r"\b", cert_text)]
            certification_match_percent = round((len(cert_matches) / len(required_skills)) * 100) if cert_matches else 50
        else:
            certification_match_percent = 100

    # 7. Hiring Score (Weighted)
    # Skill Match 50%, Experience Match 20%, Education Match 10%, Project Relevance 10%, Certifications 10%
    hiring_score = round(
        skill_match_percent * 0.50 +
        experience_match_percent * 0.20 +
        education_match_percent * 0.10 +
        project_relevance_percent * 0.10 +
        certification_match_percent * 0.10
    )
    hiring_score = min(100, max(0, hiring_score))
    
    # 8. Recommendation Status
    if hiring_score >= 90:
        recommendation = "Excellent Match"
    elif hiring_score >= 80:
        recommendation = "Highly Recommended"
    elif hiring_score >= 65:
        recommendation = "Recommended"
    elif hiring_score >= 50:
        recommendation = "Consider"
    elif hiring_score >= 30:
        recommendation = "Weak Match"
    else:
        recommendation = "Not Recommended"
        
    # Recommendations text (for the UI dropdown)
    recommendations = []
    if missing_skills:
        recommendations.append(
            f"Address missing skills gap by acquiring: {', '.join(missing_skills[:5])}"
        )
    if not candidate.get("projects"):
        recommendations.append("Strengthen resume relevance by detailing project experience.")
    if not candidate.get("certifications") and required_skills:
        recommendations.append("Consider obtaining industry certifications matching required tech stacks.")
    if exp_multiplier < 0.7:
        recommendations.append("Experience duration appears low compared to job requirement. Highlight transferable projects.")

    score_breakdown = {
        "skill_match": skill_match_percent,
        "experience_match": experience_match_percent,
        "education_match": education_match_percent,
        "project_relevance": project_relevance_percent,
        "certification_match": certification_match_percent
    }
        
    return {
        "job_id": job_id,
        "hiring_score": hiring_score,
        "recommendation": recommendation,
        "score_breakdown": score_breakdown,
        "skill_match": skill_match_percent,
        "experience_match": experience_match_percent,
        "education_match": education_match_percent,
        "project_relevance": project_relevance_percent,
        "certification_match": certification_match_percent,
        "candidate_skills": candidate_skills,
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "extra_skills": extra_skills,
        "experience_feedback": exp_feedback,
        "recommendations": recommendations,
        "profile_completeness": calculate_profile_completeness(candidate)
    }
