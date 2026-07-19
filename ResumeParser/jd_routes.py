"""
FastAPI Routes for Job Description Matching Module.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import db_jobs
from jd_matching_service import compare_candidates_with_jd

router = APIRouter(prefix="/jobs", tags=["Job Description Matching"])

# --- Pydantic Models ---
class JobDescriptionBase(BaseModel):
    job_title: str = Field(..., example="Backend Developer")
    company_name: str = Field(..., example="Infosys")
    location: str = Field(..., example="Bangalore")
    experience_required: str = Field(..., example="2+ Years")
    job_description: str = Field(..., example="Complete Job Description")
    required_skills: List[str] = Field(..., example=["Python", "FastAPI", "Docker", "MySQL"])
    salary: str = Field(default="Not specified")

class JobDescriptionCreate(JobDescriptionBase):
    pass

class JobDescriptionResponse(JobDescriptionBase):
    job_id: str
    created_at: str

class MatchCandidateResult(BaseModel):
    candidate_name: str
    email: str
    matched_skills: List[str]
    missing_skills: List[str]
    additional_skills: List[str]
    match_percentage: float


# --- Routes ---

@router.post("/", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_job_description(jd_in: JobDescriptionCreate):
    """
    Creates a new Job Description.
    """
    try:
        jd_data = jd_in.model_dump()
        jd_id = db_jobs.create_job(jd_data)
        
        created_jd = db_jobs.get_job_by_id(jd_id)
        if not created_jd:
            raise HTTPException(status_code=500, detail="Failed to retrieve created JD.")
        return created_jd
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get("/", response_model=List[JobDescriptionResponse])
def get_all_job_descriptions():
    """
    Retrieves all Job Descriptions.
    """
    jds = db_jobs.get_all_jobs()
    return jds

@router.get("/{jd_id}", response_model=JobDescriptionResponse)
def get_job_description(jd_id: str):
    """
    Retrieves a single Job Description by ID.
    """
    jd = db_jobs.get_job_by_id(jd_id)
    if not jd:
        raise HTTPException(status_code=404, detail="Job Description not found.")
    return jd

@router.get("/{jd_id}/matches", response_model=List[MatchCandidateResult])
def compare_with_selected_jd(jd_id: str):
    """
    Compares all candidates with the selected JD and returns a ranked list.
    """
    jd = db_jobs.get_job_by_id(jd_id)
    if not jd:
        raise HTTPException(status_code=404, detail="Job Description not found.")
    
    try:
        results = compare_candidates_with_jd(jd_id)
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
