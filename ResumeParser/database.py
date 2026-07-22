"""
Database Module (MongoDB Edition)
---------------------------------
Handles MongoDB connection and candidate data storage using pymongo.
Gracefully handles connection failures so the app can still run offline.
"""

import os
import datetime
import hashlib
import re
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return None

pymongo = None

def _get_pymongo():
    global pymongo
    if pymongo is None:
        try:
            import pymongo as _pymongo
            pymongo = _pymongo
        except ImportError as exc:
            raise ImportError(
                "The pymongo package is required for MongoDB operations. "
                "Install it with `pip install pymongo`."
            ) from exc
    return pymongo


def _safe_import_objectid():
    try:
        from bson.objectid import ObjectId
        return ObjectId
    except ImportError:
        return None

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

    _pymongo = _get_pymongo()
    kwargs = {"serverSelectionTimeoutMS": timeout_ms}
    if ca:
        kwargs["tlsCAFile"] = ca
    else:
        kwargs["tlsAllowInvalidCertificates"] = True

    return _pymongo.MongoClient(MONGO_CONFIG["uri"], **kwargs)


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


def _build_resume_hash(raw_text: str, source_filename: str) -> str:
    raw_text = raw_text or ""
    source_filename = source_filename or ""
    digest = hashlib.sha256((raw_text + source_filename).encode("utf-8", errors="ignore"))
    return digest.hexdigest()


def save_candidate(profile: dict[str, Any]) -> tuple[bool, str, str | None, str | None]:
    """
    Insert or update a parsed candidate profile into the MongoDB collection.
    Returns (success, message, status, candidate_id).
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]

            email = profile.get("email", "").strip() if profile.get("email") else ""
            phone = profile.get("phone", "").strip() if profile.get("phone") else ""
            raw_text = profile.get("raw_text", "") or ""
            source_filename = profile.get("source_filename", "") or ""
            source_file_type = profile.get("source_file_type", "") or ""
            resume_hash = _build_resume_hash(raw_text, source_filename)

            if email:
                filter_query = {"email": email}
            elif phone:
                filter_query = {"phone": phone}
            else:
                filter_query = {"resume_hash": resume_hash}

            update_doc = {
                "$set": {
                    "full_name": profile.get("full_name", ""),
                    "email": email,
                    "phone": phone,
                    "skills": _list_to_text(profile.get("skills")),
                    "education": profile.get("education", ""),
                    "experience": profile.get("experience", ""),
                    "certifications": profile.get("certifications", ""),
                    "projects": profile.get("projects", ""),
                    "raw_text": raw_text,
                    "updated_at": datetime.datetime.utcnow(),
                    "source_filename": source_filename,
                    "source_file_type": source_file_type,
                    "resume_hash": resume_hash,
                },
                "$setOnInsert": {
                    "created_at": datetime.datetime.utcnow(),
                },
            }

            result = col.update_one(filter_query, update_doc, upsert=True)
            if result.upserted_id is not None:
                return True, "Candidate inserted successfully", "inserted", str(result.upserted_id)
            return True, "Candidate updated successfully", "updated", str(col.find_one(filter_query)["_id"])
    except Exception as exc:
        return False, f"Failed to save candidate: {exc}", None, None


def save_evaluation(job_id: str, candidate_id: str, hiring_score: int, recommendation: str, score_breakdown: dict) -> tuple[bool, str]:
    """
    Store candidate evaluation results in the evaluations collection using upsert.
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db["evaluations"]
            
            filter_query = {
                "job_id": str(job_id),
                "candidate_id": str(candidate_id),
            }
            update_doc = {
                "$set": {
                    "job_id": str(job_id),
                    "candidate_id": str(candidate_id),
                    "hiring_score": int(hiring_score),
                    "recommendation": str(recommendation),
                    "score_breakdown": score_breakdown or {},
                    "evaluation_time": datetime.datetime.utcnow(),
                }
            }
            col.update_one(filter_query, update_doc, upsert=True)
            return True, "Evaluation saved successfully"
    except Exception as exc:
        return False, f"Failed to save evaluation: {exc}"


def auto_evaluate_all_candidates(force: bool = False) -> int:
    """
    Auto-evaluate candidates against available job descriptions if evaluations collection is empty (or if force=True).
    Returns count of evaluations created/updated.
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            eval_col = db["evaluations"]
            if not force and eval_col.count_documents({}) > 0:
                return 0

            cand_col = db[MONGO_CONFIG["collection"]]
            candidates = list(cand_col.find({}))
            if not candidates:
                return 0

            import db_jobs
            jobs = db_jobs.get_all_jobs()
            if not jobs:
                return 0

            from jd_matcher import calculate_candidate_score
            count = 0
            for candidate in candidates:
                cand_id = str(candidate["_id"])
                for job in jobs:
                    job_id = job.get("job_id", "")
                    if not job_id:
                        continue
                    res = calculate_candidate_score(candidate, job)
                    save_evaluation(
                        job_id=job_id,
                        candidate_id=cand_id,
                        hiring_score=res.get("hiring_score", 0),
                        recommendation=res.get("recommendation", "Not Recommended"),
                        score_breakdown=res.get("score_breakdown", {}),
                    )
                    count += 1
            return count
    except Exception:
        return 0


def get_all_evaluations(limit: int = 100) -> list[dict]:
    """
    Fetch the most recent evaluations from the database.
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db["evaluations"]
            _pymongo = _get_pymongo()
            return list(col.find({}, {"_id": 0}).sort("evaluation_time", _pymongo.DESCENDING).limit(limit))
    except Exception:
        return []


def get_recent_candidates(limit: int = 10) -> tuple[list[dict], str | None]:
    """
    Fetch the most recently saved or updated candidates.
    Returns (candidates_list, error_message).
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            
            _pymongo = _get_pymongo()
            docs = col.find({}, {"raw_text": 0}).sort("updated_at", _pymongo.DESCENDING).limit(limit)
            
            candidates = []
            for doc in docs:
                candidates.append({
                    "id": str(doc["_id"]),
                    "full_name": doc.get("full_name", ""),
                    "email": doc.get("email", ""),
                    "phone": doc.get("phone", ""),
                    "skills": doc.get("skills", ""),
                    "updated_at": doc.get("updated_at"),
                })
            return candidates, None
    except Exception as exc:
        return [], str(exc)


def _normalize_skill_name(skill: str) -> str:
    if not skill:
        return ""
    cleaned = re.sub(r"[^\w\+#\.\- ]+", "", skill).strip()
    normalized_key = cleaned.lower()
    normalization_map = {
        "node.js": "Node.js",
        "rest api": "REST API",
        "restapi": "REST API",
        "graphql": "GraphQL",
        "aws": "AWS",
        "gcp": "GCP",
        "azure": "Azure",
        "ci/cd": "CI/CD",
        "nlp": "NLP",
        "ml": "ML",
        "ai": "AI",
        "sql": "SQL",
        "html": "HTML",
        "css": "CSS",
        "c#": "C#",
        "c++": "C++",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "postgresql": "PostgreSQL",
        "mysql": "MySQL",
        "mongodb": "MongoDB",
        "pandas": "Pandas",
        "numpy": "NumPy",
        "tensorflow": "TensorFlow",
        "pytorch": "PyTorch",
        "scikit-learn": "Scikit-Learn",
        "power bi": "Power BI",
        "tableau": "Tableau",
        "streamlit": "Streamlit",
        "selenium": "Selenium",
        "junit": "JUnit",
        "pytest": "Pytest",
        "terraform": "Terraform",
        "ansible": "Ansible",
        "figma": "Figma",
        "photoshop": "Photoshop",
    }
    if normalized_key in normalization_map:
        return normalization_map[normalized_key]
    if cleaned.upper() == cleaned and len(cleaned) <= 5:
        return cleaned
    return cleaned.title()


def _normalize_skills_text(skills_text: str) -> list[str]:
    if not skills_text:
        return []
    skills = re.split(r"[,|;]+", skills_text)
    normalized = []
    seen = set()
    for skill in skills:
        candidate = _normalize_skill_name(skill)
        if candidate and candidate not in seen:
            seen.add(candidate)
            normalized.append(candidate)
    return sorted(normalized, key=str.lower)


def get_candidate_count() -> int:
    """Return total number of candidates in the MongoDB database."""
    try:
        with get_mongo_client(timeout_ms=2000) as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            return col.count_documents({})
    except Exception:
        return 0


def get_dashboard_stats() -> dict:
    """Return dashboard stats with aggregated skill counts and candidate totals."""
    try:
        with get_mongo_client(timeout_ms=2000) as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            total_candidates = col.count_documents({})
            docs = list(col.find({}, {
                "full_name": 1,
                "email": 1,
                "phone": 1,
                "education": 1,
                "experience": 1,
                "skills": 1,
                "updated_at": 1,
            }))

            skill_counts: dict[str, int] = {}
            completeness_list = []
            for doc in docs:
                fields = ["full_name", "email", "phone", "education", "experience", "skills"]
                filled = sum(1 for field in fields if doc.get(field))
                completeness_list.append((filled / len(fields)) * 100)
                skills_text = doc.get("skills", "")
                for skill in re.split(r"[,|;]+", skills_text or ""):
                    skill_clean = skill.strip()
                    if not skill_clean:
                        continue
                    normalized = _normalize_skill_name(skill_clean)
                    if normalized:
                        skill_counts[normalized] = skill_counts.get(normalized, 0) + 1

            avg_completeness = round(sum(completeness_list) / len(completeness_list), 1) if completeness_list else 0
            top_skills = sorted(skill_counts.items(), key=lambda item: item[1], reverse=True)[:15]
            recent_docs = sorted(
                [
                    {
                        "id": str(doc["_id"]),
                        "full_name": doc.get("full_name", ""),
                        "email": doc.get("email", ""),
                        "updated_at": doc.get("updated_at"),
                    }
                    for doc in docs
                    if doc.get("updated_at")
                ],
                key=lambda item: item["updated_at"],
                reverse=True,
            )[:5]

            return {
                "total_candidates": total_candidates,
                "avg_completeness": avg_completeness,
                "unique_skills_count": len(skill_counts),
                "top_skills": [{"skill": skill, "count": count} for skill, count in top_skills],
                "recent_activity": recent_docs,
            }
    except Exception:
        return {
            "total_candidates": 0,
            "avg_completeness": 0,
            "unique_skills_count": 0,
            "top_skills": [],
            "recent_activity": [],
        }


def get_candidate_by_id(candidate_id: str, include_raw_text: bool = True) -> dict | None:
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            ObjectId = _safe_import_objectid()
            doc = None
            if ObjectId is not None:
                try:
                    doc = col.find_one({"_id": ObjectId(candidate_id)})
                except Exception:
                    doc = None
            if not doc:
                doc = col.find_one({"_id": candidate_id})
            if not doc and isinstance(candidate_id, str) and candidate_id.strip():
                doc = col.find_one({"email": candidate_id.strip()})
            if not doc:
                return None
            result = {
                "id": str(doc["_id"]),
                "full_name": doc.get("full_name", ""),
                "email": doc.get("email", ""),
                "phone": doc.get("phone", ""),
                "skills": ", ".join(_normalize_skills_text(doc.get("skills", ""))),
                "education": doc.get("education", ""),
                "experience": doc.get("experience", ""),
                "certifications": doc.get("certifications", ""),
                "projects": doc.get("projects", ""),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
            }
            if include_raw_text:
                result["raw_text"] = doc.get("raw_text", "")
            return result
    except Exception:
        return None


def get_all_candidates(search_query: str = None, include_raw_text: bool = False) -> list[dict]:
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
            projection = {
                "raw_text": 0,
            }
            if include_raw_text:
                projection = None
            docs = col.find(query, projection).sort("updated_at", pymongo.DESCENDING)
            
            candidates = []
            for doc in docs:
                candidates.append({
                    "id": str(doc["_id"]),
                    "full_name": doc.get("full_name", ""),
                    "email": doc.get("email", ""),
                    "phone": doc.get("phone", ""),
                    "skills": ", ".join(_normalize_skills_text(doc.get("skills", ""))),
                    "education": doc.get("education", ""),
                    "experience": doc.get("experience", ""),
                    "certifications": doc.get("certifications", ""),
                    "projects": doc.get("projects", ""),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                })
            return candidates
    except Exception:
        return []


def get_all_candidates_light(search_query: str = None) -> list[dict]:
    """
    Fetch lightweight candidate records without raw_text, deduplicated by email.
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

            projection = {"raw_text": 0}
            _pymongo = _get_pymongo()
            docs = col.find(query, projection).sort("updated_at", _pymongo.DESCENDING)

            candidates = []
            seen_entries = set()
            for doc in docs:
                email = (doc.get("email") or "").strip().lower()
                unique_key = email if email else str(doc.get("_id", ""))
                if unique_key in seen_entries:
                    continue
                seen_entries.add(unique_key)

                candidates.append({
                    "id": str(doc["_id"]),
                    "full_name": doc.get("full_name", ""),
                    "email": doc.get("email", ""),
                    "phone": doc.get("phone", ""),
                    "skills": ", ".join(_normalize_skills_text(doc.get("skills", ""))),
                    "education": doc.get("education", ""),
                    "experience": doc.get("experience", ""),
                    "certifications": doc.get("certifications", ""),
                    "projects": doc.get("projects", ""),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                })
            return candidates
    except Exception:
        return []
