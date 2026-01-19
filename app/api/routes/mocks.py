import uuid
import hashlib
from typing import Dict
from fastapi import APIRouter, Header, Request, HTTPException
from models.core_models import Project, Application, Module, Repo
from utils.mocking import load_mock  # Para pruebas locales

router = APIRouter(prefix="", tags=["mock_analysis"])

# Estado en memoria para mocks
mock_projects: Dict[str, Project] = {}
mock_apps: Dict[str, Application] = {}


def hash_token(token: str = None) -> str:
    if not token:
        return None
    return hashlib.sha256(token.encode()).hexdigest()


def get_project_or_404(project_id: str) -> Project:
    project = mock_projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado (mock)")
    return project


def get_app_or_404(app_id: str) -> Application:
    app = mock_apps.get(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Aplicación {app_id} no encontrada (mock)")
    return app


@router.post("/mocks/projects")
async def mock_create_project(project_data: Project, request: Request):
    project = Project.model_validate(project_data)
    project_id = project.id or str(uuid.uuid4())
    project.id = project_id
    mock_projects[project_id] = project
    return project


@router.get("/mocks/projects")
def mock_list_projects(request: Request):
    if not mock_projects:
        raise HTTPException(status_code=404, detail="Proyectos no encontrados (mock)")
    return list(mock_projects.values())


@router.get("/mocks/projects/{project_id}")
def mock_get_project(project_id: str, request: Request):
    return get_project_or_404(project_id)


@router.post("/mocks/applications")
async def mock_create_application(app_data: Application, request: Request):
    app = Application.model_validate(app_data)
    if app.project_id not in mock_projects:
        raise HTTPException(status_code=404, detail=f"Proyecto {app.project_id} no encontrado (mock)")

    app_id = app.id or str(uuid.uuid4())
    if app_id in mock_apps:
        raise HTTPException(status_code=400, detail=f"Aplicación {app_id} ya existe (mock)")

    app.id = app_id
    mock_apps[app_id] = app

    proj = mock_projects[app.project_id]
    if app.id not in proj.applications:
        proj.applications.append(app.id)

    return app


@router.put("/mocks/applications")
async def mock_update_application(app_data: Application, request: Request):
    app = Application.model_validate(app_data)
    stored = get_app_or_404(app.id)
    mock_apps[app.id] = app
    return app


@router.get("/mocks/applications/{app_id}")
def mock_get_application(app_id: str, request: Request):
    return get_app_or_404(app_id)


@router.get("/mocks/applications")
def mock_list_applications(project_id: str, request: Request):
    apps = [a for a in mock_apps.values() if a.project_id == project_id]
    if not apps:
        raise HTTPException(status_code=404, detail="Aplicaciones no encontradas (mock)")
    return apps


@router.post("/mocks/applications/{application_id}/modules")
async def mock_create_module(application_id: str, module: Module, request: Request):
    app = get_app_or_404(application_id)
    mod = Module.model_validate(module)
    if any(m.name == mod.name for m in app.modules):
        raise HTTPException(status_code=400, detail=f"Módulo {mod.name} ya existe (mock)")
    app.modules.append(mod)
    return app


@router.put("/mocks/applications/{application_id}/modules")
async def mock_update_module(application_id: str, module: Module, request: Request):
    app = get_app_or_404(application_id)
    mod = Module.model_validate(module)
    idx = next((i for i, m in enumerate(app.modules) if m.name == mod.name), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"Módulo {mod.name} no encontrado (mock)")
    # Solo nombre y descripción actualizables
    app.modules[idx].name = mod.name
    app.modules[idx].description = mod.description
    return app


@router.post("/mocks/applications/{application_id}/modules/{module_id}/repo")
async def mock_create_or_update_repo(application_id: str, module_id: str, repo: Repo, request: Request):
    app = get_app_or_404(application_id)
    mod = next((m for m in app.modules if m.name == module_id), None)
    if mod is None:
        raise HTTPException(status_code=404, detail=f"Módulo {module_id} no encontrado (mock)")

    repo_data = Repo.model_validate(repo).model_dump(mode="python")
    token = repo_data.get("repo_token")
    if token:
        repo_data["repo_token"] = hash_token(token)
    mod.repo = Repo.model_validate(repo_data)
    return app
@router.post(
    "/mocks/functional_analysis_request"
)
async def analyze_code_request(
    repo_data: Project,
    request: Request,
    git_user: str = Header(default="", alias="X-git-user"),
    git_pat: str = Header(default="", alias="X-git-pat"),
):
    request.app.state.logger.info(
        f"MOCK | Code request analysis recibido para la app dummy"
    )
    return load_mock("create_job")


@router.get(
    "/mocks/functional_analysis_request_full/{job_id}"
)
def return_code_request_full(
    job_id: str,
    request: Request,
):
    request.app.state.logger.info(
        f"MOCK | Code request analysis consultado full para la app dummy"
    )
    return load_mock("get_job_done")

@router.get(
    "/mocks/functional_analysis_request_partial/{job_id}"
)
def return_code_request_partial(
    job_id: str,
    request: Request,
):
    request.app.state.logger.info(
        f"MOCK | Code request analysis consultado parcial para la app dummy"
    )
    return load_mock("get_job_running")
