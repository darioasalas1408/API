import logging
from app.core.config import Settings

def get_logger(settings: Settings) -> logging.Logger:
    """Configura y devuelve el logger principal según el entorno.

    Args:
        settings: Configuración con nivel de log y entorno.

    Returns:
        logging.Logger: Logger listo para usarse en la app.
    """
    logger = logging.getLogger("Synaptia_Code_Analyzer")
    logger.setLevel(settings.log_level)

    if not settings.environment or settings.environment == "DEV":
        # Logging en consola
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(levelname)s] %(asctime)s - %(name)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.info("Logging configurado en consola (modo desarrollo) 🛠️")
    else:
        # Google Cloud Logging
        import google.cloud.logging
        from google.cloud.logging.handlers import CloudLoggingHandler

        client = google.cloud.logging.Client()
        handler = CloudLoggingHandler(client)
        logger.addHandler(handler)
        logger.info("Logging configurado para Google Cloud Logging 🚀")

    return logger
