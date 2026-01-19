from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from core.auth_deps import get_current_user
from models.auth_models import LoginRequest, LoginResponse, MeResponse
from services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(request: Request) -> AuthService:
    settings = request.app.state.settings
    db = request.app.state.firestore
    return AuthService(db, session_ttl_hours=settings.session_ttl_hours)


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request, response: Response):
    settings = request.app.state.settings
    auth = get_auth_service(request)

    user = auth.get_user_by_email(body.email)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not auth.verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    session_id = auth.create_session(user)

    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=True,
        secure=False,      # True en HTTPS
        samesite="lax",    # si front y api son dominios distintos + https, usar "none"
        max_age=60 * 60 * settings.session_ttl_hours,
        path="/",
    )

    return LoginResponse(role=user.get("role", "user"))


@router.post("/logout")
def logout(request: Request, response: Response):
    settings = request.app.state.settings
    auth = get_auth_service(request)

    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        auth.delete_session(session_id)

    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(request: Request, user: dict = Depends(get_current_user)):
    auth = get_auth_service(request)

    db_user = auth.get_user_by_email(user["email"])
    if not db_user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return MeResponse(
        email=db_user["email"],
        full_name=db_user.get("full_name", ""),
        role=db_user.get("role", "user"),
        id=db_user["id"]
    )
