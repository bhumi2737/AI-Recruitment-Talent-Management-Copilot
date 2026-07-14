"""
Database operations for the Job Descriptions (jobs collection).
Reuses the MongoDB connection settings from database.py.
"""

import datetime
import uuid
from typing import Any
from database import get_mongo_client, MONGO_CONFIG

JOBS_COLLECTION = "jobs"


def create_job(job_data: dict[str, Any]) -> str:
    """
    Inserts a new job description into the jobs collection.
    Automatically generates a unique job_id and created_at timestamp.
    Returns the generated job_id.
    """
    with get_mongo_client() as client:
        db = client[MONGO_CONFIG["dbname"]]
        col = db[JOBS_COLLECTION]

        # Generate unique job ID if not provided
        job_id = job_data.get("job_id")
        if not job_id:
            job_id = f"JOB-{uuid.uuid4().hex[:6].upper()}"

        # Build document
        doc = {
            "job_id": job_id,
            "job_title": job_data.get("job_title", "").strip(),
            "company_name": job_data.get("company_name", "").strip(),
            "required_skills": job_data.get("required_skills", []),
            "experience_required": job_data.get("experience_required", "").strip(),
            "location": job_data.get("location", "").strip(),
            "salary": job_data.get("salary", "").strip(),
            "job_description": job_data.get("job_description", "").strip(),
            "created_at": datetime.datetime.utcnow()
        }

        col.insert_one(doc)
        return job_id


def get_all_jobs() -> list[dict[str, Any]]:
    """
    Fetches all job descriptions from the database, sorted by creation time (newest first).
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[JOBS_COLLECTION]

            docs = col.find().sort("created_at", -1)
            jobs = []
            for doc in docs:
                # Convert ObjectId to string for JSON serialization
                doc["_id"] = str(doc["_id"])
                if isinstance(doc.get("created_at"), datetime.datetime):
                    doc["created_at"] = doc["created_at"].isoformat()
                jobs.append(doc)
            return jobs
    except Exception:
        return []


def get_job_by_id(job_id: str) -> dict[str, Any] | None:
    """
    Fetches a specific job description by its job_id.
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[JOBS_COLLECTION]

            doc = col.find_one({"job_id": job_id})
            if doc:
                doc["_id"] = str(doc["_id"])
                if isinstance(doc.get("created_at"), datetime.datetime):
                    doc["created_at"] = doc["created_at"].isoformat()
                return doc
            return None
    except Exception:
        return None


def update_job(job_id: str, job_data: dict[str, Any]) -> bool:
    """
    Updates an existing job description by job_id.
    Returns True if update was successful, False otherwise.
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[JOBS_COLLECTION]

            # We don't want to overwrite created_at or job_id
            update_fields = {}
            for field in ["job_title", "company_name", "required_skills", 
                          "experience_required", "location", "salary", "job_description"]:
                if field in job_data:
                    update_fields[field] = job_data[field]

            result = col.update_one({"job_id": job_id}, {"$set": update_fields})
            return result.matched_count > 0
    except Exception:
        return False


def delete_job(job_id: str) -> bool:
    """
    Deletes a job description by job_id.
    Returns True if deletion was successful, False otherwise.
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[JOBS_COLLECTION]

            result = col.delete_one({"job_id": job_id})
            return result.deleted_count > 0
    except Exception:
        return False
