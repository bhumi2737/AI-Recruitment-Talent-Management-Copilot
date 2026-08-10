"""
Database module for Interview Assignment & Candidate Interview Responses (MongoDB & Persistent Offline Fallback)
---------------------------------------------------------------------------------------------------------------
Handles creating assignments, tracking drafts, storing submitted responses, and fetching recruiter reports.
Works seamlessly online (MongoDB) and offline (Disk JSON cache), persisting all assignments across app restarts.
"""

import datetime
import uuid
from typing import Any
import database as db
import offline_storage

_OFFLINE_INTERVIEWS: dict[str, dict[str, Any]] = offline_storage.load_offline_data("interviews")
_OFFLINE_RESPONSES: dict[str, list[dict[str, Any]]] = offline_storage.load_offline_data("responses")


def _get_collection(col_name: str):
    client = db.get_mongo_client()
    database_inst = client[db.MONGO_CONFIG["dbname"]]
    return database_inst[col_name]


def generate_job_interview_questions(job_data: dict[str, Any]) -> list[str]:
    """
    Generates relevant technical and situational interview questions based on job title & required skills.
    """
    job_title = job_data.get("job_title", "Software Engineer")
    skills = job_data.get("required_skills", [])
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    questions = [
        f"Please introduce yourself and explain why your experience makes you a strong fit for the {job_title} position.",
        f"Describe a challenging project you worked on recently. What was your specific role and how did you measure success?",
    ]

    for skill in skills[:4]:
        questions.append(
            f"How do you utilize {skill} in your daily engineering workflow? Describe a practical scenario where you solved a key technical problem using {skill}."
        )

    questions.append(
        "Describe a situation where you had to handle tight project deadlines or conflicting priorities. How did you manage your time and communicate progress?"
    )

    return questions[:6]


def create_interview_assignment(
    candidate_id: str,
    job_id: str,
    questions: list[str],
    due_date: str,
    recruiter_id: str = "recruiter_admin",
    question_source: str = "Recruiter Question Set",
    question_set_id: str = "",
    duration_minutes: int = 30,
    voice_enabled: bool = True,
    allow_ai_followup: bool = True
) -> tuple[bool, str, str | None]:
    """
    Insert a new interview assignment into MongoDB 'interviews' collection and offline cache.
    Status values: 'Assigned', 'In Progress', 'Submitted', 'Evaluated'
    """
    try:
        if not candidate_id or not str(candidate_id).strip():
            return False, "Candidate selection is required.", None
        if not job_id or not str(job_id).strip():
            return False, "Job selection is required.", None
        if not questions and question_source != "Fully AI Generated":
            return False, "At least one interview question is required.", None

        cand_doc = db.get_candidate_by_id(candidate_id) or {}
        cand_email = cand_doc.get("email", "") or (candidate_id if "@" in str(candidate_id) else "")

        interview_id = f"INTV-{uuid.uuid4().hex[:8].upper()}"
        doc = {
            "interview_id": interview_id,
            "candidate_id": str(candidate_id).strip(),
            "candidate_email": str(cand_email).strip().lower(),
            "recruiter_id": str(recruiter_id).strip(),
            "job_id": str(job_id).strip(),
            "generated_questions": questions or ["Tell me about your background and experience."],
            "question_source": str(question_source or "Recruiter Question Set"),
            "question_set_id": str(question_set_id or ""),
            "duration_minutes": int(duration_minutes or 30),
            "voice_enabled": bool(voice_enabled),
            "allow_ai_followup": bool(allow_ai_followup),
            "assigned_date": datetime.datetime.utcnow().isoformat(),
            "due_date": str(due_date or "").strip(),
            "interview_status": "Assigned",
            "draft_answers": {},
            "conversation_history": [],
            "messages": [],
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }

        try:
            col = _get_collection("interviews")
            col.insert_one(dict(doc))
        except Exception:
            pass

        _OFFLINE_INTERVIEWS[interview_id] = doc
        offline_storage.upsert_offline_record("interviews", interview_id, doc)

        # Update candidate's recruitment stage to 'Interview' in DB
        try:
            db.update_candidate_stage(candidate_id, "Interview")
        except Exception:
            pass

        # Sync application status in applications collection
        try:
            import db_applications
            db_applications.update_application_interview_assignment(candidate_id, job_id, interview_id)
        except Exception:
            pass

        return True, f"Interview assigned successfully. Assignment ID: {interview_id}", interview_id
    except Exception as exc:
        return False, f"Failed to create interview assignment: {exc}", None


def get_interviews_by_candidate(candidate_id: str, candidate_email: str = "") -> list[dict]:
    """
    Fetch all assigned/submitted interviews for a given candidate matching by candidate_id or email.
    """
    cid_str = str(candidate_id or "").strip()
    email_str = str(candidate_email or "").strip().lower()

    try:
        col = _get_collection("interviews")
        _pymongo = db._get_pymongo()

        or_conds = []
        if cid_str:
            or_conds.append({"candidate_id": cid_str})
            or_conds.append({"candidate_id": cid_str.lower()})
            or_conds.append({"candidate_email": cid_str.lower()})
        if email_str:
            or_conds.append({"candidate_id": email_str})
            or_conds.append({"candidate_email": email_str})

        query = {"$or": or_conds} if or_conds else {}
        docs = list(col.find(query, {"_id": 0}).sort("assigned_date", _pymongo.DESCENDING))
        if docs:
            return docs
    except Exception:
        pass

    results = []
    for intv in _OFFLINE_INTERVIEWS.values():
        c_id = str(intv.get("candidate_id") or "").strip()
        c_email = str(intv.get("candidate_email") or "").strip().lower()
        if (cid_str and (c_id == cid_str or c_id.lower() == cid_str.lower() or c_email == cid_str.lower())) or \
           (email_str and (c_id.lower() == email_str or c_email == email_str)):
            results.append(dict(intv))

    results.sort(key=lambda x: str(x.get("assigned_date") or ""), reverse=True)
    return results


def get_interview_by_id(interview_id: str) -> dict | None:
    """
    Fetch single interview assignment by interview_id.
    """
    iid = str(interview_id or "").strip()
    try:
        col = _get_collection("interviews")
        doc = col.find_one({"interview_id": iid}, {"_id": 0})
        if doc:
            return doc
    except Exception:
        pass

    if iid in _OFFLINE_INTERVIEWS:
        return dict(_OFFLINE_INTERVIEWS[iid])
    return None


def update_interview_draft_answers(
    interview_id: str,
    draft_answers: dict[str, str],
    status: str = "In Progress"
) -> tuple[bool, str]:
    """
    Auto-save candidate's draft answers and update status to 'In Progress'.
    """
    iid = str(interview_id or "").strip()
    now_iso = datetime.datetime.utcnow().isoformat()

    try:
        col = _get_collection("interviews")
        update_doc = {
            "$set": {
                "draft_answers": draft_answers or {},
                "interview_status": status,
                "updated_at": datetime.datetime.utcnow(),
            }
        }
        res = col.update_one({"interview_id": iid}, update_doc)
    except Exception:
        pass

    if iid in _OFFLINE_INTERVIEWS:
        _OFFLINE_INTERVIEWS[iid]["draft_answers"] = draft_answers or {}
        _OFFLINE_INTERVIEWS[iid]["interview_status"] = status
        _OFFLINE_INTERVIEWS[iid]["updated_at"] = now_iso
        offline_storage.upsert_offline_record("interviews", iid, _OFFLINE_INTERVIEWS[iid])
        return True, "Draft saved successfully."
    
    intv = get_interview_by_id(iid)
    if intv:
        intv["draft_answers"] = draft_answers or {}
        intv["interview_status"] = status
        intv["updated_at"] = now_iso
        _OFFLINE_INTERVIEWS[iid] = intv
        offline_storage.upsert_offline_record("interviews", iid, intv)
        return True, "Draft saved successfully."

    return False, "Interview assignment not found."


def submit_interview_responses(
    interview_id: str,
    candidate_id: str,
    job_id: str,
    responses_list: list[dict[str, str]]
) -> tuple[bool, str]:
    """
    Save final submitted interview answers to 'interview_responses' collection and set status to 'Submitted'.
    responses_list is a list of dicts: [{'question': '...', 'answer': '...'}]
    """
    iid = str(interview_id or "").strip()
    if not responses_list:
        return False, "Cannot submit empty responses."

    intv = get_interview_by_id(iid)
    if not intv:
        return False, "Interview assignment not found."

    if intv.get("interview_status") == "Submitted":
        return False, "Interview has already been submitted and is read-only."

    submission_time = datetime.datetime.utcnow().isoformat()
    response_docs = []
    for idx, item in enumerate(responses_list):
        res_id = f"RESP-{uuid.uuid4().hex[:8].upper()}"
        response_docs.append({
            "response_id": res_id,
            "interview_id": iid,
            "candidate_id": str(candidate_id),
            "job_id": str(job_id),
            "question": item.get("question", ""),
            "answer": item.get("answer", ""),
            "submitted_time": submission_time,
            "question_order": idx + 1,
        })

    try:
        resp_col = _get_collection("interview_responses")
        if response_docs:
            resp_col.insert_many([dict(r) for r in response_docs])
    except Exception:
        pass

    _OFFLINE_RESPONSES[iid] = response_docs
    offline_storage.upsert_offline_record("responses", iid, response_docs)

    draft_dict = {str(idx): item.get("answer", "") for idx, item in enumerate(responses_list)}
    
    try:
        intv_col = _get_collection("interviews")
        intv_col.update_one(
            {"interview_id": iid},
            {
                "$set": {
                    "interview_status": "Submitted",
                    "draft_answers": draft_dict,
                    "submitted_time": datetime.datetime.utcnow(),
                    "updated_at": datetime.datetime.utcnow(),
                }
            }
        )
    except Exception:
        pass

    if iid in _OFFLINE_INTERVIEWS:
        _OFFLINE_INTERVIEWS[iid]["interview_status"] = "Submitted"
        _OFFLINE_INTERVIEWS[iid]["draft_answers"] = draft_dict
        _OFFLINE_INTERVIEWS[iid]["submitted_time"] = submission_time
        _OFFLINE_INTERVIEWS[iid]["updated_at"] = submission_time
        offline_storage.upsert_offline_record("interviews", iid, _OFFLINE_INTERVIEWS[iid])
    else:
        intv["interview_status"] = "Submitted"
        intv["draft_answers"] = draft_dict
        intv["submitted_time"] = submission_time
        intv["updated_at"] = submission_time
        _OFFLINE_INTERVIEWS[iid] = intv
        offline_storage.upsert_offline_record("interviews", iid, intv)

    try:
        import db_applications
        db_applications.update_application_interview_submission(str(candidate_id), str(job_id), iid)
    except Exception:
        pass

    return True, "Interview responses submitted successfully."


def get_submitted_interviews() -> list[dict]:
    """
    Fetch all submitted interviews for recruiter view.
    """
    try:
        col = _get_collection("interviews")
        _pymongo = db._get_pymongo()
        query = {"interview_status": {"$in": ["Submitted", "Evaluated"]}}
        docs = list(col.find(query, {"_id": 0}).sort("updated_at", _pymongo.DESCENDING))
        if docs:
            return docs
    except Exception:
        pass

    results = [i for i in _OFFLINE_INTERVIEWS.values() if i.get("interview_status") in ["Submitted", "Evaluated"]]
    results.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    return results


def get_responses_by_interview(interview_id: str) -> list[dict]:
    """
    Fetch all Q&A responses for a specific interview_id.
    """
    iid = str(interview_id or "").strip()
    try:
        col = _get_collection("interview_responses")
        _pymongo = db._get_pymongo()
        docs = list(col.find({"interview_id": iid}, {"_id": 0}).sort("question_order", _pymongo.ASCENDING))
        if docs:
            return docs
    except Exception:
        pass

    if iid in _OFFLINE_RESPONSES:
        return _OFFLINE_RESPONSES[iid]

    intv = get_interview_by_id(iid)
    if intv and intv.get("conversation_history"):
        history = intv.get("conversation_history", [])
        return [
            {
                "interview_id": iid,
                "question": turn.get("question", ""),
                "answer": turn.get("answer", ""),
                "ai_reasoning": turn.get("ai_reasoning", ""),
                "question_order": idx + 1
            }
            for idx, turn in enumerate(history)
        ]
    return []


def append_conversational_turn(
    interview_id: str,
    question: str,
    answer: str,
    ai_reasoning: str = ""
) -> tuple[bool, str]:
    """
    Appends a turn (question, answer, timestamp, ai_reasoning) to the interview's conversation_history.
    """
    iid = str(interview_id or "").strip()
    now_iso = datetime.datetime.utcnow().isoformat()
    turn_doc = {
        "question": str(question or "").strip(),
        "answer": str(answer or "").strip(),
        "timestamp": now_iso,
        "ai_reasoning": str(ai_reasoning or "").strip(),
    }

    try:
        col = _get_collection("interviews")
        col.update_one(
            {"interview_id": iid},
            {
                "$push": {"conversation_history": turn_doc},
                "$set": {
                    "interview_status": "In Progress",
                    "updated_at": datetime.datetime.utcnow()
                }
            }
        )
    except Exception:
        pass

    if iid not in _OFFLINE_INTERVIEWS:
        intv = get_interview_by_id(iid) or {"interview_id": iid, "conversation_history": [], "messages": []}
        _OFFLINE_INTERVIEWS[iid] = intv

    if "conversation_history" not in _OFFLINE_INTERVIEWS[iid]:
        _OFFLINE_INTERVIEWS[iid]["conversation_history"] = []

    _OFFLINE_INTERVIEWS[iid]["conversation_history"].append(turn_doc)
    _OFFLINE_INTERVIEWS[iid]["interview_status"] = "In Progress"
    _OFFLINE_INTERVIEWS[iid]["updated_at"] = now_iso
    offline_storage.upsert_offline_record("interviews", iid, _OFFLINE_INTERVIEWS[iid])

    return True, "Turn appended successfully."


def get_conversational_turns(interview_id: str) -> list[dict]:
    """
    Retrieves stored conversation history turns for a given interview.
    """
    intv = get_interview_by_id(interview_id)
    if intv:
        return intv.get("conversation_history", [])
    return []


def append_chat_message(
    interview_id: str,
    sender: str,
    message_text: str,
    is_voice: bool = False,
    ai_reasoning: str = ""
) -> tuple[bool, str, dict]:
    """
    Appends a message document to the interview document's 'messages' array.
    """
    iid = str(interview_id or "").strip()
    now_iso = datetime.datetime.utcnow().isoformat()
    msg_id = f"MSG-{uuid.uuid4().hex[:8].upper()}"
    msg_doc = {
        "message_id": msg_id,
        "interview_id": iid,
        "sender": str(sender or "AI").strip(),
        "message_text": str(message_text or "").strip(),
        "timestamp": now_iso,
        "is_voice": bool(is_voice),
        "ai_reasoning": str(ai_reasoning or "").strip(),
    }

    try:
        col = _get_collection("interviews")
        col.update_one(
            {"interview_id": iid},
            {
                "$push": {"messages": msg_doc},
                "$set": {
                    "interview_status": "In Progress",
                    "updated_at": datetime.datetime.utcnow()
                }
            }
        )
    except Exception:
        pass

    if iid not in _OFFLINE_INTERVIEWS:
        intv = get_interview_by_id(iid) or {"interview_id": iid, "conversation_history": [], "messages": []}
        _OFFLINE_INTERVIEWS[iid] = intv

    if "messages" not in _OFFLINE_INTERVIEWS[iid]:
        _OFFLINE_INTERVIEWS[iid]["messages"] = []

    _OFFLINE_INTERVIEWS[iid]["messages"].append(msg_doc)
    _OFFLINE_INTERVIEWS[iid]["interview_status"] = "In Progress"
    _OFFLINE_INTERVIEWS[iid]["updated_at"] = now_iso
    offline_storage.upsert_offline_record("interviews", iid, _OFFLINE_INTERVIEWS[iid])

    return True, "Message appended successfully.", msg_doc


def get_interview_messages(interview_id: str) -> list[dict]:
    """
    Retrieves all stored chat messages for an interview_id.
    """
    intv = get_interview_by_id(interview_id)
    if intv and intv.get("messages"):
        return intv.get("messages", [])
    return []
