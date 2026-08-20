"""
Database Module for User Authentication
----------------------------------------
Handles MongoDB operations and offline JSON fallback for user accounts.
"""

import datetime
import uuid
from typing import Any

import database as db
import offline_storage

COLLECTION_NAME = "users"


def create_user(user_data: dict[str, Any]) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Create a new user account in MongoDB or offline cache.
    user_data must contain: email, full_name, password_hash, role (optional)
    """
    email = user_data.get("email", "").strip().lower()
    full_name = user_data.get("full_name", "").strip()
    password_hash = user_data.get("password_hash", "")
    role = user_data.get("role", "admin").strip().lower()

    if not email or not full_name or not password_hash:
        return False, "Full Name, Email, and Password are required.", None

    existing_user = get_user_by_email(email)
    if existing_user:
        return False, "An account with this email address already exists.", None

    user_id = user_data.get("user_id") or f"USR-{uuid.uuid4().hex[:8].upper()}"
    candidate_id = user_data.get("candidate_id") or (user_id if role == "candidate" else "")
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    record = {
        "user_id": user_id,
        "candidate_id": candidate_id,
        "email": email,
        "full_name": full_name,
        "password_hash": password_hash,
        "role": role,
        "created_at": user_data.get("created_at") or now_iso,
        "updated_at": now_iso
    }

    try:
        with db.get_mongo_client() as client:
            database_inst = client[db.MONGO_CONFIG["dbname"]]
            database_inst[COLLECTION_NAME].insert_one(record.copy())
            offline_storage.upsert_offline_record(COLLECTION_NAME, user_id, record)
            sanitized = record.copy()
            sanitized.pop("_id", None)
            return True, "User registered successfully.", sanitized
    except Exception:
        # Fallback to offline storage
        offline_storage.upsert_offline_record(COLLECTION_NAME, user_id, record)
        return True, "User registered successfully (offline mode).", record


def update_user_candidate_link(user_id: str, candidate_id: str) -> bool:
    """Link candidate_id to an existing user_id record."""
    if not user_id or not candidate_id:
        return False
    try:
        with db.get_mongo_client() as client:
            database_inst = client[db.MONGO_CONFIG["dbname"]]
            database_inst[COLLECTION_NAME].update_one(
                {"user_id": user_id},
                {"$set": {"candidate_id": candidate_id, "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
            )
    except Exception:
        pass

    user = get_user_by_id(user_id)
    if user:
        user["candidate_id"] = candidate_id
        offline_storage.upsert_offline_record(COLLECTION_NAME, user_id, user)
        return True
    return False


def get_user_by_email(email: str) -> dict[str, Any] | None:
    """Fetch user record by email address (case-insensitive)."""
    clean_email = (email or "").strip().lower()
    if not clean_email:
        return None

    try:
        with db.get_mongo_client() as client:
            database_inst = client[db.MONGO_CONFIG["dbname"]]
            doc = database_inst[COLLECTION_NAME].find_one({"email": clean_email})
            if doc:
                doc.pop("_id", None)
                return doc
    except Exception:
        pass

    # Fallback to offline cache
    offline_users = offline_storage.get_all_offline_records(COLLECTION_NAME)
    for user in offline_users:
        if user.get("email", "").lower() == clean_email:
            return user
    return None


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Fetch user record by user_id."""
    clean_id = (user_id or "").strip()
    if not clean_id:
        return None

    try:
        with db.get_mongo_client() as client:
            database_inst = client[db.MONGO_CONFIG["dbname"]]
            doc = database_inst[COLLECTION_NAME].find_one({"user_id": clean_id})
            if doc:
                doc.pop("_id", None)
                return doc
    except Exception:
        pass

    offline_users = offline_storage.get_all_offline_records(COLLECTION_NAME)
    for user in offline_users:
        if user.get("user_id") == clean_id:
            return user
    return None


def list_users() -> list[dict[str, Any]]:
    """List all registered users."""
    try:
        with db.get_mongo_client() as client:
            database_inst = client[db.MONGO_CONFIG["dbname"]]
            docs = list(database_inst[COLLECTION_NAME].find({}))
            for d in docs:
                d.pop("_id", None)
            return docs
    except Exception:
        return offline_storage.get_all_offline_records(COLLECTION_NAME)


def update_user_status(user_id: str, is_active: bool) -> tuple[bool, str]:
    """Activate or deactivate a user account."""
    if not user_id:
        return False, "User ID is required."
    try:
        with db.get_mongo_client() as client:
            database_inst = client[db.MONGO_CONFIG["dbname"]]
            database_inst[COLLECTION_NAME].update_one(
                {"user_id": user_id},
                {"$set": {"is_active": is_active, "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
            )
    except Exception:
        pass

    user = get_user_by_id(user_id)
    if user:
        user["is_active"] = is_active
        user["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        offline_storage.upsert_offline_record(COLLECTION_NAME, user_id, user)
        status_text = "Activated" if is_active else "Deactivated"
        return True, f"User account {status_text} successfully."
    return False, "User not found."


def update_user_role(user_id: str, new_role: str) -> tuple[bool, str]:
    """Update role for a user account."""
    clean_role = (new_role or "").strip().lower()
    if clean_role not in ["admin", "recruiter", "candidate"]:
        return False, "Invalid role specified."

    try:
        with db.get_mongo_client() as client:
            database_inst = client[db.MONGO_CONFIG["dbname"]]
            database_inst[COLLECTION_NAME].update_one(
                {"user_id": user_id},
                {"$set": {"role": clean_role, "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
            )
    except Exception:
        pass

    user = get_user_by_id(user_id)
    if user:
        user["role"] = clean_role
        user["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        offline_storage.upsert_offline_record(COLLECTION_NAME, user_id, user)
        return True, f"User role updated to '{clean_role.capitalize()}'."
    return False, "User not found."

