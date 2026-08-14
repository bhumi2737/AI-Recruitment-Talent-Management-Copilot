"""
Offline JSON Storage Fallback Module
------------------------------------
Provides disk-backed JSON persistence when MongoDB is unreachable.
Ensures candidates, applications, jobs, and interviews persist across app restarts.
"""

import json
import os
from typing import Any

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".offline_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _get_filepath(collection_name: str) -> str:
    return os.path.join(CACHE_DIR, f"{collection_name}.json")


def load_offline_data(collection_name: str) -> dict[str, Any]:
    """Load JSON records dictionary from disk."""
    filepath = _get_filepath(collection_name)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_offline_data(collection_name: str, data: dict[str, Any]) -> None:
    """Save JSON records dictionary to disk."""
    filepath = _get_filepath(collection_name)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as exc:
        print(f"[Warning] Failed to save offline cache for {collection_name}: {exc}")


def upsert_offline_record(collection_name: str, key: str, record: dict[str, Any]) -> None:
    """Upsert a single record into the offline JSON file, preserving existing fields if new fields are empty."""
    data = load_offline_data(collection_name)
    existing = data.get(key)
    if existing and isinstance(existing, dict) and isinstance(record, dict):
        merged = existing.copy()
        for k, v in record.items():
            if v is not None and v != "" and v != []:
                merged[k] = v
            elif k not in merged:
                merged[k] = v
        data[key] = merged
    else:
        data[key] = record
    save_offline_data(collection_name, data)


def get_all_offline_records(collection_name: str) -> list[dict[str, Any]]:
    """Return list of all records stored in offline JSON file."""
    data = load_offline_data(collection_name)
    return list(data.values())
