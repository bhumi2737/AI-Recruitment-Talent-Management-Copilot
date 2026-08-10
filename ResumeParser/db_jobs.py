"""
Database operations for the Job Descriptions (jobs collection & persistent offline cache).
Reuses the MongoDB connection settings from database.py.
"""

import datetime
import uuid
from typing import Any
from database import get_mongo_client, MONGO_CONFIG
import offline_storage

JOBS_COLLECTION = "jobs"
_OFFLINE_JOBS: dict[str, dict[str, Any]] = offline_storage.load_offline_data("jobs")


def create_job(job_data: dict[str, Any]) -> str:
    """
    Inserts a new job description into the jobs collection and offline cache.
    Automatically generates a unique job_id and created_at timestamp.
    Returns the generated job_id.
    """
    job_id = job_data.get("job_id")
    if not job_id:
        job_id = f"JOB-{uuid.uuid4().hex[:6].upper()}"

    doc = {
        "job_id": job_id,
        "job_title": job_data.get("job_title", "").strip(),
        "company_name": job_data.get("company_name", "").strip(),
        "required_skills": job_data.get("required_skills", []),
        "experience_required": job_data.get("experience_required", "").strip(),
        "location": job_data.get("location", "").strip(),
        "salary": job_data.get("salary", "").strip(),
        "job_description": job_data.get("job_description", "").strip(),
        "created_at": datetime.datetime.utcnow().isoformat()
    }

    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[JOBS_COLLECTION]
            col.insert_one(dict(doc))
    except Exception:
        pass

    _OFFLINE_JOBS[job_id] = doc
    offline_storage.upsert_offline_record("jobs", job_id, doc)
    return job_id


def get_all_jobs() -> list[dict[str, Any]]:
    """
    Fetches all job descriptions from the database or offline cache, sorted by creation time (newest first).
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[JOBS_COLLECTION]

            docs = col.find().sort("created_at", -1)
            jobs = []
            for doc in docs:
                doc["_id"] = str(doc["_id"])
                if isinstance(doc.get("created_at"), datetime.datetime):
                    doc["created_at"] = doc["created_at"].isoformat()
                jobs.append(doc)
            if jobs:
                return jobs
    except Exception:
        pass

    jobs = list(_OFFLINE_JOBS.values())
    jobs.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return jobs


def get_job_by_id(job_id: str) -> dict[str, Any] | None:
    """
    Fetches a specific job description by its job_id.
    """
    jid = str(job_id or "").strip()
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[JOBS_COLLECTION]

            doc = col.find_one({"job_id": jid})
            if doc:
                doc["_id"] = str(doc["_id"])
                if isinstance(doc.get("created_at"), datetime.datetime):
                    doc["created_at"] = doc["created_at"].isoformat()
                return doc
    except Exception:
        pass

    if jid in _OFFLINE_JOBS:
        return dict(_OFFLINE_JOBS[jid])
    return None


def update_job(job_id: str, job_data: dict[str, Any]) -> bool:
    """
    Updates an existing job description by job_id.
    Returns True if update was successful, False otherwise.
    """
    jid = str(job_id or "").strip()
    update_fields = {}
    for field in ["job_title", "company_name", "required_skills", 
                  "experience_required", "location", "salary", "job_description"]:
        if field in job_data:
            update_fields[field] = job_data[field]

    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[JOBS_COLLECTION]
            result = col.update_one({"job_id": jid}, {"$set": update_fields})
    except Exception:
        pass

    if jid in _OFFLINE_JOBS:
        _OFFLINE_JOBS[jid].update(update_fields)
        offline_storage.upsert_offline_record("jobs", jid, _OFFLINE_JOBS[jid])
        return True

    return False


def delete_job(job_id: str) -> bool:
    """
    Deletes a job description by job_id.
    Returns True if deletion was successful, False otherwise.
    """
    jid = str(job_id or "").strip()
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[JOBS_COLLECTION]
            col.delete_one({"job_id": jid})
    except Exception:
        pass

    if jid in _OFFLINE_JOBS:
        del _OFFLINE_JOBS[jid]
        offline_storage.save_offline_data("jobs", _OFFLINE_JOBS)
        return True

    return False
