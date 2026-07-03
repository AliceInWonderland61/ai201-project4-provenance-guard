"""
Structured audit log storage for Provenance Guard.

Uses a JSON file as the store for simplicity. Each entry is one submission,
identified by content_id. Appeals update the existing entry rather than
creating a new one.
"""

import json
import os
from datetime import datetime, timezone
from threading import Lock

LOG_PATH = os.path.join(os.path.dirname(__file__), "audit_log.json")
_lock = Lock()  # guards read-modify-write so concurrent requests don't clobber each other


def _read_all() -> list:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _write_all(entries: list) -> None:
    with open(LOG_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def log_submission(content_id: str, creator_id: str, signal_1_score: float,
                    signal_2_score: float, confidence: float, attribution: str,
                    label: str) -> None:
    """Writes a new audit log entry for a fresh submission."""
    entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attribution": attribution,
        "confidence": confidence,
        "signal_1_score": signal_1_score,
        "signal_2_score": signal_2_score,
        "label": label,
        "status": "classified",
        "appeal_reasoning": None,
        "appeal_timestamp": None,
    }
    with _lock:
        entries = _read_all()
        entries.append(entry)
        _write_all(entries)


def log_appeal(content_id: str, creator_reasoning: str) -> dict | None:
    """
    Updates the existing entry for content_id with appeal info.
    Returns the updated entry, or None if content_id wasn't found.
    """
    with _lock:
        entries = _read_all()
        for entry in entries:
            if entry["content_id"] == content_id:
                entry["status"] = "under_review"
                entry["appeal_reasoning"] = creator_reasoning
                entry["appeal_timestamp"] = datetime.now(timezone.utc).isoformat()
                _write_all(entries)
                return entry
        return None


def get_log(limit: int = 20) -> list:
    """Returns the most recent log entries, newest first."""
    entries = _read_all()
    return list(reversed(entries))[:limit]


def get_entry(content_id: str) -> dict | None:
    """Fetches a single entry by content_id."""
    entries = _read_all()
    for entry in entries:
        if entry["content_id"] == content_id:
            return entry
    return None