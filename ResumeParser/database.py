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

import offline_storage

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

# Sync secrets from Streamlit Cloud (st.secrets) to os.environ if available
try:
    import streamlit as _st
    if hasattr(_st, "secrets"):
        for _key in _st.secrets:
            if _key not in os.environ:
                _val = _st.secrets[_key]
                if isinstance(_val, str):
                    os.environ[_key] = _val
except Exception:
    pass

# MongoDB connection settings (override with environment variables)
MONGO_CONFIG = {
    "uri": os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
    "dbname": os.getenv("MONGO_DB", "recruitment_copilot"),
    "collection": os.getenv("MONGO_COLLECTION", "candidates"),
}


class UnclosableClientWrapper:
    def __init__(self, client):
        self._client = client

    def __enter__(self):
        return self._client

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Prevent context managers (with get_mongo_client()) from closing the shared MongoClient connection
        pass

    def __getattr__(self, name):
        return getattr(self._client, name)

    def __getitem__(self, name):
        return self._client[name]


_cached_mongo_client = None

def get_mongo_client(timeout_ms: int = 2000):
    """Create and return a cached MongoClient instance wrapped to prevent premature socket closure."""
    global _cached_mongo_client
    _pymongo = _get_pymongo()

    if _cached_mongo_client is not None:
        try:
            if _cached_mongo_client._topology and not _cached_mongo_client._topology._closed:
                return UnclosableClientWrapper(_cached_mongo_client)
        except Exception:
            pass
        _cached_mongo_client = None

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

    _cached_mongo_client = _pymongo.MongoClient(MONGO_CONFIG["uri"], **kwargs)
    ensure_db_indexes(_cached_mongo_client[MONGO_CONFIG["dbname"]])
    return UnclosableClientWrapper(_cached_mongo_client)


_indexes_created = False

def ensure_db_indexes(database_inst=None):
    """Safely initialize MongoDB indexes on startup if connected."""
    global _indexes_created
    if _indexes_created:
        return
    try:
        if database_inst is None:
            with get_mongo_client() as client:
                database_inst = client[MONGO_CONFIG["dbname"]]
        
        # Candidates collection indexes
        cand_col = database_inst[MONGO_CONFIG["collection"]]
        cand_col.create_index("candidate_id", background=True, sparse=True)
        cand_col.create_index("email", background=True, sparse=True)
        cand_col.create_index("resume_hash", background=True, sparse=True)

        # Applications collection indexes
        app_col = database_inst["applications"]
        app_col.create_index([("candidate_id", 1), ("job_id", 1)], background=True)
        app_col.create_index("application_id", background=True, sparse=True)
        app_col.create_index("status", background=True)
        app_col.create_index("final_decision", background=True)

        # Jobs collection indexes
        job_col = database_inst["jobs"]
        job_col.create_index("job_id", background=True, sparse=True)
        job_col.create_index("status", background=True)

        # Interviews collection indexes
        intv_col = database_inst["interviews"]
        intv_col.create_index("interview_id", background=True, sparse=True)
        intv_col.create_index("candidate_id", background=True)
        intv_col.create_index("job_id", background=True)
        intv_col.create_index("interview_status", background=True)

        # Evaluations collection indexes
        database_inst["interview_evaluations"].create_index("interview_id", background=True)
        database_inst["interview_summaries"].create_index("interview_id", background=True)
        
        # Users collection indexes
        user_col = database_inst["users"]
        user_col.create_index("user_id", background=True, sparse=True)
        user_col.create_index("email", background=True, unique=True, sparse=True)
        
        _indexes_created = True
    except Exception:
        pass


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

            existing_doc = col.find_one(filter_query)
            if existing_doc:
                for k in ["full_name", "phone", "skills", "education", "experience", "certifications", "projects", "raw_text", "source_filename", "source_file_type", "resume_hash", "candidate_id", "user_id", "recruitment_stage", "application_status"]:
                    if (profile.get(k) is None or profile.get(k) == "" or profile.get(k) == []) and existing_doc.get(k):
                        profile[k] = existing_doc.get(k)

            update_doc = {
                "$set": {
                    "full_name": profile.get("full_name", ""),
                    "email": email,
                    "phone": profile.get("phone", ""),
                    "skills": _list_to_text(profile.get("skills")),
                    "education": profile.get("education", ""),
                    "experience": profile.get("experience", ""),
                    "certifications": profile.get("certifications", ""),
                    "projects": profile.get("projects", ""),
                    "raw_text": profile.get("raw_text", ""),
                    "updated_at": datetime.datetime.utcnow(),
                    "source_filename": profile.get("source_filename", ""),
                    "source_file_type": profile.get("source_file_type", ""),
                    "resume_hash": profile.get("resume_hash", resume_hash),
                    "candidate_id": profile.get("candidate_id") or (str(existing_doc.get("_id")) if existing_doc else None),
                    "user_id": profile.get("user_id") or (existing_doc.get("user_id") if existing_doc else None)
                },
                "$setOnInsert": {
                    "created_at": datetime.datetime.utcnow(),
                    "application_status": "Applied",
                    "recruitment_stage": "Applied",
                    "interview_date": "",
                    "interview_time": "",
                    "interviewer_name": "",
                    "recruiter_notes": "",
                    "recruiter_feedback": "",
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
    doc = None
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            ObjectId = _safe_import_objectid()
            if ObjectId is not None:
                try:
                    doc = col.find_one({"_id": ObjectId(candidate_id)})
                except Exception:
                    doc = None
            if not doc:
                doc = col.find_one({"_id": candidate_id})
            if not doc and isinstance(candidate_id, str) and candidate_id.strip():
                doc = col.find_one({"email": candidate_id.strip()})
    except Exception:
        doc = None

    if not doc:
        try:
            off_dict = offline_storage.load_offline_data("candidates")
            cid_str = str(candidate_id or "").strip().lower()
            for k, v in off_dict.items():
                v_id = str(v.get("id") or v.get("_id") or v.get("candidate_id") or "").strip().lower()
                v_email = str(v.get("email") or "").strip().lower()
                v_name = str(v.get("full_name") or "").strip().lower()
                if k.lower() == cid_str or v_id == cid_str or v_email == cid_str or (cid_str and cid_str == v_name):
                    doc = v
                    break
        except Exception:
            pass

    if not doc:
        return None

    skills_val = doc.get("skills", "")
    if isinstance(skills_val, (list, tuple, set)):
        skills_str = ", ".join(_normalize_skills_text(skills_val))
    else:
        skills_str = str(skills_val or "")

    result = {
        "id": str(doc.get("id") or doc.get("_id") or doc.get("email") or candidate_id),
        "candidate_id": str(doc.get("candidate_id") or doc.get("id") or doc.get("_id") or doc.get("email") or candidate_id),
        "full_name": doc.get("full_name", ""),
        "email": doc.get("email", ""),
        "phone": doc.get("phone", ""),
        "skills": skills_str,
        "education": doc.get("education", ""),
        "experience": doc.get("experience", ""),
        "certifications": doc.get("certifications", ""),
        "projects": doc.get("projects", ""),
        "application_status": doc.get("application_status", doc.get("recruitment_stage", "Applied")),
        "recruitment_stage": doc.get("recruitment_stage", "Applied"),
        "interview_date": doc.get("interview_date", ""),
        "interview_time": doc.get("interview_time", ""),
        "interviewer_name": doc.get("interviewer_name", ""),
        "recruiter_notes": doc.get("recruiter_notes", ""),
        "recruiter_feedback": doc.get("recruiter_feedback", ""),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }
    if include_raw_text:
        result["raw_text"] = doc.get("raw_text", "")
    return result


def get_all_candidates(search_query: str = None, include_raw_text: bool = False) -> list[dict]:
    """
    Fetch all candidates from MongoDB, optionally filtered by a search query, falling back to offline storage.
    """
    candidates = []
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
            _pymongo = _get_pymongo()
            docs = col.find(query, projection).sort("updated_at", _pymongo.DESCENDING)
            
            for doc in docs:
                skills_val = doc.get("skills", "")
                skills_str = ", ".join(_normalize_skills_text(skills_val)) if isinstance(skills_val, (list, tuple, set)) else str(skills_val or "")
                c_id = str(doc.get("_id") or doc.get("id") or doc.get("email") or "")
                candidates.append({
                    "id": c_id,
                    "candidate_id": str(doc.get("candidate_id") or c_id),
                    "full_name": doc.get("full_name", ""),
                    "email": doc.get("email", ""),
                    "phone": doc.get("phone", ""),
                    "skills": skills_str,
                    "education": doc.get("education", ""),
                    "experience": doc.get("experience", ""),
                    "certifications": doc.get("certifications", ""),
                    "projects": doc.get("projects", ""),
                    "application_status": doc.get("application_status", doc.get("recruitment_stage", "Applied")),
                    "recruitment_stage": doc.get("recruitment_stage", "Applied"),
                    "interview_date": doc.get("interview_date", ""),
                    "interview_time": doc.get("interview_time", ""),
                    "interviewer_name": doc.get("interviewer_name", ""),
                    "recruiter_notes": doc.get("recruiter_notes", ""),
                    "recruiter_feedback": doc.get("recruiter_feedback", ""),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                })
    except Exception:
        candidates = []

    if not candidates:
        try:
            off_dict = offline_storage.load_offline_data("candidates")
            sq = (search_query or "").strip().lower()
            for k, doc in off_dict.items():
                fname = str(doc.get("full_name") or "")
                femail = str(doc.get("email") or "")
                fskills = str(doc.get("skills") or "")
                fedu = str(doc.get("education") or "")
                fexp = str(doc.get("experience") or "")
                if sq:
                    if sq not in fname.lower() and sq not in femail.lower() and sq not in fskills.lower() and sq not in fedu.lower() and sq not in fexp.lower():
                        continue
                skills_val = doc.get("skills", "")
                skills_str = ", ".join(_normalize_skills_text(skills_val)) if isinstance(skills_val, (list, tuple, set)) else str(skills_val or "")
                c_id = str(doc.get("id") or doc.get("_id") or doc.get("email") or k)
                candidates.append({
                    "id": c_id,
                    "candidate_id": str(doc.get("candidate_id") or c_id),
                    "full_name": fname,
                    "email": femail,
                    "phone": doc.get("phone", ""),
                    "skills": skills_str,
                    "education": fedu,
                    "experience": fexp,
                    "certifications": doc.get("certifications", ""),
                    "projects": doc.get("projects", ""),
                    "application_status": doc.get("application_status", doc.get("recruitment_stage", "Applied")),
                    "recruitment_stage": doc.get("recruitment_stage", "Applied"),
                    "interview_date": doc.get("interview_date", ""),
                    "interview_time": doc.get("interview_time", ""),
                    "interviewer_name": doc.get("interviewer_name", ""),
                    "recruiter_notes": doc.get("recruiter_notes", ""),
                    "recruiter_feedback": doc.get("recruiter_feedback", ""),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                })
        except Exception:
            pass

    return candidates


def get_all_candidates_light(search_query: str = None) -> list[dict]:
    """
    Fetch lightweight candidate records without raw_text, deduplicated by email.
    """
    return get_all_candidates(search_query=search_query, include_raw_text=False)


# ── ATS Candidate Management Helpers ─────────────────────────────────────────

ALLOWED_RECRUITMENT_STAGES = ["Applied", "Screening", "Interview", "Selected", "Selected (Hired)", "Hired", "Shortlisted", "Rejected"]


def _get_candidate_filter(candidate_id: str) -> dict:
    ObjectId = _safe_import_objectid()
    if ObjectId is not None:
        try:
            return {"_id": ObjectId(candidate_id)}
        except Exception:
            pass
    if isinstance(candidate_id, str) and candidate_id.strip():
        if "@" in candidate_id:
            return {"email": candidate_id.strip()}
    return {"_id": candidate_id}


def update_candidate_stage(candidate_id: str, recruitment_stage: str) -> tuple[bool, str]:
    """
    Update recruitment stage for a candidate in MongoDB and offline cache.
    Allowed stages: Applied, Screening, Interview, Selected, Rejected.
    """
    if recruitment_stage not in ALLOWED_RECRUITMENT_STAGES:
        return False, f"Invalid stage '{recruitment_stage}'. Must be one of {ALLOWED_RECRUITMENT_STAGES}."

    cid = str(candidate_id or "").strip()
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            filter_query = _get_candidate_filter(cid)

            update_doc = {
                "$set": {
                    "recruitment_stage": recruitment_stage,
                    "application_status": recruitment_stage,
                    "updated_at": datetime.datetime.utcnow(),
                }
            }
            res = col.update_one(filter_query, update_doc)
    except Exception:
        pass

    try:
        import offline_storage
        cand_doc = get_candidate_by_id(cid)
        if cand_doc:
            cand_doc["recruitment_stage"] = recruitment_stage
            cand_doc["application_status"] = recruitment_stage
            offline_storage.upsert_offline_record("candidates", cid, cand_doc)
            return True, f"Recruitment stage updated to '{recruitment_stage}'."
    except Exception:
        pass

    return True, f"Recruitment stage updated to '{recruitment_stage}'."


def update_candidate_interview(candidate_id: str, interview_date: str, interview_time: str, interviewer_name: str) -> tuple[bool, str]:
    """
    Schedule/update interview details for a candidate in MongoDB.
    Validation: interview_date cannot be before today, interview_time cannot be empty.
    """
    if not interview_time or not str(interview_time).strip():
        return False, "Interview time cannot be empty."

    # Validate date
    if interview_date:
        try:
            if isinstance(interview_date, str):
                parsed_date = datetime.datetime.strptime(interview_date, "%Y-%m-%d").date()
            else:
                parsed_date = interview_date
            today = datetime.date.today()
            if parsed_date < today:
                return False, "Interview date cannot be before today's date."
            interview_date_str = str(parsed_date)
        except ValueError:
            return False, "Invalid date format. Expected YYYY-MM-DD."
    else:
        return False, "Interview date is required."

    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            filter_query = _get_candidate_filter(candidate_id)

            update_doc = {
                "$set": {
                    "interview_date": interview_date_str,
                    "interview_time": str(interview_time).strip(),
                    "interviewer_name": str(interviewer_name or "").strip(),
                    "updated_at": datetime.datetime.utcnow(),
                }
            }
            res = col.update_one(filter_query, update_doc)
            if res.matched_count > 0:
                return True, "Interview schedule saved successfully."
            return False, "Candidate not found."
    except Exception as exc:
        return False, f"Failed to update interview schedule: {exc}"


def update_candidate_notes(candidate_id: str, recruiter_notes: str) -> tuple[bool, str]:
    """
    Save internal recruiter notes for a candidate in MongoDB.
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            filter_query = _get_candidate_filter(candidate_id)

            update_doc = {
                "$set": {
                    "recruiter_notes": str(recruiter_notes or "").strip(),
                    "updated_at": datetime.datetime.utcnow(),
                }
            }
            res = col.update_one(filter_query, update_doc)
            if res.matched_count > 0:
                return True, "Recruiter notes saved successfully."
            return False, "Candidate not found."
    except Exception as exc:
        return False, f"Failed to save recruiter notes: {exc}"


def update_candidate_feedback(candidate_id: str, recruiter_feedback: str) -> tuple[bool, str]:
    """
    Save recruiter feedback for a candidate in MongoDB.
    """
    try:
        with get_mongo_client() as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            filter_query = _get_candidate_filter(candidate_id)

            update_doc = {
                "$set": {
                    "recruiter_feedback": str(recruiter_feedback or "").strip(),
                    "updated_at": datetime.datetime.utcnow(),
                }
            }
            res = col.update_one(filter_query, update_doc)
            if res.matched_count > 0:
                return True, "Recruiter feedback saved successfully."
            return False, "Candidate not found."
    except Exception as exc:
        return False, f"Failed to save recruiter feedback: {exc}"


def get_candidate_stage_counts() -> dict[str, int]:
    """
    Aggregates and returns the candidate count per recruitment stage from MongoDB.
    Returns dict: {'Total': X, 'Applied': A, 'Screening': S, 'Interview': I, 'Selected': SEL, 'Rejected': R}
    """
    counts = {stage: 0 for stage in ALLOWED_RECRUITMENT_STAGES}
    counts["Total"] = 0
    try:
        with get_mongo_client(timeout_ms=2000) as client:
            db = client[MONGO_CONFIG["dbname"]]
            col = db[MONGO_CONFIG["collection"]]
            docs = list(col.find({}, {"recruitment_stage": 1, "email": 1, "phone": 1}))

            seen_keys = set()
            for doc in docs:
                email = (doc.get("email") or "").strip().lower()
                phone = (doc.get("phone") or "").strip()
                key = email or phone or str(doc.get("_id"))
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                stage = doc.get("recruitment_stage", "Applied")
                if stage not in counts:
                    stage = "Applied"
                counts[stage] += 1
                counts["Total"] += 1

            return counts
    except Exception:
        return counts


AUDIT_LOGS_COLLECTION = "audit_logs"

def log_audit_event(user_email: str, user_name: str, user_role: str, action: str, entity: str, status: str = "Success", details: str = "") -> None:
    """
    Record an audit trail event in MongoDB (or offline storage fallback).
    """
    log_id = f"LOG-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(2).hex()}"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "log_id": log_id,
        "timestamp": timestamp,
        "user_email": (user_email or "system@copilot.ai").strip().lower(),
        "user_name": (user_name or "System").strip(),
        "user_role": (user_role or "System").strip(),
        "action": action,
        "entity": entity,
        "status": status,
        "details": details,
        "created_at": datetime.datetime.utcnow().isoformat()
    }

    try:
        with get_mongo_client(timeout_ms=1500) as client:
            db_inst = client[MONGO_CONFIG["dbname"]]
            col = db_inst[AUDIT_LOGS_COLLECTION]
            col.insert_one(entry.copy())
    except Exception:
        offline_storage.upsert_offline_record(AUDIT_LOGS_COLLECTION, log_id, entry)


def get_audit_logs(limit: int = 100) -> list[dict[str, Any]]:
    """
    Retrieve audit trail log entries sorted by timestamp descending.
    """
    logs = []
    try:
        with get_mongo_client(timeout_ms=1500) as client:
            db_inst = client[MONGO_CONFIG["dbname"]]
            col = db_inst[AUDIT_LOGS_COLLECTION]
            cursor = col.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
            logs = list(cursor)
    except Exception:
        raw_offline = offline_storage.get_all_offline_records(AUDIT_LOGS_COLLECTION)
        raw_offline.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
        logs = raw_offline[:limit]

    return logs


def get_system_health_metrics() -> dict[str, Any]:
    """
    Inspects actual database records and returns a recruitment health summary with diagnostic metrics.
    """
    issues = []
    
    # 1. Inspect Jobs
    all_jobs = []
    try:
        import db_jobs
        all_jobs = db_jobs.get_all_jobs()
    except Exception:
        pass

    jds_no_desc = [j for j in all_jobs if not (j.get("job_description") or "").strip()]
    jds_no_skills = [j for j in all_jobs if not j.get("required_skills")]
    
    if jds_no_desc:
        issues.append({"level": "Needs Attention", "category": "Job Descriptions", "message": f"{len(jds_no_desc)} Job Requisition(s) missing full job description text."})
    if jds_no_skills:
        issues.append({"level": "Needs Attention", "category": "Job Descriptions", "message": f"{len(jds_no_skills)} Job Requisition(s) missing required skill tags."})

    # 2. Inspect Candidates
    all_candidates = get_all_candidates()
    cands_no_skills = [c for c in all_candidates if not c.get("skills")]
    cands_no_contact = [c for c in all_candidates if not c.get("email") and not c.get("phone")]

    if cands_no_skills:
        issues.append({"level": "Needs Attention", "category": "Candidates", "message": f"{len(cands_no_skills)} Candidate Profile(s) missing extracted skills."})
    if cands_no_contact:
        issues.append({"level": "Critical", "category": "Candidates", "message": f"{len(cands_no_contact)} Candidate Profile(s) missing both email and phone contact info."})

    # Check candidate email duplicates
    emails = [c.get("email").strip().lower() for c in all_candidates if c.get("email")]
    dup_emails = len(emails) - len(set(emails))
    if dup_emails > 0:
        issues.append({"level": "Needs Attention", "category": "Candidates", "message": f"Detected {dup_emails} duplicate candidate email record(s)."})

    # 3. Inspect Applications across JDs
    all_apps = []
    try:
        import db_applications
        all_apps = db_applications.get_all_applications()
    except Exception:
        pass

    jds_with_apps = {a.get("job_id") for a in all_apps if a.get("job_id")}
    jds_no_apps = [j for j in all_jobs if j.get("job_id") not in jds_with_apps]
    if jds_no_apps:
        issues.append({"level": "Needs Attention", "category": "Applications", "message": f"{len(jds_no_apps)} Active Job Requisition(s) have 0 received applications."})

    # Overall Status Calculation
    critical_count = sum(1 for i in issues if i["level"] == "Critical")
    attention_count = sum(1 for i in issues if i["level"] == "Needs Attention")

    if critical_count > 0:
        overall_status = "Critical"
    elif attention_count > 0:
        overall_status = "Needs Attention"
    else:
        overall_status = "Healthy"

    return {
        "status": overall_status,
        "issues": issues,
        "total_jobs": len(all_jobs),
        "total_candidates": len(all_candidates),
        "total_applications": len(all_apps),
        "issues_count": len(issues)
    }


