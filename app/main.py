from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import applications, projects, health, mocks, auth
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.firestore import get_firestore_client

from app.services.project_services import ProjectsService
from app.services.apps_services import AppsService
from app.api.routes import users


def create_app() -> FastAPI:
    settings = get_settings()
    logger = get_logger(settings)

    app = FastAPI(
        title="Application Management API",
        version="1.0.0",
    )

    # CORS (necesario para cookies/sesiones desde el front)
    origins = [o.strip() for o in settings.frontend_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    firestore = get_firestore_client(
    project=settings.gcp_project,
    database=settings.firestore_db,
    )
    app.state.firestore = firestore

    # Settings & logger
    app.state.settings = settings
    app.state.logger = logger

    # Services
    app.state.projects_service = ProjectsService(settings, logger)
    app.state.apps_service = AppsService(settings, logger)

    # Routers
    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(applications.router)
    app.include_router(health.router)
    app.include_router(mocks.router)
    app.include_router(users.router)
    return app


app = create_app()
