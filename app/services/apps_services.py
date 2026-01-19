from datetime import datetime
from typing import Any, Optional
import hashlib
import json
import logging
import uuid
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from models.core_models import Application, Module, Repo
from core.config import Settings

class AppsService:
    """Administra la persistencia y consulta del estado de jobs en Firestore."""

    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        """Inicializa el cliente de Firestore y la colección de apps."""
        self.settings = settings
        self.logger = logger

        self.db = firestore.Client(
            project=settings.gcp_project,
            database=settings.firestore_db,
        )
        self.apps_collection = self.db.collection(settings.apps_collection)

    def create_app(self, app: Application) -> None:
        try:
            validated_app = Application.model_validate(app)
            if validated_app.id is None:
                validated_app.id = uuid.uuid4()
                
            self.apps_collection.document(validated_app.id).set(
                validated_app.model_dump(mode="python")
            )
            try:
                projects_col = self.db.collection(self.settings.projects_collection)
                projects_col.document(validated_app.project_id).update(
                    {"applications": firestore.ArrayUnion([validated_app.id])}
                )
                self.logger.info(
                    f"{validated_app.id} | App asociada al proyecto {validated_app.project_id}"
                )
            except Exception as inner_e:
                self.logger.error(
                    f"{validated_app.id} | No se pudo asociar la app al proyecto {validated_app.project_id}. Error: {str(inner_e)}"
                )
                raise
        except Exception as e:
            self.logger.error(f"{app.id} | Error al crear la app. Error: {str(e)}")
            raise

    def create_module(self, app_id, module: Module):
        try:
            validated_module = Module.model_validate(module)
            app = self.get_app(app_id)

            # Evitar duplicados por nombre (se usa como identificador)
            if any(m.name == validated_module.name for m in app.modules):
                raise ValueError(
                    f"{app_id} | El módulo '{validated_module.name}' ya existe en la app"
                )

            app.modules.append(validated_module)
            self.apps_collection.document(app.id).set(app.model_dump(mode="python"))
            self.logger.info(f"{app.id} | Módulo '{validated_module.name}' agregado")
        except Exception as e:
            self.logger.error(f"{app_id} | Error al agregar módulo. Error: {str(e)}")
            raise
    
    def update_module(self, app_id, module_id, module: Module):
        try:
            validated_module = Module.model_validate(module)
            app = self.get_app(app_id)

            idx = next(
                (i for i, m in enumerate(app.modules) if m.name == module_id),
                None,
            )
            if idx is None:
                raise ValueError(f"{app_id} | Módulo '{module_id}' no encontrado")

            # Solo se permite modificar nombre y descripción; resto de campos se preservan
            app.modules[idx].name = validated_module.name
            app.modules[idx].description = validated_module.description
            self.apps_collection.document(app.id).set(app.model_dump(mode="python"))
            self.logger.info(f"{app.id} | Módulo '{module_id}' actualizado")
        except Exception as e:
            self.logger.error(f"{app_id} | Error al actualizar módulo. Error: {str(e)}")
            raise

    def create_repo(self, app_id, module_id, repo:Repo):
        try:
            validated_repo = Repo.model_validate(repo)
            app = self.get_app(app_id)

            module = next((m for m in app.modules if m.name == module_id), None)
            if module is None:
                raise ValueError(f"{app_id} | Módulo '{module_id}' no encontrado")

            repo_data = validated_repo.model_dump(mode="python")
            token = repo_data.get("repo_token")
            if token:
                repo_data["repo_token"] = hashlib.sha256(token.encode()).hexdigest()

            module.repo = Repo.model_validate(repo_data)
            self.apps_collection.document(app.id).set(app.model_dump(mode="python"))
            self.logger.info(f"{app.id} | Repo agregado al módulo '{module_id}'")
        except Exception as e:
            self.logger.error(f"{app_id} | Error al agregar repo. Error: {str(e)}")
            raise
    
    def update_repo(self, app_id, module_id, repo:Repo):
        try:
            validated_repo = Repo.model_validate(repo)
            app = self.get_app(app_id)

            module = next((m for m in app.modules if m.name == module_id), None)
            if module is None:
                raise ValueError(f"{app_id} | Módulo '{module_id}' no encontrado")

            repo_data = validated_repo.model_dump(mode="python")
            token = repo_data.get("repo_token")
            if token:
                repo_data["repo_token"] = hashlib.sha256(token.encode()).hexdigest()

            module.repo = Repo.model_validate(repo_data)
            self.apps_collection.document(app.id).set(app.model_dump(mode="python"))
            self.logger.info(f"{app.id} | Repo actualizado en módulo '{module_id}'")
        except Exception as e:
            self.logger.error(f"{app_id} | Error al actualizar repo. Error: {str(e)}")
            raise

    def update_app(
        self,
        app,
    ) -> None:
        try:
            validated_app = Application.model_validate(app)

            doc_ref = self.apps_collection.document(validated_app.id)
            snapshot = doc_ref.get()

            if not snapshot.exists:
                raise ValueError(f"Aplicación {validated_app.id} no existe en Firestore")

            current_data = snapshot.to_dict()
            if isinstance(current_data, str):
                # Compatibilidad por si se guardó como JSON string
                try:
                    current_data = json.loads(current_data)
                except json.JSONDecodeError:
                    pass

            new_data = validated_app.model_dump(mode="python")

            if current_data == new_data:
                self.logger.info(f"{validated_app.id} | Aplicación sin cambios, no se guarda")
                return
            
            doc_ref.set(new_data)
            self.logger.info(f"{validated_app.id} | Aplicación actualizada en Firestore")
        except Exception as e:
            self.logger.error(f"{app.id} | Error al modificar la app. Error: {str(e)}")
            raise

    def get_app(self, app_id: str) -> Optional[dict]:
        try:
            doc = self.apps_collection.document(app_id).get()
            doc_dict = doc.to_dict()
            if doc_dict is None:
                raise ValueError(f"{app_id} | App no encontrada")

            if isinstance(doc_dict, str):
                try:
                    doc_dict = json.loads(doc_dict)
                except json.JSONDecodeError:
                    pass

            return Application.model_validate(doc_dict)
        except Exception as e:
            self.logger.error(f"{app_id} | Error al encontrar la app. Error: {str(e)}") 
            raise

    def list_apps(self, project_id:str = None) -> list[Application]:
        apps = []
        try:
            if project_id:
                query = self.apps_collection.where(
                    filter=FieldFilter("project_id", "==", project_id)
                )
                docs = query.stream()
            else:
                docs = self.apps_collection.stream()
                
            for doc in docs:
                doc_dict = doc.to_dict()
                if isinstance(doc_dict, str):
                    try:
                        doc_dict = json.loads(doc_dict)
                    except json.JSONDecodeError:
                        pass
                app = Application.model_validate(doc_dict)
                apps.append(app)
        except Exception as e:
            self.logger.error(f"Error al listar las apps. Error: {str(e)}")
        return apps
