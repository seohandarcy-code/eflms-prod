from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict:
    settings = get_settings()
    return {"status": "ok", "app_env": settings.app_env}
