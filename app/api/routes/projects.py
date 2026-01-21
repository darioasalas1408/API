import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.models.core_models import Project
from app.core.config import Settings
from app.services.project_services import ProjectsService
from app.core.auth_deps import get_current_user
from app.models.project_responses import ProjectWithUserResponse
from app.utils.mocking import load_mock  # Para pruebas locales


router = APIRouter(
    dependencies=[Depends(get_current_user)],
    prefix="",
    tags=["project"],
)


class ProjectUpdateRequest(BaseModel):
    name: str = Field(..., max_length=140)
    user_id: str = Field(..., description="uuid-4 del usuario dueño/admin del proyecto")


def get_services(request: Request) -> tuple[Settings, ProjectsService]:
    settings: Settings = request.app.state.settings
    projects_service: ProjectsService = request.app.state.projects_service
    return settings, projects_service


@router.post("/projects", response_model=ProjectWithUserResponse)
async def create_project(project_data: Project, request: Request):
    _, project_service = get_services(request)

    # ✅ Si viene vacío, generamos id
    if not project_data.id:
        project_data.id = str(uuid.uuid4())

    try:
        project_service.create_project(project_data)

        request.app.state.logger.info(
            f"{project_data.id} | Proyecto creado con el nombre {project_data.name}"
        )

        return project_service.get_project(project_data.id)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}", response_model=ProjectWithUserResponse)
async def update_project(project_id: str, body: ProjectUpdateRequest, request: Request):
    _, project_service = get_services(request)

    try:
        project_service.update_project(
            project_id, project_name=body.name, user_id=body.user_id
        )
        return project_service.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}", response_model=dict)
async def delete_project(project_id: str, request: Request):
    _, project_service = get_services(request)

    try:
        project_service.delete_project(project_id)
        return {"ok": True, "deleted_project_id": project_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", response_model=ProjectWithUserResponse)
def get_project(project_id: str, request: Request):
    service = ProjectsService(request.app.state.settings, request.app.state.logger)
    return service.get_project(project_id)


@router.get("/projects", response_model=list[ProjectWithUserResponse])
def list_projects(request: Request):
    service = ProjectsService(request.app.state.settings, request.app.state.logger)
    return service.list_projects()


@router.get("/projects/by-user/{user_id}", response_model=list[ProjectWithUserResponse])
def get_projects_by_user(user_id: str, request: Request):
    service = ProjectsService(request.app.state.settings, request.app.state.logger)
    return service.list_projects_by_user_id(user_id)


@router.get("/projects/{project_id}/relations")
def get_project_relations(project_id: str, request: Request):
    """
    Mock: hoy siempre devuelve el mismo JSON.
    A futuro: se reemplaza por lógica que depende de project_id.
    """
    request.app.state.logger.info(
        f"{project_id} | MOCK project relations solicitadas"
    )
    data = load_mock("project_relations")
    if isinstance(data, dict):
        data["project_id"] = project_id  # útil desde ya, sin cambiar el mock base
    return data
