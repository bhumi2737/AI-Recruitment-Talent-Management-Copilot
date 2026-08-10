"""
Database helper module for MongoDB InterviewQuestionSet collection (interview_question_sets)
-----------------------------------------------------------------------------------------
Handles saving, updating, and loading recruiter AI-generated question sets.
"""

import datetime
import uuid
from typing import Any
import database as db


def _get_collection(col_name: str = "interview_question_sets"):
    client = db.get_mongo_client()
    database_inst = client[db.MONGO_CONFIG["dbname"]]
    return database_inst[col_name]


def save_question_set(
    candidate_id: str,
    job_id: str,
    questions: list[dict[str, Any]],
    difficulty: str = "Mixed",
    created_by: str = "recruiter_admin",
    status: str = "Draft"
) -> tuple[bool, str, str | None]:
    """
    Saves a generated interview question set into MongoDB 'interview_question_sets' collection.
    """
    try:
        if not candidate_id or not str(candidate_id).strip():
            return False, "Candidate selection is required.", None
        if not job_id or not str(job_id).strip():
            return False, "Job description selection is required.", None
        if not questions:
            return False, "At least one question is required in the question set.", None

        qset_id = f"QSET-{uuid.uuid4().hex[:8].upper()}"
        col = _get_collection("interview_question_sets")

        doc = {
            "question_set_id": qset_id,
            "candidate_id": str(candidate_id).strip(),
            "job_id": str(job_id).strip(),
            "generated_questions": questions,
            "difficulty": difficulty,
            "created_at": datetime.datetime.utcnow(),
            "created_by": str(created_by).strip(),
            "status": str(status or "Draft").strip(),
            "updated_at": datetime.datetime.utcnow(),
        }

        col.insert_one(doc)
        return True, f"Interview Question Set saved successfully. Set ID: {qset_id}", qset_id
    except Exception as exc:
        return False, f"Failed to save question set: {exc}", None


def get_question_set_by_id(question_set_id: str) -> dict | None:
    """
    Fetches a single Question Set by question_set_id.
    """
    try:
        col = _get_collection("interview_question_sets")
        doc = col.find_one({"question_set_id": str(question_set_id)}, {"_id": 0})
        return doc
    except Exception:
        return None


def get_question_sets_by_candidate(candidate_id: str) -> list[dict]:
    """
    Fetches all Question Sets generated for a candidate.
    """
    try:
        col = _get_collection("interview_question_sets")
        _pymongo = db._get_pymongo()
        query = {"candidate_id": str(candidate_id)}
        docs = list(col.find(query, {"_id": 0}).sort("created_at", _pymongo.DESCENDING))
        return docs
    except Exception:
        return []


def update_question_set(
    question_set_id: str,
    questions: list[dict[str, Any]],
    status: str = "Draft"
) -> tuple[bool, str]:
    """
    Updates an existing Question Set in MongoDB.
    """
    try:
        col = _get_collection("interview_question_sets")
        update_doc = {
            "$set": {
                "generated_questions": questions,
                "status": status,
                "updated_at": datetime.datetime.utcnow(),
            }
        }
        res = col.update_one({"question_set_id": str(question_set_id)}, update_doc)
        if res.matched_count > 0:
            return True, "Question Set updated successfully."
        return False, "Question Set not found."
    except Exception as exc:
        return False, f"Failed to update Question Set: {exc}"
