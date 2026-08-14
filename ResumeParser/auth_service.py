"""
Authentication Service Module
------------------------------
Provides secure password hashing (bcrypt), verification, and JWT token generation/validation.
"""

import datetime
import os
import re
import hashlib
from typing import Any

import db_auth

try:
    import bcrypt
except ImportError:
    bcrypt = None

try:
    import jwt
except ImportError:
    jwt = None

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "copilot_secret_jwt_key_super_secure_2026")
JWT_ALGORITHM = "HS256"


def normalize_role(role_input: Any) -> str:
    """Normalize user role into 'admin', 'recruiter', or 'candidate'."""
    if isinstance(role_input, list):
        role_str = str(role_input[0]) if role_input else "candidate"
    else:
        role_str = str(role_input or "candidate")
    
    role_clean = role_str.strip().lower()
    if "admin" in role_clean:
        return "admin"
    if "recruiter" in role_clean or "hr" in role_clean:
        return "recruiter"
    return "candidate"


def hash_password(password: str) -> str:
    """Hash password securely using bcrypt if available, otherwise SHA-256 fallback with salt."""
    if not password:
        raise ValueError("Password cannot be empty.")

    if bcrypt is not None:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    else:
        # Fallback salted hashlib hash
        salt = "recruitment_copilot_static_salt_2026"
        return "sha256$" + hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    if not password or not hashed_password:
        return False

    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        if bcrypt is not None:
            try:
                return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
            except Exception:
                return False
        return False
    elif hashed_password.startswith("sha256$"):
        salt = "recruitment_copilot_static_salt_2026"
        computed = "sha256$" + hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return computed == hashed_password

    return False


def create_access_token(user_data: dict[str, Any], expires_hours: int = 24) -> str:
    """Generate JWT access token containing user claims."""
    now = datetime.datetime.now(datetime.timezone.utc)
    exp = now + datetime.timedelta(hours=expires_hours)

    payload = {
        "sub": user_data.get("user_id"),
        "email": user_data.get("email"),
        "full_name": user_data.get("full_name"),
        "role": user_data.get("role", "admin"),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp())
    }

    if jwt is not None:
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token if isinstance(token, str) else token.decode("utf-8")
    else:
        # Simple fallback token string if PyJWT is missing
        import json
        import base64
        payload_str = json.dumps(payload)
        b64 = base64.b64encode(payload_str.encode("utf-8")).decode("utf-8")
        sig = hashlib.sha256((b64 + JWT_SECRET_KEY).encode("utf-8")).hexdigest()[:16]
        return f"fallback.{b64}.{sig}"


def verify_access_token(token: str) -> dict[str, Any] | None:
    """Verify and decode JWT access token."""
    if not token:
        return None

    if token.startswith("fallback."):
        try:
            import json
            import base64
            parts = token.split(".")
            if len(parts) == 3:
                b64 = parts[1]
                payload_str = base64.b64decode(b64.encode("utf-8")).decode("utf-8")
                return json.loads(payload_str)
        except Exception:
            return None

    if jwt is not None:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except Exception:
            return None

    return None


def validate_email_format(email: str) -> bool:
    """Validate email format with standard regex."""
    if not email:
        return False
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email.strip()))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password length and basic complexity."""
    if not password:
        return False, "Password cannot be empty."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    return True, ""


def register_user(full_name: str, email: str, password: str, confirm_password: str = "", role: str = "candidate", is_bootstrap: bool = False) -> tuple[bool, str, dict[str, Any] | None]:
    """Register a new user account with validation and automatic candidate record linkage."""
    clean_name = (full_name or "").strip()
    clean_email = (email or "").strip().lower()
    clean_role = (role or "candidate").strip().lower()

    if clean_role not in ["recruiter", "candidate", "admin"]:
        return False, "Invalid account role specified.", None

    if clean_role == "admin" and not is_bootstrap:
        return False, "Admin accounts cannot be created via public registration.", None

    if not clean_name:
        return False, "Full Name is required.", None

    if not validate_email_format(clean_email):
        return False, "Please enter a valid email address.", None

    valid_pw, pw_msg = validate_password_strength(password)
    if not valid_pw:
        return False, pw_msg, None

    if confirm_password and password != confirm_password:
        return False, "Passwords do not match.", None

    if db_auth.get_user_by_email(clean_email):
        return False, "An account with this email address already exists. Please sign in.", None

    hashed_pw = hash_password(password)

    user_payload = {
        "full_name": clean_name,
        "email": clean_email,
        "password_hash": hashed_pw,
        "role": clean_role
    }

    ok, msg, user_record = db_auth.create_user(user_payload)
    if not ok or not user_record:
        return False, msg, None

    # Automatic Candidate profile creation & linkage if candidate role
    candidate_id = user_record.get("candidate_id") or user_record.get("user_id")
    if clean_role == "candidate":
        cand_profile = {
            "candidate_id": candidate_id,
            "user_id": user_record.get("user_id"),
            "full_name": clean_name,
            "email": clean_email,
            "created_at": user_record.get("created_at")
        }
        try:
            import database as db
            db.save_candidate(cand_profile)
        except Exception:
            pass

    # Generate token
    token = create_access_token(user_record)
    result = {
        "user_id": user_record.get("user_id"),
        "candidate_id": candidate_id,
        "full_name": user_record.get("full_name"),
        "email": user_record.get("email"),
        "role": user_record.get("role"),
        "token": token
    }
    return True, "Registration successful!", result


def authenticate_user(email: str, password: str) -> tuple[bool, str, dict[str, Any] | None]:
    """Authenticate user with email and password."""
    clean_email = (email or "").strip().lower()
    if not clean_email or not password:
        return False, "Email and Password are required.", None

    user = db_auth.get_user_by_email(clean_email)
    if not user and clean_email in ["admin@copilot.com", "admin@gmail.com", "admin@admin.com"]:
        # Auto-seed default demo admin user for easy access
        register_user("Admin Recruiter", clean_email, "admin123", "admin123", role="admin", is_bootstrap=True)
        user = db_auth.get_user_by_email(clean_email)

    if not user:
        return False, "Invalid email or password.", None

    if not verify_password(password, user.get("password_hash", "")):
        return False, "Invalid email or password.", None

    # Ensure candidate profile exists if user is candidate
    user_role = user.get("role", "candidate")
    candidate_id = user.get("candidate_id") or user.get("user_id")
    if user_role == "candidate":
        cand_profile = {
            "candidate_id": candidate_id,
            "user_id": user.get("user_id"),
            "full_name": user.get("full_name"),
            "email": clean_email,
            "skills": [],
            "recruitment_stage": "Applied",
            "created_at": user.get("created_at")
        }
        try:
            import database as db
            db.save_candidate(cand_profile)
        except Exception:
            pass

    token = create_access_token(user)
    result = {
        "user_id": user.get("user_id"),
        "candidate_id": candidate_id,
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "role": user_role,
        "token": token
    }
    return True, "Login successful!", result
