import os
import logging
from google.auth.exceptions import DefaultCredentialsError

from app.core.config import Settings


def _is_dev_environment(env: str | None) -> bool:
    v = (env or "").strip().lower()
    return v in {"", "dev", "local", "development", "test", "preview"}


def get_logger(settings: Settings) -> logging.Logger:
    """Configura y devuelve el logger principal.

    - En dev/local: consola (stdout)
    - En prod: intenta Google Cloud Logging si hay credenciales; si no, cae a consola.

    Nota: en Vercel, `VERCEL_ENV` suele ser `production|preview|development`.
    """
    logger = logging.getLogger("startia")
    # Normaliza nivel
    level_name = str(getattr(settings, "log_level", "INFO")).upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))
    logger.propagate = False

    # Evitar handlers duplicados (Vercel puede reusar el runtime)
    if getattr(logger, "_configured", False):
        return logger

    env = getattr(settings, "environment", None)
    force_gcp = os.environ.get("USE_GCP_LOGGING", "").strip().lower() in {"1", "true", "yes"}
    use_gcp = force_gcp or (not _is_dev_environment(env) and (env or "").strip().lower() in {"prod", "production", "staging"})

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    if use_gcp:
        try:
            import google.cloud.logging
            from google.cloud.logging.handlers import CloudLoggingHandler

            client = google.cloud.logging.Client(project=getattr(settings, 'gcp_project', None) or None)
            handler = CloudLoggingHandler(client)
            logger.addHandler(handler)
            logger.info("Logging configurado para Google Cloud Logging 🚀")
        except (DefaultCredentialsError, Exception) as e:
            # Fallback a consola si no hay credenciales/permiso
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.warning(f"No se pudo inicializar Google Cloud Logging; usando consola. Motivo: {e}")
    else:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.info("Logging configurado en consola 🛠️")

    logger._configured = True  # type: ignore[attr-defined]
    return logger
