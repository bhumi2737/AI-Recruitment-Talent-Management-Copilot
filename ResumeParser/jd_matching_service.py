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

from jd_matcher import calculate_candidate_score

def compare_candidates_with_jd(jd_id: str) -> list[dict[str, Any]]:
    """
    Compares all parsed candidates with the given JD using the centralized scoring engine.
    Returns a ranked list of candidates sorted by match percentage.
    """
    jd = db_jobs.get_job_by_id(jd_id)
    if not jd:
        return []

    candidates = fetch_all_candidates()
    
    results = []
    for cand in candidates:
        ats_result = calculate_candidate_score(cand, jd)
        
        results.append({
            "candidate_id": str(cand.get("_id", "")),
            "candidate_name": cand.get("full_name", "Unknown Candidate"),
            "email": cand.get("email", ""),
            "matched_skills": ats_result.get("matched_skills", []),
            "missing_skills": ats_result.get("missing_skills", []),
            "additional_skills": ats_result.get("extra_skills", []),
            "match_percentage": ats_result.get("hiring_score", 0),
            "recommendation": ats_result.get("recommendation", "Not Recommended")
        })
        
    # Sort in descending order of match percentage (hiring score)
    results.sort(key=lambda x: x["match_percentage"], reverse=True)
    return results
