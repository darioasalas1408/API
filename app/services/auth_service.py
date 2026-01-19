from __future__ import annotations

from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class AuthService:
    def __init__(self, db, *, session_ttl_hours: int = 8, users_collection: str = "users", sessions_collection: str = "sessions"):
        self.db = db
        self.users = db.collection(users_collection)
        self.sessions = db.collection(sessions_collection)
        self.session_ttl_hours = session_ttl_hours

    def get_user_by_email(self, email: str) -> dict | None:
        docs = list(self.users.where("email", "==", email).limit(1).stream())
        if not docs:
            return None
        doc = docs[0]
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def hash_password(self, plain: str) -> str:
        return pwd_context.hash(plain)

    def create_session(self, user: dict) -> str:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=self.session_ttl_hours)

        doc_ref = self.sessions.document()  # auto id
        doc_ref.set({
            "user_id": user["id"],
            "email": user["email"],
            "role": user.get("role", "user"),
            "created_at": now,
            "expires_at": expires,
        })
        return doc_ref.id

    def get_session(self, session_id: str) -> dict | None:
        doc = self.sessions.document(session_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    def delete_session(self, session_id: str) -> None:
        self.sessions.document(session_id).delete()

    def is_session_expired(self, session: dict) -> bool:
        exp = session.get("expires_at")
        if not exp:
            return False
        return exp < datetime.now(timezone.utc)
