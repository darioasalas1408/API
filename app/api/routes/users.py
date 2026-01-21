from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.auth_deps import require_admin
from app.models.user_crud_models import UserCreateRequest, UserReadModel, UserUpdateRequest
from app.services.user_services import UsersService


router = APIRouter(
    prefix="",
    tags=["users"],
    dependencies=[Depends(require_admin)],  # ✅ Solo admin
)


def _svc(request: Request) -> UsersService:
    svc = request.app.state.users_service
    if svc is None:
        raise HTTPException(status_code=503, detail="Firestore no está configurado. Configurá credenciales de GCP en Vercel.")
    return svc


@router.get("/users", response_model=list[UserReadModel])
def list_users(
    request: Request,
    include_inactive: bool = Query(default=False),
):
    try:
        return _svc(request).list_users(include_inactive=include_inactive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}", response_model=UserReadModel)
def get_user(user_id: str, request: Request):
    try:
        return _svc(request).get_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users", response_model=UserReadModel)
def create_user(body: UserCreateRequest, request: Request):
    try:
        return _svc(request).create_user(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}", response_model=UserReadModel)
def update_user(user_id: str, body: UserUpdateRequest, request: Request):
    try:
        return _svc(request).update_user(user_id, body)
    except ValueError as e:
        # 404 si no existe, 400 si es validación (email repetido)
        msg = str(e)
        if "no encontrado" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}", response_model=dict)
def delete_user(
    user_id: str,
    request: Request,
    hard: bool = Query(default=False),
):
    try:
        return _svc(request).delete_user(user_id, hard=hard)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
