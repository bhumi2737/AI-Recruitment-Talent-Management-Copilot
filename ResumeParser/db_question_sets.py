"""
Question Sets Database & Persistence Module
-------------------------------------------
Manages recruiter-created reusable interview question sets.
Supports primary MongoDB storage with transparent offline disk fallback.
"""

import datetime
import uuid
from typing import Any
import database
import offline_storage

_OFFLINE_QUESTION_SETS: dict[str, dict[str, Any]] = offline_storage.load_offline_data("question_sets")


def _format_doc(doc: dict[str, Any]) -> dict[str, Any]:
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def save_question_set(
    set_name: str,
    job_id: str,
    questions: list[dict[str, Any]],
    job_title: str = ""
) -> tuple[bool, str, str]:
    """
    Saves or updates a recruiter question set.
    Returns (success: bool, message: str, set_id: str).
    """
    s_name = str(set_name or "").strip()
    j_id = str(job_id or "").strip()
    if not s_name:
        return False, "Question Set name is required.", ""
    if not questions:
        return False, "At least one question is required to save a Question Set.", ""

    set_id = f"QSET-{uuid.uuid4().hex[:8].upper()}"
    now_iso = datetime.datetime.utcnow().isoformat()

    # Format questions list with clean IDs and ordering
    formatted_questions = []
    for idx, q in enumerate(questions):
        if isinstance(q, str):
            q_text = q
            diff = "Intermediate"
            cat = "Technical"
            skill = "General"
        else:
            q_text = q.get("question", "")
            diff = q.get("difficulty", "Intermediate")
            cat = q.get("category", "Technical")
            skill = q.get("expected_skill", "General")

        formatted_questions.append({
            "question_id": f"Q-{idx+1}",
            "question": q_text,
            "difficulty": diff,
            "category": cat,
            "expected_skill": skill,
            "order": idx + 1
        })

    record = {
        "set_id": set_id,
        "set_name": s_name,
        "job_id": j_id,
        "job_title": job_title or j_id,
        "questions": formatted_questions,
        "question_count": len(formatted_questions),
        "created_at": now_iso,
        "updated_at": now_iso
    }

    # Save to MongoDB
    mongo_success = False
    try:
        with database.get_mongo_client() as client:
            db = client[database.MONGO_CONFIG["dbname"]]
            col = db["question_sets"]
            col.insert_one(dict(record))
            mongo_success = True
    except Exception as exc:
        print(f"[Warning] Mongo save failed for question_set ({exc}). Saving offline.")

    # Save to offline cache
    _OFFLINE_QUESTION_SETS[set_id] = record
    offline_storage.upsert_offline_record("question_sets", set_id, record)

    return True, f"Question Set '{s_name}' saved successfully ({len(formatted_questions)} questions).", set_id


def get_all_question_sets(job_id: str | None = None) -> list[dict[str, Any]]:
    """Retrieve all saved question sets, optionally filtered by job_id."""
    records_dict = {}

    # Read from MongoDB
    try:
        with database.get_mongo_client() as client:
            db = client[database.MONGO_CONFIG["dbname"]]
            col = db["question_sets"]
            query = {"job_id": job_id} if job_id else {}
            for doc in col.find(query):
                f_doc = _format_doc(doc)
                sid = f_doc.get("set_id")
                if sid:
                    records_dict[sid] = f_doc
    except Exception:
        pass

    # Read offline records
    offline_data = offline_storage.load_offline_data("question_sets")
    for sid, rec in offline_data.items():
        if job_id:
            if rec.get("job_id") == job_id:
                records_dict[sid] = rec
        else:
            records_dict[sid] = rec

    results = list(records_dict.values())
    results.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    return results


def get_question_set_by_id(set_id: str) -> dict[str, Any] | None:
    """Retrieve a specific question set by set_id."""
    sid = str(set_id or "").strip()
    if not sid:
        return None

    # Check MongoDB
    try:
        with database.get_mongo_client() as client:
            db = client[database.MONGO_CONFIG["dbname"]]
            col = db["question_sets"]
            doc = col.find_one({"set_id": sid})
            if doc:
                return _format_doc(doc)
    except Exception:
        pass

    # Fallback to offline cache
    offline_data = offline_storage.load_offline_data("question_sets")
    if sid in offline_data:
        return offline_data[sid]

    return None


def delete_question_set(set_id: str) -> tuple[bool, str]:
    """Deletes a question set by set_id."""
    sid = str(set_id or "").strip()
    if not sid:
        return False, "Invalid set ID."

    try:
        with database.get_mongo_client() as client:
            db = client[database.MONGO_CONFIG["dbname"]]
            col = db["question_sets"]
            col.delete_one({"set_id": sid})
    except Exception:
        pass

    offline_data = offline_storage.load_offline_data("question_sets")
    if sid in offline_data:
        del offline_data[sid]
        offline_storage.save_offline_data("question_sets", offline_data)
        if sid in _OFFLINE_QUESTION_SETS:
            del _OFFLINE_QUESTION_SETS[sid]

    return True, f"Question Set '{sid}' deleted."
