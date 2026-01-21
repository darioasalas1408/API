import os
import tempfile
import base64
import configparser
from functools import lru_cache
from dataclasses import dataclass


@dataclass
class Settings:
    """Parámetros de configuración cargados desde archivo y variables de entorno."""
    environment: str
    config: configparser.ConfigParser
    gcp_project: str
    firestore_db: str
    apps_collection: str
    projects_collection: str
    log_level: str
    frontend_origins: str
    session_ttl_hours: int
    session_cookie_name: str
    google_application_credentials: str | None = None 
    users_collection: str = "users"


@lru_cache()
def get_settings() -> Settings:
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.ini")
    config_path = os.path.abspath(config_path)

    cfg = configparser.ConfigParser()
    cfg.read(config_path)
    # -------------------------------------------------------------------------
    # Credenciales GCP en Vercel
    #
    # Recomendado:
    # - GOOGLE_APPLICATION_CREDENTIALS_JSON: JSON del Service Account (texto)
    # Alternativa:
    # - GOOGLE_APPLICATION_CREDENTIALS_JSON_B64: el mismo JSON pero en Base64
    #
    # La app vuelca el JSON a /tmp y setea GOOGLE_APPLICATION_CREDENTIALS para usar ADC.
    # -------------------------------------------------------------------------
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

    creds_b64 = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON_B64")
    if (not creds_json) and creds_b64:
        try:
            creds_json = base64.b64decode(creds_b64).decode("utf-8")
        except Exception:
            creds_json = None

    if creds_json and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        tmp_path = os.path.join(tempfile.gettempdir(), "gcp_credentials.json")
        try:
            if (not os.path.exists(tmp_path)) or (open(tmp_path, "r", encoding="utf-8").read() != creds_json):
                with open(tmp_path, "w", encoding="utf-8") as f:
                    f.write(creds_json)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp_path
        except Exception:
            # Si falla (muy raro), dejamos que la app siga y caiga con un error claro al usar GCP
            pass


    # -------------------------------------------------------------------------
    # GOOGLE_APPLICATION_CREDENTIALS
    # Prioridad:
    # 1. Variable de entorno GOOGLE_APPLICATION_CREDENTIALS
    # 2. ./secrets/GCP.json (relativo al repo) si existe
    # -------------------------------------------------------------------------
    google_application_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if not google_application_credentials:
        candidate = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "secrets", "GCP.json")
        )
        if os.path.exists(candidate):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = candidate
            google_application_credentials = candidate

    # -------------------------------------------------------------------------
    # ENV
    # -------------------------------------------------------------------------
    environment = os.environ.get(
        "ENVIRONMENT",
        cfg.get("General", "environment", fallback="local"),
    )

    # -------------------------------------------------------------------------
    # GCP / Firestore
    # Prioridad:
    # 1. Variables de entorno
    # 2. config.ini [GCP]
    # -------------------------------------------------------------------------
    gcp_project = os.environ.get(
        "GCP_PROJECT",
        os.environ.get(
            "GOOGLE_CLOUD_PROJECT",
            cfg.get("GCP", "gcp_project", fallback=""),
        ),
    )

    firestore_db = os.environ.get(
        "FIRESTORE_DB",
        cfg.get("GCP", "firestore_db", fallback=""),
    )

    # -------------------------------------------------------------------------
    # Collections
    # -------------------------------------------------------------------------
    apps_collection = os.environ.get(
        "APPS_COLLECTION",
        cfg.get("GCP", "apps_collection", fallback="apps"),
    )

    projects_collection = os.environ.get(
        "PROJECTS_COLLECTION",
        cfg.get("GCP", "projects_collection", fallback="projects"),
    )

    # -------------------------------------------------------------------------
    # Users
    # -------------------------------------------------------------------------
    users_collection = os.environ.get(
        "USERS_COLLECTION",
        cfg.get("GCP", "users_collection", fallback="users"),
    )

    # -------------------------------------------------------------------------
    # Logging / Frontend
    # -------------------------------------------------------------------------
    log_level = os.environ.get(
        "LOG_LEVEL",
        cfg.get("General", "log_level", fallback="INFO"),
    )

    frontend_origins = os.environ.get(
        "FRONTEND_ORIGINS",
        cfg.get("General", "frontend_origins", fallback="http://localhost:5173"),
    )

    # -------------------------------------------------------------------------
    # Sessions
    # -------------------------------------------------------------------------
    session_ttl_hours = int(
        os.environ.get(
            "SESSION_TTL_HOURS",
            cfg.get("General", "session_ttl_hours", fallback="8"),
        )
    )

    session_cookie_name = os.environ.get(
        "SESSION_COOKIE_NAME",
        cfg.get("General", "session_cookie_name", fallback="startia_session"),
    )

    return Settings(
        config=cfg,
        environment=environment,
        gcp_project=gcp_project,
        firestore_db=firestore_db,
        apps_collection=apps_collection,
        projects_collection=projects_collection,
        log_level=log_level,
        frontend_origins=frontend_origins,
        session_ttl_hours=session_ttl_hours,
        session_cookie_name=session_cookie_name,
        google_application_credentials=google_application_credentials,
        users_collection=users_collection
    )
