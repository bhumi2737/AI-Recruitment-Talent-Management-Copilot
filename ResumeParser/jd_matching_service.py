"""
Job Description Matching Service layer.
Handles the logic of comparing all parsed candidates against a selected Job Description.
"""

from typing import Any
import db_jobs
from database import get_mongo_client, MONGO_CONFIG

def normalize_skill(skill: str) -> str:
    """
    Normalizes a single skill by removing leading/trailing spaces and converting to lowercase.
    """
    return skill.strip().lower()

def get_normalized_skills(skills_list: list[str] | str) -> set[str]:
    """
    Normalizes a list (or comma-separated string) of skills and removes duplicates.
    """
    if isinstance(skills_list, str):
        # Handle case where skills are stored as a comma-separated string
        skills = [s for s in skills_list.split(",") if s.strip()]
    else:
        skills = skills_list or []
        
    normalized = set()
    for s in skills:
        ns = normalize_skill(s)
        if ns:
            normalized.add(ns)
    return normalized

def fetch_all_candidates() -> list[dict[str, Any]]:
    """
    Fetches all parsed candidates from the database.
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            # Exclude raw_text to save memory
            docs = col.find({}, {"raw_text": 0})
            return list(docs)
    except Exception:
        return []

def compare_candidates_with_jd(jd_id: str) -> list[dict[str, Any]]:
    """
    Compares all parsed candidates with the given JD.
    Returns a ranked list of candidates sorted by match percentage.
    """
    jd = db_jobs.get_job_by_id(jd_id)
    if not jd:
        return []

    jd_skills = get_normalized_skills(jd.get("required_skills", []))
    candidates = fetch_all_candidates()
    
    results = []
    for cand in candidates:
        cand_skills = get_normalized_skills(cand.get("skills", []))
        
        matched_skills = list(jd_skills.intersection(cand_skills))
        missing_skills = list(jd_skills.difference(cand_skills))
        additional_skills = list(cand_skills.difference(jd_skills))
        
        # Calculate percentage
        if len(jd_skills) > 0:
            match_percentage = round((len(matched_skills) / len(jd_skills)) * 100, 2)
        else:
            match_percentage = 100.0 if len(cand_skills) > 0 else 0.0
            
        # Map back to original case for display if possible (optional, but requested output just needs the lists)
        # We'll just return the normalized ones for simplicity as per requirement example
        
        # The prompt requires this output structure:
        # candidate_name, email, matched_skills, missing_skills, additional_skills, match_percentage
        results.append({
            "candidate_name": cand.get("full_name", "Unknown Candidate"),
            "email": cand.get("email", ""),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "additional_skills": additional_skills,
            "match_percentage": match_percentage
        })
        
    # Sort in descending order of match percentage
    results.sort(key=lambda x: x["match_percentage"], reverse=True)
    return results
