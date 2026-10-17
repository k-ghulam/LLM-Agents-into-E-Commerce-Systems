"""Opaque, revocable bearer sessions. Client-provided email is never identity."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException
from .database import users_collection, sessions_collection


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(user: dict) -> str:
    token = secrets.token_urlsafe(32)
    sessions_collection.insert_one({
        "token_hash": token_digest(token),
        "user_id": user["_id"],
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=8),
    })
    return token


def session_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in required")
    token = authorization[7:]
    if not 32 <= len(token) <= 128:
        raise HTTPException(401, "Invalid session")
    return token


def current_user(token: str = Depends(session_token)) -> dict:
    session = sessions_collection.find_one({
        "token_hash": token_digest(token),
        "expires_at": {"$gt": datetime.now(timezone.utc)},
    })
    user = users_collection.find_one({"_id": session["user_id"]}) if session else None
    if not user:
        raise HTTPException(401, "Session expired; sign in again")
    return user


def require_owner(email: str, user: dict) -> str:
    if email.strip().lower() != user["email"]:
        raise HTTPException(403, "Account access denied")
    return user["email"]


def is_admin(email: str | None) -> bool:
    user = users_collection.find_one({"email": email}) if email else None
    return bool(user and user.get("is_admin"))


def require_admin(user: dict = Depends(current_user)) -> str:
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin access required")
    return user["email"]
