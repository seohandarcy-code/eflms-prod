from fastapi import Depends, Header, HTTPException

from app.auth.state import AdminAuthStore, get_auth_store
from app.core.config import get_settings


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    return authorization.removeprefix("Bearer ")


def _role(authorization: str | None, auth_store: AdminAuthStore) -> str:
    role = auth_store.get_role(_bearer_token(authorization))
    if role is None:
        raise HTTPException(status_code=401, detail="세션이 유효하지 않습니다")
    return role


def _require_admin_feature_enabled() -> None:
    if get_settings().auth_mode == "none":
        raise HTTPException(status_code=503, detail="관리자 기능이 비활성화돼 있습니다(AUTH_MODE=none)")


def require_viewer(
    authorization: str | None = Header(default=None),
    auth_store: AdminAuthStore = Depends(get_auth_store),
) -> None:
    """대시보드 조회 API용 (Stage 16-1).

    `AUTH_MODE=sso`일 때만 로그인 세션(역할 무관 — general 포함)을 요구한다. none/local은
    사용자를 구분할 수단이 없어(local은 관리자 비밀번호 1개) 지금처럼 공개로 둔다.
    """
    if get_settings().auth_mode != "sso":
        return
    _role(authorization, auth_store)


def require_session(
    authorization: str | None = Header(default=None),
    auth_store: AdminAuthStore = Depends(get_auth_store),
) -> None:
    """`allowed_users`에 등록된 사람(admin/user) — 관리자 화면의 DB 테이블 조회에 쓴다.

    local 모드는 세션 = 관리자 그 자체다. sso 모드의 미등록 사용자(general)는 대시보드만 볼 수
    있으므로 여기서 403으로 막는다.
    """
    _require_admin_feature_enabled()
    if _role(authorization, auth_store) not in ("admin", "user"):
        raise HTTPException(status_code=403, detail="등록된 사용자만 사용할 수 있습니다")


def require_admin(
    authorization: str | None = Header(default=None),
    auth_store: AdminAuthStore = Depends(get_auth_store),
) -> None:
    """admin 세션만 통과 — 접근 권한 관리, 데이터 입력·내보내기처럼 실제 관리자 권한이 필요한 동작."""
    _require_admin_feature_enabled()
    if _role(authorization, auth_store) != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
