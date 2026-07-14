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


def match_candidate_to_job(candidate: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluates a candidate profile against a structured Job Description.
    Calculates detailed ATS score, skill match %, missing skills, and recommendations.
    """
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
    
    if required_skills:
        skill_match_percent = round((len(matched_skills) / len(required_skills)) * 100)
    else:
        skill_match_percent = 100 # No skills required -> 100% skill match by default
        
    # 2. Profile Completeness
    profile_completeness = calculate_profile_completeness(candidate)
    
    # 3. Keyword Context Match
    jd_keywords = extract_keywords_from_text(job.get("job_description", ""))
    candidate_raw_text = candidate.get("raw_text", "").lower()
    
    keyword_matches = []
    if jd_keywords and candidate_raw_text:
        for kw in jd_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", candidate_raw_text):
                keyword_matches.append(kw)
        keyword_match_percent = round((len(keyword_matches) / len(jd_keywords)) * 100)
    else:
        keyword_match_percent = 0
        
    # 4. Experience Match
    exp_multiplier, exp_feedback = check_experience_match(
        candidate.get("experience", ""), 
        job.get("experience_required", "")
    )
    
    # 5. ATS Scoring (Refined algorithm)
    # Weights: Skills (55%), Keywords/Context (15%), Completeness & Contact (15%), Experience alignment (15%)
    skill_score = skill_match_percent * 0.55
    keyword_score = keyword_match_percent * 0.15
    completeness_score = profile_completeness * 0.10
    
    contact_score = 5 if candidate.get("email") and candidate.get("phone") else 2.5
    education_score = 5 if candidate.get("education") else 0
    experience_weight = (15 * exp_multiplier)
    
    ats_score = round(skill_score + keyword_score + completeness_score + contact_score + education_score + experience_weight)
    ats_score = min(100, max(0, ats_score))
    
    # Verdicts
    if ats_score >= 80:
        verdict = "Strong Match"
    elif ats_score >= 60:
        verdict = "Moderate Match"
    else:
        verdict = "Weak Match"
        
    # Recommendations
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
        
    return {
        "ats_score": ats_score,
        "verdict": verdict,
        "candidate_skills": candidate_skills,
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "skill_match_percent": skill_match_percent,
        "keyword_match_percent": keyword_match_percent,
        "keyword_matches": keyword_matches,
        "profile_completeness": profile_completeness,
        "experience_feedback": exp_feedback,
        "recommendations": recommendations
    }
