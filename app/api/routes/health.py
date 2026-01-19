from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])

@router.get("/healthz", status_code=200)
def health_check(request: Request):
    """Endpoint simple para verificar que la API está viva."""
    request.app.state.logger.info("Startia Application Management Health Check")
    return {"status": "ok"}
