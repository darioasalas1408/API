import json
import logging
from typing import List, Optional, Tuple

from google.cloud import firestore
from models.core_models import Project
from core.config import Settings
from models.project_responses import ProjectWithUserResponse


class ProjectsService:
    """Administra la persistencia y consulta del estado de Proyectos en Firestore."""

    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger

        self.db = firestore.Client(
            project=settings.gcp_project,
            database=settings.firestore_db,
        )
        self.projects_collection = self.db.collection(settings.projects_collection)

    def create_project(self, project: Project) -> None:
        try:
            validated_project = Project.model_validate(project)
            # Validar que el usuario exista (y esté activo)
            self._ensure_user_exists(validated_project.user_id)

            self.projects_collection.document(validated_project.id).set(
                validated_project.model_dump(mode="python")
            )
        except Exception as e:
            self.logger.error(
                f"{getattr(project, 'id', '')} | Error al crear el proyecto. Error: {str(e)}"
            )
            raise

    # Mantengo tu método original (update solo del nombre) por compatibilidad
    def update_project(
        self,
        project_id: str,
        project_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Actualiza campos del proyecto en Firestore.

        - project_name: si viene, actualiza 'name'
        - user_id: si viene, valida que el usuario exista y actualiza 'user_id'
        """
        try:
            doc_ref = self.projects_collection.document(project_id)
            snapshot = doc_ref.get()

            if not snapshot.exists:
                raise ValueError(f"Proyecto {project_id} no existe en Firestore")

            current_data = snapshot.to_dict()
            if current_data is None:
                raise ValueError(f"Proyecto {project_id} no tiene datos")

            if isinstance(current_data, str):
                try:
                    current_data = json.loads(current_data)
                except json.JSONDecodeError:
                    pass

            project = Project.model_validate(current_data)
            new_data = project.model_dump(mode="python")

            if project_name is not None:
                new_data["name"] = project_name

            if user_id is not None:
                self._ensure_user_exists(user_id)
                new_data["user_id"] = user_id

            doc_ref.set(new_data)
            self.logger.info(f"{project_id} | Proyecto actualizado en Firestore")
        except Exception as e:
            self.logger.error(
                f"{project_id} | Error al modificar el proyecto. Error: {str(e)}"
            )
            raise

    # Nuevo: delete
    def delete_project(self, project_id: str) -> None:
        try:
            doc_ref = self.projects_collection.document(project_id)
            snapshot = doc_ref.get()
            if not snapshot.exists:
                raise ValueError(f"Proyecto {project_id} no existe en Firestore")

            doc_ref.delete()
            self.logger.info(f"{project_id} | Proyecto eliminado en Firestore")
        except Exception as e:
            self.logger.error(
                f"{project_id} | Error al eliminar el proyecto. Error: {str(e)}"
            )
            raise

    def get_project(self, project_id: str) -> ProjectWithUserResponse:
        try:
            doc = self.projects_collection.document(project_id).get()
            doc_dict = doc.to_dict()

            if doc_dict is None:
                raise ValueError(f"{project_id} | Proyecto no encontrado")

            if isinstance(doc_dict, str):
                try:
                    doc_dict = json.loads(doc_dict)
                except json.JSONDecodeError:
                    pass

            doc_dict.setdefault("id", doc.id)
            project = Project.model_validate(doc_dict)

            user_id = getattr(project, "user_id", "") or ""
            user_email, user_full_name = self._get_user_info(user_id)

            return ProjectWithUserResponse(
                project=project,
                user_email=user_email,
                user_full_name=user_full_name,
            )

        except Exception as e:
            self.logger.error(
                f"{project_id} | Error al encontrar el proyecto. Error: {str(e)}"
            )
            raise

    def list_projects(self, project_id: Optional[str] = None) -> List[ProjectWithUserResponse]:
        results: List[ProjectWithUserResponse] = []

        try:
            docs = self.projects_collection.stream()

            # cache: user_id -> (email, full_name)
            user_cache: dict[str, Tuple[str, str]] = {}

            for doc in docs:
                project_dict = doc.to_dict()
                if project_dict is None:
                    continue

                if isinstance(project_dict, str):
                    try:
                        project_dict = json.loads(project_dict)
                    except json.JSONDecodeError:
                        pass

                project_dict.setdefault("id", doc.id)
                project = Project.model_validate(project_dict)

                user_id = getattr(project, "user_id", "") or ""
                if user_id in user_cache:
                    user_email, user_full_name = user_cache[user_id]
                else:
                    user_email, user_full_name = self._get_user_info(user_id)
                    user_cache[user_id] = (user_email, user_full_name)

                results.append(
                    ProjectWithUserResponse(
                        project=project,
                        user_email=user_email,
                        user_full_name=user_full_name,
                    )
                )

        except Exception as e:
            self.logger.error(f"{project_id or ''} | Error al listar proyectos. Error: {str(e)}")
            raise

        return results

    def list_projects_by_user_id(self, user_id: str) -> list[ProjectWithUserResponse]:
        results: list[ProjectWithUserResponse] = []

        try:
            # Validar usuario y obtener info (email/full_name)
            user_doc = self.db.collection(self.settings.users_collection).document(user_id).get()
            if not user_doc.exists:
                raise ValueError(f"Usuario {user_id} no encontrado")

            user_data = user_doc.to_dict() or {}
            email = (user_data.get("email") or "").strip()
            full_name = (user_data.get("full_name") or "").strip()

            docs = self.projects_collection.where("user_id", "==", user_id).stream()

            for doc in docs:
                project_dict = doc.to_dict()
                if project_dict is None:
                    continue

                if isinstance(project_dict, str):
                    try:
                        project_dict = json.loads(project_dict)
                    except json.JSONDecodeError:
                        pass

                project_dict.setdefault("id", doc.id)
                project = Project.model_validate(project_dict)

                results.append(
                    ProjectWithUserResponse(
                        project=project,
                        user_email=email,
                        user_full_name=full_name,
                    )
                )

        except Exception as e:
            self.logger.error(
                f"{user_id} | Error al listar proyectos por usuario. Error: {str(e)}"
            )
            raise

        return results

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _ensure_user_exists(self, user_id: str) -> None:
        """Valida que el usuario exista en users_collection (y esté activo)."""
        if not user_id:
            raise ValueError("user_id es requerido")

        doc = self.db.collection(self.settings.users_collection).document(user_id).get()
        if not doc.exists:
            raise ValueError(f"Usuario {user_id} no encontrado")

        data = doc.to_dict() or {}
        if data.get("is_active") is False:
            raise ValueError(f"Usuario {user_id} está inactivo")

    def _get_user_info(self, user_id: str) -> Tuple[str, str]:
        """Devuelve (email, full_name) desde users_collection."""
        if not user_id:
            return "", ""

        try:
            doc = self.db.collection(self.settings.users_collection).document(user_id).get()
            if not doc.exists:
                return "", ""

            data = doc.to_dict() or {}
            email = (data.get("email") or "").strip()
            full_name = (data.get("full_name") or "").strip()
            return email, full_name

        except Exception as e:
            self.logger.error(f"{user_id} | Error leyendo user info. Error: {str(e)}")
            return "", ""
