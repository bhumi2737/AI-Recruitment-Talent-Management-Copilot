import datetime
import re
import os
import io
import mimetypes
from typing import Optional, Tuple
from html import escape

import streamlit as st
import database as db

RATE_LIMITS = {
    "signup_ip": {"limit": 5, "window_seconds": 3600},
    "login_ip": {"limit": 10, "window_seconds": 900},
    "resume_upload_user": {"limit": 10, "window_seconds": 3600},
    "ai_request_user": {"limit": 20, "window_seconds": 3600}
}

class RateLimiter:
    @staticmethod
    def _cleanup_expired(collection, action_type: str, window_seconds: int):
        """Remove expired rate limit entries."""
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=window_seconds)
        try:
            collection.delete_many({"action": action_type, "timestamp": {"$lt": cutoff.isoformat()}})
        except Exception:
            pass

    @staticmethod
    def check_rate_limit(action_type: str, identifier: str) -> Tuple[bool, str]:
        """
        Check if the action by identifier exceeds the configured rate limit.
        Returns (is_allowed, error_message).
        """
        if action_type not in RATE_LIMITS:
            return True, ""
            
        limit_config = RATE_LIMITS[action_type]
        limit = int(os.getenv(f"RATE_LIMIT_{action_type.upper()}", limit_config["limit"]))
        window = limit_config["window_seconds"]
        
        try:
            with db.get_mongo_client() as client:
                database_inst = client[db.MONGO_CONFIG["dbname"]]
                col = database_inst["security_rate_limits"]
                
                # Cleanup old entries first (simple garbage collection)
                RateLimiter._cleanup_expired(col, action_type, window)
                
                # Count recent attempts
                cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=window)
                count = col.count_documents({
                    "action": action_type,
                    "identifier": identifier,
                    "timestamp": {"$gte": cutoff.isoformat()}
                })
                
                if count >= limit:
                    return False, f"Rate limit exceeded. Please try again later."
                
                # Log the new attempt
                col.insert_one({
                    "action": action_type,
                    "identifier": identifier,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                })
                
                return True, ""
        except Exception as e:
            # Fail open if DB is down, to avoid breaking the app completely
            return True, ""


def get_client_ip() -> str:
    """Extract client IP securely, failing gracefully if Streamlit internals change."""
    # Try modern Streamlit context (Streamlit >= 1.30)
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            forwarded = headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
            real_ip = headers.get("X-Real-IP")
            if real_ip:
                return real_ip.strip()
    except Exception:
        pass
        
    # Try legacy ScriptRunContext safely
    try:
        from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx is not None:
            # In older Streamlit versions, headers might be attached here in some third-party hacks,
            # but usually it's just best to return localhost if we get here.
            pass
    except ImportError:
        pass
    except Exception:
        pass
        
    return "127.0.0.1"


def sanitize_input(text: str, max_length: int = 500) -> str:
    """Sanitize user input to prevent XSS and limit length."""
    if not isinstance(text, str):
        return ""
    # HTML escape and truncate
    clean = escape(text.strip())[:max_length]
    return clean


def validate_file_security(uploaded_file, max_size_mb: int = 5) -> Tuple[bool, str]:
    """
    Validate file upload security:
    1. Size check
    2. Magic bytes check
    """
    if uploaded_file is None:
        return False, "No file uploaded."
        
    # Check size
    file_bytes = uploaded_file.getvalue()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"File exceeds {max_size_mb}MB limit."
        
    # Magic bytes check for PDF and DOCX
    header = file_bytes[:4]
    
    # PDF magic bytes: %PDF
    if header == b"%PDF":
        return True, "pdf"
        
    # ZIP magic bytes (DOCX is a zip file): PK\x03\x04
    if header == b"PK\x03\x04":
        return True, "docx"
        
    return False, "Invalid file format. Only actual PDF or DOCX files are allowed."
