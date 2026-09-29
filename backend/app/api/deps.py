from fastapi import Depends, Header, HTTPException

from app.auth.state import AdminAuthStore, get_auth_store
from app.core.config import get_settings


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    return authorization.removeprefix("Bearer ")


def require_session(
    authorization: str | None = Header(default=None),
    auth_store: AdminAuthStore = Depends(get_auth_store),
) -> None:
    """유효한 `/admin` 세션이면 통과 — DB 테이블 조회처럼 등록된 사람이면 누구나 되는 동작에 쓴다.

    local 모드는 세션 = 관리자 그 자체이므로 이걸로 충분하다. sso 모드에선
    `allowed_users`에 등록된 사람이면(admin이 아니어도) 통과한다.
    """
    if get_settings().auth_mode == "none":
        raise HTTPException(status_code=503, detail="관리자 기능이 비활성화돼 있습니다(AUTH_MODE=none)")

    token = _bearer_token(authorization)
    if not auth_store.is_valid(token):
        raise HTTPException(status_code=401, detail="세션이 유효하지 않습니다")


def require_admin(
    authorization: str | None = Header(default=None),
    auth_store: AdminAuthStore = Depends(get_auth_store),
) -> None:
    """`is_admin=True` 세션만 통과 — 접근 권한 관리(allowed_users CRUD)처럼

    실제 관리자 권한이 필요한 동작에 쓴다. local 모드는 로그인 자체가 항상
    is_admin=True 세션을 발급하므로 `require_session`과 동일하게 동작한다.
    """
    if get_settings().auth_mode == "none":
        raise HTTPException(status_code=503, detail="관리자 기능이 비활성화돼 있습니다(AUTH_MODE=none)")

    token = _bearer_token(authorization)
    if not auth_store.is_valid(token):
        raise HTTPException(status_code=401, detail="세션이 유효하지 않습니다")
    if not auth_store.get_is_admin(token):
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
