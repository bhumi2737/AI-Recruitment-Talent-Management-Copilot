"""
Database Module for Applications Collection (MongoDB & Offline Fallback)
------------------------------------------------------------------------
Manages job-specific applications for candidates in the ATS.
Each candidate application links candidate_id, job_id, resume_id,
ats_score, recommendation, status, interview_status, interview_score,
and final_decision.
"""

import datetime
import uuid
from typing import Any

from jd_matcher import calculate_candidate_score
from scorer import calculate_ats_score

import offline_storage

APPLICATIONS_COLLECTION = "applications"

# Disk-backed storage fallback for offline / disconnected mode
_OFFLINE_APPLICATIONS: dict[str, dict[str, Any]] = offline_storage.load_offline_data("applications")


def _get_collection():
    try:
        import database as db
        client = db.get_mongo_client()
        database_inst = client[db.MONGO_CONFIG["dbname"]]
        return database_inst[APPLICATIONS_COLLECTION]
    except Exception:
        return None


def clear_applications():
    """Clears in-memory applications cache and test database applications."""
    global _OFFLINE_APPLICATIONS
    _OFFLINE_APPLICATIONS.clear()
    offline_storage.save_offline_data("applications", {})
    col = _get_collection()
    if col is not None:
        try:
            col.delete_many({})
        except Exception:
            pass


def compute_recommendation(ats_score: float) -> str:
    """
    Computes ATS recommendation based on score:
    - >= 80: Highly Recommended
    - >= 65: Recommended
    - >= 50: Needs Improvement
    - < 50: Not Recommended
    """
    score = float(ats_score or 0)
    if score >= 80.0:
        return "Highly Recommended"
    elif score >= 65.0:
        return "Recommended"
    elif score >= 50.0:
        return "Needs Improvement"
    else:
        return "Not Recommended"


def is_eligible_for_interview(recommendation: str, is_overridden: bool = False) -> bool:
    """
    Returns True if application is eligible for interview.
    Highly Recommended, Recommended, and Excellent Match are eligible by default.
    Overridden applications are also eligible.
    """
    if is_overridden:
        return True
    return str(recommendation or "").strip() in ["Highly Recommended", "Recommended", "Excellent Match"]


def _format_doc(doc: dict[str, Any]) -> dict[str, Any]:
    if not doc:
        return doc
    doc_copy = dict(doc)
    if "_id" in doc_copy:
        doc_copy["_id"] = str(doc_copy["_id"])
    if isinstance(doc_copy.get("created_at"), datetime.datetime):
        doc_copy["created_at"] = doc_copy["created_at"].isoformat()
    if isinstance(doc_copy.get("updated_at"), datetime.datetime):
        doc_copy["updated_at"] = doc_copy["updated_at"].isoformat()
    return doc_copy


def create_application(
    candidate_id: str,
    job_id: str,
    resume_id: str = "",
    ats_score: float | None = None,
    recommendation: str | None = None,
    status: str = "Applied",
    interview_status: str = "Not Assigned",
    interview_score: Any = None,
    final_decision: str = "Pending",
    extra_data: dict[str, Any] | None = None
) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Creates a new application record in the applications collection.
    Prevents duplicate applications for the same candidate_id and job_id.
    """
    try:
        cid_str = str(candidate_id or "").strip()
        jid_str = str(job_id or "").strip()

        if not cid_str:
            return False, "Candidate ID is required.", None
        if not jid_str:
            return False, "Job ID is required.", None

        # Check existing
        existing = get_application(cid_str, jid_str)
        if existing:
            return False, f"Candidate has already applied for job {jid_str}.", existing

        app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.datetime.utcnow()

        if ats_score is None:
            ats_score = 0.0
        else:
            ats_score = float(ats_score)

        if recommendation is None:
            recommendation = compute_recommendation(ats_score)

        eligible = is_eligible_for_interview(recommendation, False)
        if status == "Applied" or not status:
            status = "Interview Eligible" if eligible else "Interview Ineligible"

        doc = {
            "application_id": app_id,
            "candidate_id": cid_str,
            "job_id": jid_str,
            "resume_id": str(resume_id or "").strip(),
            "ats_score": round(ats_score, 2),
            "recommendation": recommendation,
            "status": status,
            "interview_status": interview_status or "Not Assigned",
            "interview_score": interview_score,
            "interview_id": (extra_data or {}).get("interview_id", ""),
            "final_decision": final_decision or "Pending",
            "is_overridden": False,
            "override_reason": "",
            "created_at": now,
            "updated_at": now,
        }

        if extra_data:
            for k, v in extra_data.items():
                if k not in doc:
                    doc[k] = v

        col = _get_collection()
        if col is not None:
            try:
                col.insert_one(doc)
            except Exception:
                pass

        _OFFLINE_APPLICATIONS[app_id] = doc
        offline_storage.upsert_offline_record("applications", app_id, doc)
        formatted = _format_doc(doc)
        return True, f"Application submitted successfully. Application ID: {app_id}", formatted
    except Exception as exc:
        return False, f"Failed to create application: {exc}", None


def evaluate_and_apply(candidate: dict[str, Any], job: dict[str, Any]) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Evaluates candidate profile against target job description, calculates ATS score and recommendation,
    and creates the Application record.
    """
    try:
        cand_id = str(candidate.get("candidate_id") or candidate.get("email") or "").strip()
        job_id = str(job.get("job_id") or "").strip()

        if not cand_id or not job_id:
            return False, "Invalid candidate or job information.", None

        existing = get_application(cand_id, job_id)
        if existing:
            # Auto-repair existing applications that have 0.0 ATS score
            if not existing.get("ats_score") or float(existing.get("ats_score", 0)) == 0.0:
                score_data = calculate_candidate_score(candidate, job)
                re_score = float(score_data.get("hiring_score") or score_data.get("overall_score") or score_data.get("ats_score") or 0.0)
                re_rec = score_data.get("recommendation") or compute_recommendation(re_score)
                existing["ats_score"] = re_score
                existing["recommendation"] = re_rec
                update_application(existing.get("application_id"), {"ats_score": re_score, "recommendation": re_rec})
            return True, "Already applied for this job.", existing

        # Calculate ATS score
        score_data = calculate_candidate_score(candidate, job)
        ats_score = float(score_data.get("hiring_score") or score_data.get("overall_score") or score_data.get("ats_score") or 0.0)
        rec_from_matcher = score_data.get("recommendation")
        recommendation = rec_from_matcher if rec_from_matcher else compute_recommendation(ats_score)

        resume_id = candidate.get("resume_hash") or candidate.get("candidate_id") or "RESUME-DEFAULT"

        extra_info = {
            "candidate_name": candidate.get("full_name") or candidate.get("email") or cand_id,
            "candidate_email": candidate.get("email") or "",
            "job_title": job.get("job_title") or job_id,
            "company_name": job.get("company_name") or "",
            "match_breakdown": score_data.get("breakdown", {}),
            "matching_skills": score_data.get("matching_skills", []),
            "missing_skills": score_data.get("missing_skills", []),
        }

        eligible = is_eligible_for_interview(recommendation)
        init_status = "Interview Eligible" if eligible else "Interview Ineligible"

        return create_application(
            candidate_id=cand_id,
            job_id=job_id,
            resume_id=resume_id,
            ats_score=ats_score,
            recommendation=recommendation,
            status=init_status,
            interview_status="Not Assigned",
            interview_score=None,
            final_decision="Pending",
            extra_data=extra_info
        )
    except Exception as exc:
        return False, f"Error evaluating application: {exc}", None


def get_application_by_id(application_id: str) -> dict[str, Any] | None:
    app_id = str(application_id or "").strip()
    try:
        col = _get_collection()
        if col is not None:
            doc = col.find_one({"application_id": app_id})
            if doc:
                return _format_doc(doc)
    except Exception:
        pass

    if app_id in _OFFLINE_APPLICATIONS:
        return _format_doc(_OFFLINE_APPLICATIONS[app_id])
    return None


def get_application(candidate_id: str, job_id: str) -> dict[str, Any] | None:
    cid = str(candidate_id or "").strip()
    jid = str(job_id or "").strip()
    
    # Try resolving candidate email and name for cross-field matching
    cand_email = ""
    cand_name = ""
    try:
        import database as db
        cand_obj = db.get_candidate_by_id(cid)
        if cand_obj:
            cand_email = str(cand_obj.get("email") or "").strip().lower()
            cand_name = str(cand_obj.get("full_name") or "").strip().lower()
    except Exception:
        pass

    try:
        col = _get_collection()
        if col is not None:
            query = {"job_id": jid}
            or_conds = [{"candidate_id": cid}]
            if cand_email:
                or_conds.extend([{"candidate_id": cand_email}, {"candidate_email": cand_email}])
            query["$or"] = or_conds
            doc = col.find_one(query)
            if doc:
                return _format_doc(doc)
    except Exception:
        pass

    for app in _OFFLINE_APPLICATIONS.values():
        app_cid = str(app.get("candidate_id") or "").strip()
        app_cemail = str(app.get("candidate_email") or "").strip().lower()
        app_cname = str(app.get("candidate_name") or "").strip().lower()
        app_jid = str(app.get("job_id") or "").strip()
        
        if app_jid == jid:
            if (app_cid == cid or 
                app_cid.lower() == cid.lower() or
                (app_cemail and cid.lower() == app_cemail) or
                (cand_email and (app_cemail == cand_email or app_cid.lower() == cand_email)) or
                (cand_name and app_cname == cand_name)):
                return _format_doc(app)
    return None


def get_applications_by_candidate(candidate_id: str, candidate_email: str = "") -> list[dict[str, Any]]:
    cid = str(candidate_id or "").strip()
    cemail = str(candidate_email or "").strip().lower()

    if not cemail and cid:
        try:
            import database as db
            cand_obj = db.get_candidate_by_id(cid)
            if cand_obj:
                cemail = str(cand_obj.get("email") or "").strip().lower()
        except Exception:
            pass

    results_map = {}
    try:
        col = _get_collection()
        if col is not None:
            query_or = []
            if cid:
                query_or.append({"candidate_id": cid})
            if cemail:
                query_or.append({"candidate_id": cemail})
                query_or.append({"candidate_email": cemail})
            docs = list(col.find({"$or": query_or}).sort("created_at", -1))
            for doc in docs:
                fmt = _format_doc(doc)
                results_map[fmt["application_id"]] = fmt
    except Exception:
        pass

    for app in _OFFLINE_APPLICATIONS.values():
        app_cid = str(app.get("candidate_id") or "").strip()
        app_cemail = str(app.get("candidate_email") or "").strip().lower()
        if (cid and (app_cid == cid or app_cid.lower() == cid.lower())) or (cemail and (app_cemail == cemail or app_cid.lower() == cemail)):
            fmt = _format_doc(app)
            results_map[fmt["application_id"]] = fmt

    res = list(results_map.values())
    dedup_map = {}
    for a in res:
        jid = a.get("job_id")
        if jid not in dedup_map or str(a.get("created_at") or "") > str(dedup_map[jid].get("created_at") or ""):
            dedup_map[jid] = a
    res = list(dedup_map.values())
    res.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return res


def get_applications_by_job(job_id: str) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    results_map = {}
    try:
        col = _get_collection()
        if col is not None:
            docs = list(col.find({"job_id": jid}).sort("created_at", -1))
            for doc in docs:
                fmt = _format_doc(doc)
                results_map[fmt["application_id"]] = fmt
    except Exception:
        pass

    for app in _OFFLINE_APPLICATIONS.values():
        if str(app.get("job_id") or "").strip() == jid:
            fmt = _format_doc(app)
            results_map[fmt["application_id"]] = fmt

    res = list(results_map.values())
    res.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return res


def get_all_applications() -> list[dict[str, Any]]:
    results_map = {}
    try:
        col = _get_collection()
        if col is not None:
            docs = list(col.find().sort("created_at", -1))
            for doc in docs:
                fmt = _format_doc(doc)
                results_map[fmt["application_id"]] = fmt
    except Exception:
        pass

    for app in _OFFLINE_APPLICATIONS.values():
        fmt = _format_doc(app)
        results_map[fmt["application_id"]] = fmt

    res = list(results_map.values())
    res.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return res


def update_application(application_id: str, update_fields: dict[str, Any]) -> bool:
    app_id = str(application_id or "").strip()
    update_fields["updated_at"] = datetime.datetime.utcnow()

    success = False
    try:
        col = _get_collection()
        if col is not None:
            res = col.update_one({"application_id": app_id}, {"$set": update_fields})
            if res.matched_count > 0:
                success = True
    except Exception:
        pass

    if app_id in _OFFLINE_APPLICATIONS:
        _OFFLINE_APPLICATIONS[app_id].update(update_fields)
        offline_storage.upsert_offline_record("applications", app_id, _OFFLINE_APPLICATIONS[app_id])
        success = True
    else:
        app_doc = get_application_by_id(app_id)
        if app_doc:
            app_doc.update(update_fields)
            _OFFLINE_APPLICATIONS[app_id] = app_doc
            offline_storage.upsert_offline_record("applications", app_id, app_doc)
            success = True

    return success


def override_application_eligibility(application_id: str, recruiter_notes: str = "") -> tuple[bool, str]:
    app_id = str(application_id or "").strip()
    app_doc = get_application_by_id(app_id)
    if not app_doc:
        return False, "Application record not found."

    update_fields = {
        "is_overridden": True,
        "override_reason": recruiter_notes or "Recruiter Override applied.",
        "status": "Interview Eligible (Overridden)",
    }

    ok = update_application(app_id, update_fields)
    if ok:
        return True, "Recruiter override applied successfully. Candidate is now eligible for interview."
    return False, "Failed to apply recruiter override."


def update_application_interview_assignment(
    candidate_id: str,
    job_id: str,
    interview_id: str
) -> bool:
    app_doc = get_application(candidate_id, job_id)
    if app_doc:
        app_id = app_doc["application_id"]
        return update_application(app_id, {
            "interview_id": interview_id,
            "interview_status": "Assigned",
            "status": "Interview Assigned"
        })
    return False


def update_application_interview_submission(
    candidate_id: str,
    job_id: str,
    interview_id: str,
    interview_score: Any = None,
    evaluation_summary: dict[str, Any] | None = None
) -> bool:
    app_doc = get_application(candidate_id, job_id)
    if app_doc:
        app_id = app_doc["application_id"]
        update_data = {
            "interview_status": "Evaluated" if interview_score is not None else "Submitted",
            "status": "Interview Completed" if interview_score is not None else "Interview Submitted",
        }
        if interview_score is not None:
            update_data["interview_score"] = interview_score
        if evaluation_summary:
            update_data["interview_evaluation"] = evaluation_summary

        return update_application(app_id, update_data)
    return False


def set_application_final_decision(
    candidate_id: str,
    job_id: str,
    final_decision: str,
    recruiter_notes: str = ""
) -> tuple[bool, str]:
    cid = str(candidate_id or "").strip()
    jid = str(job_id or "").strip()

    app_doc = get_application(cid, jid)
    if not app_doc:
        try:
            import database, db_jobs
            cand_profile = database.get_candidate_by_id(cid) or {"candidate_id": cid, "email": cid}
            job_doc = db_jobs.get_job_by_id(jid) or {"job_id": jid}
            ok_e, msg_e, app_doc = evaluate_and_apply(cand_profile, job_doc)
        except Exception:
            pass

    if not app_doc:
        return False, "Application record not found for candidate and job."

    app_id = app_doc["application_id"]
    status_map = {
        "Selected": "Selected (Hired)",
        "Hired": "Selected (Hired)",
        "Selected (Hired)": "Selected (Hired)",
        "Rejected": "Rejected",
        "Shortlisted": "Shortlisted",
        "Accepted": "Selected (Hired)"
    }
    new_status = status_map.get(final_decision, final_decision)

    success = update_application(app_id, {
        "final_decision": final_decision,
        "status": new_status,
        "recruiter_notes": recruiter_notes
    })

    if success:
        try:
            import database
            stage_to_set = final_decision if final_decision in database.ALLOWED_RECRUITMENT_STAGES else "Selected"
            database.update_candidate_stage(candidate_id, stage_to_set)
        except Exception:
            pass
        return True, f"Final decision updated to '{final_decision}'."
    return False, "Failed to update final decision."
