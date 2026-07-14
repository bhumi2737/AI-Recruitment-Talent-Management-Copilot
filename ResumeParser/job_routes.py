"""
FastAPI Routes for Job Operations
---------------------------------
Defines HTTP endpoints and request/response models for CRUD operations on Job Descriptions.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import db_jobs

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


# --- Pydantic Models ---

class JobBase(BaseModel):
    job_title: str = Field(..., example="Senior Python Developer")
    company_name: str = Field(..., example="Google")
    required_skills: List[str] = Field(default_factory=list, example=["Python", "FastAPI", "MongoDB"])
    experience_required: str = Field(..., example="3-5 Years")
    location: str = Field(..., example="San Francisco, CA")
    salary: str = Field(..., example="$120,000 - $150,000")
    job_description: str = Field(..., example="Looking for a Python developer experienced in backend services.")


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    required_skills: Optional[List[str]] = None
    experience_required: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    job_description: Optional[str] = None


class JobResponse(JobBase):
    job_id: str
    created_at: str


# --- Route Endpoints ---

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_new_job(job_in: JobCreate):
    """
    Creates a new Job Description in the database.
    """
    try:
        job_data = job_in.model_dump()
        job_id = db_jobs.create_job(job_data)
        
        # Retrieve the created job to return
        created_job = db_jobs.get_job_by_id(job_id)
        if not created_job:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Job description was created but could not be retrieved."
            )
        return created_job
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create job description: {exc}"
        )


@router.get("/", response_model=List[JobResponse])
def read_all_jobs():
    """
    Retrieves all Job Descriptions.
    """
    return db_jobs.get_all_jobs()


@router.get("/{job_id}", response_model=JobResponse)
def read_job(job_id: str):
    """
    Retrieves a specific Job Description by its job_id.
    """
    job = db_jobs.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description with ID '{job_id}' not found."
        )
    return job


@router.put("/{job_id}", status_code=status.HTTP_200_OK)
def update_existing_job(job_id: str, job_in: JobUpdate):
    """
    Updates an existing Job Description by its job_id.
    """
    # Check if job exists
    existing_job = db_jobs.get_job_by_id(job_id)
    if not existing_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description with ID '{job_id}' not found."
        )
        
    # Filter out None values to perform partial update
    update_data = {k: v for k, v in job_in.model_dump().items() if v is not None}
    
    success = db_jobs.update_job(job_id, update_data)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update job description."
        )
        
    return {"message": "Job description updated successfully", "job_id": job_id}


@router.delete("/{job_id}", status_code=status.HTTP_200_OK)
def delete_existing_job(job_id: str):
    """
    Deletes a Job Description by its job_id.
    """
    # Check if job exists
    existing_job = db_jobs.get_job_by_id(job_id)
    if not existing_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job description with ID '{job_id}' not found."
        )
        
    success = db_jobs.delete_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete job description."
        )
        
    return {"message": "Job description deleted successfully", "job_id": job_id}
