from fastapi import Depends, Header, HTTPException

from app.auth.state import AdminAuthStore, get_auth_store
from app.core.config import get_settings


def require_admin(
    authorization: str | None = Header(default=None),
    auth_store: AdminAuthStore = Depends(get_auth_store),
) -> None:
    settings = get_settings()
    if settings.auth_mode == "none":
        raise HTTPException(status_code=503, detail="관리자 기능이 비활성화돼 있습니다(AUTH_MODE=none)")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")

    token = authorization.removeprefix("Bearer ")
    if not auth_store.is_valid(token):
        raise HTTPException(status_code=401, detail="세션이 유효하지 않습니다")
