"""
Database Module (MongoDB Edition)
---------------------------------
Handles MongoDB connection and candidate data storage using pymongo.
Gracefully handles connection failures so the app can still run offline.
"""

import os
import datetime
from typing import Any

from dotenv import load_dotenv
import pymongo

# Load environment variables from .env file
load_dotenv()

# MongoDB connection settings (override with environment variables)
MONGO_CONFIG = {
    "uri": os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
    "dbname": os.getenv("MONGO_DB", "recruitment_copilot"),
    "collection": os.getenv("MONGO_COLLECTION", "candidates"),
}


def get_mongo_client(timeout_ms: int = 3000):
    """Create and return a new MongoClient instance."""
    import certifi
    try:
        ca = certifi.where()
    except Exception:
        ca = None

    kwargs = {"serverSelectionTimeoutMS": timeout_ms}
    if ca:
        kwargs["tlsCAFile"] = ca
    else:
        kwargs["tlsAllowInvalidCertificates"] = True

    return pymongo.MongoClient(MONGO_CONFIG["uri"], **kwargs)


def test_connection() -> tuple[bool, str]:
    """
    Test whether MongoDB is reachable.
    Returns (success: bool, message: str).
    """
    try:
        with get_mongo_client(timeout_ms=2000) as client:
            # The ping command will trigger server selection and fail if offline
            client.admin.command('ping')
        return True, "Connected to MongoDB"
    except Exception as exc:
        return False, f"Database unavailable: {exc}"


def _list_to_text(value: list | str | None) -> str:
    """Convert a list (e.g. skills) to a comma-separated string for storage."""
    if isinstance(value, list):
        return ", ".join(value)
    return value or ""


def save_candidate(profile: dict[str, Any]) -> tuple[bool, str, str | None]:
    """
    Insert a parsed candidate profile into the MongoDB collection.
    Returns (success, message, candidate_id).
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            
            # Check if candidate already exists by email or phone
            email = profile.get("email", "").strip() if profile.get("email") else ""
            phone = profile.get("phone", "").strip() if profile.get("phone") else ""
            
            if email:
                existing = col.find_one({"email": email})
                if existing:
                    return False, f"Candidate with email '{email}' already exists in the database.", str(existing["_id"])
            
            if phone:
                existing = col.find_one({"phone": phone})
                if existing:
                    return False, f"Candidate with phone '{phone}' already exists in the database.", str(existing["_id"])
            
            doc = {
                "full_name": profile.get("full_name", ""),
                "email": profile.get("email", ""),
                "phone": profile.get("phone", ""),
                "skills": _list_to_text(profile.get("skills")),
                "education": profile.get("education", ""),
                "experience": profile.get("experience", ""),
                "certifications": profile.get("certifications", ""),
                "projects": profile.get("projects", ""),
                "raw_text": profile.get("raw_text", ""),
                "created_at": datetime.datetime.utcnow()
            }
            
            result = col.insert_one(doc)
            return True, "Candidate saved successfully", str(result.inserted_id)
    except Exception as exc:
        return False, f"Failed to save candidate: {exc}", None


def get_recent_candidates(limit: int = 10) -> tuple[list[dict], str | None]:
    """
    Fetch the most recently added candidates.
    Returns (candidates_list, error_message).
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            
            # Fetch and sort by created_at descending
            docs = col.find().sort("created_at", pymongo.DESCENDING).limit(limit)
            
            candidates = []
            for doc in docs:
                candidates.append({
                    "id": str(doc["_id"]),
                    "full_name": doc.get("full_name", ""),
                    "email": doc.get("email", ""),
                    "phone": doc.get("phone", ""),
                    "skills": doc.get("skills", ""),
                })
            return candidates, None
    except Exception as exc:
        return [], str(exc)


def get_candidate_count() -> int:
    """Return total number of candidates in the MongoDB database."""
    try:
        with get_mongo_client(timeout_ms=2000) as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            return col.count_documents({})
    except Exception:
        return 0


def get_all_candidates(search_query: str = None) -> list[dict]:
    """
    Fetch all candidates from MongoDB, optionally filtered by a search query.
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            
            query = {}
            if search_query and search_query.strip():
                q = search_query.strip()
                query = {
                    "$or": [
                        {"full_name": {"$regex": q, "$options": "i"}},
                        {"email": {"$regex": q, "$options": "i"}},
                        {"skills": {"$regex": q, "$options": "i"}},
                        {"education": {"$regex": q, "$options": "i"}},
                        {"experience": {"$regex": q, "$options": "i"}},
                    ]
                }
                
            docs = col.find(query).sort("created_at", pymongo.DESCENDING)
            
            candidates = []
            for doc in docs:
                candidates.append({
                    "id": str(doc["_id"]),
                    "full_name": doc.get("full_name", ""),
                    "email": doc.get("email", ""),
                    "phone": doc.get("phone", ""),
                    "skills": doc.get("skills", ""),
                    "education": doc.get("education", ""),
                    "experience": doc.get("experience", ""),
                    "certifications": doc.get("certifications", ""),
                    "projects": doc.get("projects", ""),
                    "raw_text": doc.get("raw_text", ""),
                    "created_at": doc.get("created_at"),
                })
            return candidates
    except Exception:
        return []
