"""
Database operations for the new Job Descriptions Module.
Uses the 'job_descriptions' MongoDB collection.
"""

import datetime
import uuid
from typing import Any
from database import get_mongo_client, MONGO_CONFIG

JD_COLLECTION = "job_descriptions"

def create_jd(jd_data: dict[str, Any]) -> str:
    """
    Inserts a new job description into the job_descriptions collection.
    Automatically generates a unique _id (as a string) and created_at timestamp.
    Returns the generated _id.
    """
    with get_mongo_client() as client:
        db = client[MONGO_CONFIG["dbname"]]
        col = db[JD_COLLECTION]

        # Generate unique ID if not provided
        jd_id = jd_data.get("_id")
        if not jd_id:
            jd_id = f"JD-{uuid.uuid4().hex[:8].upper()}"

        doc = {
            "_id": jd_id,
            "job_title": jd_data.get("job_title", "").strip(),
            "company": jd_data.get("company", "").strip(),
            "location": jd_data.get("location", "").strip(),
            "experience": jd_data.get("experience", "").strip(),
            "description": jd_data.get("description", "").strip(),
            "required_skills": jd_data.get("required_skills", []),
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        col.insert_one(doc)
        return jd_id

def get_all_jds() -> list[dict[str, Any]]:
    """
    Fetches all job descriptions from the database.
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[JD_COLLECTION]
            docs = col.find().sort("created_at", -1)
            return list(docs)
    except Exception:
        return []

def get_jd_by_id(jd_id: str) -> dict[str, Any] | None:
    """
    Fetches a specific job description by its _id.
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[JD_COLLECTION]
            return col.find_one({"_id": jd_id})
    except Exception:
        return None
