"""File-backed user store (no DB). Token = email; password = SHA-256 hex."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import uuid

from schemas.user import UserResponse, UserRole

USERS_FILE = Path(__file__).resolve().parent / "users.json"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def load_users() -> dict:
    if USERS_FILE.exists():
        with open(USERS_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    return {}


def save_users(users: dict) -> None:
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def record_to_user_response(rec: dict) -> UserResponse:
    created = rec.get("created_at") or datetime.now(timezone.utc).isoformat()
    if isinstance(created, str):
        created_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
    else:
        created_at = datetime.now(timezone.utc)
    return UserResponse(
        id=uuid.UUID(rec["id"]),
        name=str(rec["name"]),
        email=str(rec["email"]).strip().lower(),
        role=UserRole(str(rec["role"])),
        language=str(rec.get("language") or "English"),
        phone=(str(rec["phone"]).strip() if rec.get("phone") else None) or None,
        created_at=created_at,
    )


def user_for_email_token(token: str | None) -> UserResponse | None:
    if not token:
        return None
    email = str(token).strip().lower()
    rec = load_users().get(email)
    if not rec:
        return None
    try:
        return record_to_user_response(rec)
    except Exception:
        return None
