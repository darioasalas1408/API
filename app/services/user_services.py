from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from google.cloud import firestore

from core.config import Settings
from models.user_crud_models import UserCreateRequest, UserReadModel, UserUpdateRequest


try:
    # Es el mismo formato que ya tenés en password_hash: $pbkdf2-sha256$...
    from passlib.hash import pbkdf2_sha256
except Exception as _:
    pbkdf2_sha256 = None


class UsersService:
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger

        self.db = firestore.Client(
            project=settings.gcp_project,
            database=settings.firestore_db,
        )
        self.users_collection = self.db.collection(settings.users_collection)

    # ---------------------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------------------

    def list_users(self, include_inactive: bool = False) -> list[UserReadModel]:
        results: list[UserReadModel] = []
        try:
            for doc in self.users_collection.stream():
                data = doc.to_dict() or {}
                data["id"] = doc.id

                if not include_inactive and data.get("is_active") is False:
                    continue

                results.append(self._to_user_read(data))
            return results
        except Exception as e:
            self.logger.error(f"Error listando usuarios. Error: {str(e)}")
            raise

    def get_user(self, user_id: str) -> UserReadModel:
        doc = self.users_collection.document(user_id).get()
        if not doc.exists:
            raise ValueError(f"Usuario {user_id} no encontrado")

        data = doc.to_dict() or {}
        data["id"] = doc.id
        return self._to_user_read(data)

    def create_user(self, req: UserCreateRequest) -> UserReadModel:
        # Email único (best-effort)
        if self._email_exists(req.email):
            raise ValueError(f"Ya existe un usuario con email {req.email}")

        now = datetime.now(timezone.utc)

        if pbkdf2_sha256 is None:
            raise RuntimeError(
                "passlib no está disponible. Instalá 'passlib' para generar password_hash."
            )

        user_data: dict[str, Any] = {
            "email": str(req.email).strip().lower(),
            "full_name": req.full_name.strip(),
            "role": (req.role or "user").strip(),
            "is_active": bool(req.is_active),
            "password_hash": pbkdf2_sha256.hash(req.password),
            "created_at": now,
            "updated_at": now,
        }

        doc_ref = self.users_collection.document()  # auto id
        doc_ref.set(user_data)

        user_data["id"] = doc_ref.id
        return self._to_user_read(user_data)

    def update_user(self, user_id: str, req: UserUpdateRequest) -> UserReadModel:
        doc_ref = self.users_collection.document(user_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            raise ValueError(f"Usuario {user_id} no encontrado")

        current = snapshot.to_dict() or {}
        updates: dict[str, Any] = {}

        if req.email is not None:
            new_email = str(req.email).strip().lower()
            # Si cambia el email, validar que no exista en otro user
            if new_email != (current.get("email") or "").strip().lower():
                if self._email_exists(new_email, exclude_user_id=user_id):
                    raise ValueError(f"Ya existe un usuario con email {new_email}")
            updates["email"] = new_email

        if req.full_name is not None:
            updates["full_name"] = req.full_name.strip()

        if req.role is not None:
            updates["role"] = req.role.strip()

        if req.is_active is not None:
            updates["is_active"] = bool(req.is_active)

        if req.password is not None:
            if pbkdf2_sha256 is None:
                raise RuntimeError(
                    "passlib no está disponible. Instalá 'passlib' para generar password_hash."
                )
            updates["password_hash"] = pbkdf2_sha256.hash(req.password)

        updates["updated_at"] = datetime.now(timezone.utc)

        if updates:
            doc_ref.update(updates)

        # devolver actualizado
        return self.get_user(user_id)

    def delete_user(self, user_id: str, hard: bool = False) -> dict:
        doc_ref = self.users_collection.document(user_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            raise ValueError(f"Usuario {user_id} no encontrado")

        if hard:
            doc_ref.delete()
            return {"ok": True, "deleted_user_id": user_id, "hard": True}

        # Soft delete: is_active = False
        doc_ref.update(
            {
                "is_active": False,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        return {"ok": True, "deleted_user_id": user_id, "hard": False}

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _to_user_read(self, data: dict[str, Any]) -> UserReadModel:
        # Firestore timestamps suelen venir como datetime; Pydantic los maneja.
        return UserReadModel.model_validate(data)

    def _email_exists(self, email: str, exclude_user_id: Optional[str] = None) -> bool:
        email_norm = str(email).strip().lower()

        try:
            # Firestore new SDK (FieldFilter) / old signature compatibility
            try:
                from google.cloud.firestore_v1.base_query import FieldFilter  # type: ignore
                q = self.users_collection.where(filter=FieldFilter("email", "==", email_norm)).limit(1)
            except Exception:
                q = self.users_collection.where("email", "==", email_norm).limit(1)

            for doc in q.stream():
                if exclude_user_id and doc.id == exclude_user_id:
                    continue
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error validando email existente {email_norm}. Error: {str(e)}")
            # fallback: no bloquear por validación
            return False
