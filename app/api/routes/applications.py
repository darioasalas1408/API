from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from app.models.core_models import Application, Module, Repo
from app.core.config import get_settings, Settings
from app.services.apps_services import AppsService
from app.utils.mocking import load_mock  # Para pruebas locales
from app.core.auth_deps import get_current_user

router = APIRouter(
    dependencies=[Depends(get_current_user)],
    prefix="", tags=["applications"])

def get_services(request: Request) -> tuple[Settings, AppsService]:
    """Extrae dependencias compartidas desde el estado de la aplicación.

    Args:
        request: Petición entrante de FastAPI.

    Returns:
        tuple[Settings, JobsService, AnalysisService]: Servicios configurados.
    """
    settings: Settings = request.app.state.settings
    apps_service: AppsService = request.app.state.apps_service
    if apps_service is None:
        raise HTTPException(status_code=503, detail="Firestore no está configurado. Configurá credenciales de GCP en Vercel.")
    return settings, apps_service

@router.post(
    "/applications"
)
async def create_application(
    app_data: Application,
    request: Request,
):
    settings, apps_service = get_services(request)
    try:
        apps_service.create_app(app_data)
        request.app.state.logger.info(f"{app_data.id} | Aplicación creada")
        return apps_service.get_app(app_data.id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        request.app.state.logger.error(f"{app_data.id} | Error al crear aplicación: {e}")
        raise HTTPException(status_code=500, detail="Error al crear la aplicación")

@router.put(
    "/applications"
)
async def update_application(
    app_data: Application,
    request: Request,
):
    settings, apps_service = get_services(request)
    try:
        apps_service.update_app(app_data)
        request.app.state.logger.info(f"{app_data.id} | Aplicación actualizada")
        return apps_service.get_app(app_data.id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        request.app.state.logger.error(f"{app_data.id} | Error al actualizar aplicación: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar la aplicación")

@router.get(
    "/applications/{app_id}"
)
def get_application(
    app_id: str,
    request: Request,
):
    settings, apps_service = get_services(request)
    try:
        return apps_service.get_app(app_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        request.app.state.logger.error(f"{app_id} | Error al obtener aplicación: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener la aplicación")

@router.get(
    "/applications/"
)
def list_applications(
    project_id: str,
    request: Request,
):
    settings, apps_service = get_services(request)
    try:
        apps = apps_service.list_apps(project_id)
        if not apps:
            raise HTTPException(status_code=404, detail="Aplicaciones no encontradas")
        return apps
    except HTTPException:
        raise
    except Exception as e:
        request.app.state.logger.error(f"{project_id} | Error al listar aplicaciones: {e}")
        raise HTTPException(status_code=500, detail="Error al listar las aplicaciones")


@router.post(
    "/applications/{application_id}/modules"
)
async def create_module(
    application_id: str,
    module: Module,
    request: Request,
):
    settings, apps_service = get_services(request)
    try:
        apps_service.create_module(application_id, module)
        request.app.state.logger.info(f"{application_id} | Módulo '{module.name}' creado")
        return apps_service.get_app(application_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        request.app.state.logger.error(f"{application_id} | Error al crear módulo: {e}")
        raise HTTPException(status_code=500, detail="Error al crear el módulo")

@router.put(
    "/applications/{application_id}/modules"
)
async def update_module(
    application_id: str,
    module: Module,
    request: Request,
):
    settings, apps_service = get_services(request)
    try:
        apps_service.update_module(application_id, module.name, module)
        request.app.state.logger.info(f"{application_id} | Módulo '{module.name}' actualizado")
        return apps_service.get_app(application_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        request.app.state.logger.error(f"{application_id} | Error al actualizar módulo: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar el módulo")

@router.post(
    "/applications/{application_id}/modules/{module_id}/repo"
)
async def create_or_update_repo(
    application_id: str,
    module_id: str,
    repo: Repo,
    request: Request,
):
    settings, apps_service = get_services(request)
    try:
        apps_service.update_repo(application_id, module_id, repo)
        request.app.state.logger.info(
            f"{application_id} | Repo actualizado para módulo '{module_id}'"
        )
        return apps_service.get_app(application_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        request.app.state.logger.error(f"{application_id} | Error al actualizar repo: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar el repo")

        

@router.get("/applications/{application_id}/tech-dependencies")
def get_app_tech_dependencies(application_id: str, request: Request):
    """
    Mock: hoy siempre devuelve el mismo JSON.
    A futuro: se reemplaza por lógica que depende de application_id.
    """
    request.app.state.logger.info(
        f"{application_id} | MOCK tech dependencies solicitadas"
    )
    data = load_mock("app_tech_dependencies")
    if isinstance(data, dict):
        data["app_id"] = application_id  # útil desde ya, sin cambiar el mock base
    return data


@router.get("/applications/{application_id}/relations")
def get_app_relations(application_id: str, request: Request):
    """
    Mock: hoy siempre devuelve el mismo JSON.
    A futuro: se reemplaza por lógica que depende de application_id.
    """
    request.app.state.logger.info(
        f"{application_id} | MOCK relations solicitadas"
    )
    data = load_mock("app_relations")
    if isinstance(data, dict):
        data["app_id"] = application_id
    return data
