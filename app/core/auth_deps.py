from __future__ import annotations

from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Request

from services.auth_service import AuthService


def get_auth_service(request: Request) -> AuthService:
    settings = request.app.state.settings
    db = request.app.state.firestore
    return AuthService(db, session_ttl_hours=settings.session_ttl_hours)


def get_current_user(request: Request, auth: AuthService = Depends(get_auth_service)) -> dict:
    cookie_name = request.app.state.settings.session_cookie_name
    session_id = request.cookies.get(cookie_name)

    if not session_id:
        raise HTTPException(status_code=401, detail="No autenticado")

    sess = auth.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=401, detail="Sesión inválida")

    if auth.is_session_expired(sess):
        auth.delete_session(session_id)
        raise HTTPException(status_code=401, detail="Sesión expirada")

    return {
        "user_id": sess.get("user_id"),
        "email": sess.get("email"),
        "role": sess.get("role", "user"),
        "session_id": session_id,
    }


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Requiere rol admin")
    return user
