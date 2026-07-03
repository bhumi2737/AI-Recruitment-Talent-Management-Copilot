"""
Database Module
---------------
Handles PostgreSQL connection and candidate data storage using psycopg.
Gracefully handles connection failures so the app can still run offline.
"""

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

# Database connection settings (override with environment variables)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "recruitment_copilot"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}


def get_connection():
    """Create and return a new PostgreSQL connection."""
    conn_string = (
        f"host={DB_CONFIG['host']} "
        f"port={DB_CONFIG['port']} "
        f"dbname={DB_CONFIG['dbname']} "
        f"user={DB_CONFIG['user']} "
        f"password={DB_CONFIG['password']}"
    )
    return psycopg.connect(conn_string, row_factory=dict_row)


def test_connection() -> tuple[bool, str]:
    """
    Test whether the database is reachable.
    Returns (success: bool, message: str).
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True, "Connected to PostgreSQL"
    except Exception as exc:
        return False, f"Database unavailable: {exc}"


def _list_to_text(value: list | str | None) -> str:
    """Convert a list (e.g. skills) to a comma-separated string for storage."""
    if isinstance(value, list):
        return ", ".join(value)
    return value or ""


def save_candidate(profile: dict[str, Any]) -> tuple[bool, str, int | None]:
    """
    Insert a parsed candidate profile into the database.
    Returns (success, message, candidate_id).
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO candidates (
                        full_name, email, phone, skills, education,
                        experience, certifications, projects, raw_text
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        profile.get("full_name", ""),
                        profile.get("email", ""),
                        profile.get("phone", ""),
                        _list_to_text(profile.get("skills")),
                        profile.get("education", ""),
                        profile.get("experience", ""),
                        profile.get("certifications", ""),
                        profile.get("projects", ""),
                        profile.get("raw_text", ""),
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                return True, "Candidate saved successfully", row["id"]
    except Exception as exc:
        return False, f"Failed to save candidate: {exc}", None


def get_recent_candidates(limit: int = 10) -> tuple[list[dict], str | None]:
    """
    Fetch the most recently added candidates.
    Returns (candidates_list, error_message).
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, full_name, email, phone, skills, created_at
                    FROM candidates
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                return rows, None
    except Exception as exc:
        return [], str(exc)


def get_candidate_count() -> int:
    """Return total number of candidates in the database."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS count FROM candidates")
                row = cur.fetchone()
                return row["count"] if row else 0
    except Exception:
        return 0
