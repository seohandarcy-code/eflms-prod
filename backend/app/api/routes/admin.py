import logging

from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, require_session
from app.auth import access_store
from app.auth.access_store import LastAdminError
from app.auth.oidc import SSO_BROKER_CONFIGURED, oauth
from app.auth.state import AccountLockedError, AdminAuthStore, InvalidCredentialsError, get_auth_store
from app.core.config import get_settings
from app.db.session import get_session
from app.schemas.admin import (
    AllowedUserCreate,
    AllowedUserOut,
    AllowedUserUpdate,
    AuthConfigResponse,
    LoginRequest,
    LoginResponse,
    TableListResponse,
    TablePageResponse,
)
from app.services import admin_service

logger = logging.getLogger("eflms.admin")

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/auth-config", response_model=AuthConfigResponse)
def auth_config() -> AuthConfigResponse:
    """비인증 공개 엔드포인트 — 프론트가 비밀번호 폼/SSO 버튼 중 뭘 보여줄지 결정하는 데 씀."""
    settings = get_settings()
    local_login_available = settings.auth_mode == "local" or (
        settings.auth_mode == "sso" and settings.sso_allow_local_login
    )
    return AuthConfigResponse(auth_mode=settings.auth_mode, local_login_available=local_login_available)


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, auth_store: AdminAuthStore = Depends(get_auth_store)) -> LoginResponse:
    settings = get_settings()
    # local 모드는 항상 허용. sso 모드는 SSO_ALLOW_LOCAL_LOGIN=true일 때만 허용 —
    # 브로커가 client_id를 아직 발급하지 않은 개발 단계에서 관리자가 먼저 비밀번호로
    # 들어가 "접근 권한 관리"에 SSO 계정을 등록해둘 수 있게 하는 부트스트랩 경로.
    local_login_allowed = settings.auth_mode == "local" or (
        settings.auth_mode == "sso" and settings.sso_allow_local_login
    )
    if not local_login_allowed:
        raise HTTPException(status_code=503, detail="관리자 비밀번호 로그인이 비활성화돼 있습니다")
    try:
        token, expires_in = auth_store.login(body.password)
    except AccountLockedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return LoginResponse(token=token, expires_in=expires_in, is_admin=auth_store.get_is_admin(token))


@router.post("/logout")
def logout(
    authorization: str | None = Header(default=None),
    auth_store: AdminAuthStore = Depends(get_auth_store),
) -> dict[str, bool]:
    if authorization and authorization.startswith("Bearer "):
        auth_store.logout(authorization.removeprefix("Bearer "))
    return {"ok": True}


@router.get("/tables", response_model=TableListResponse, dependencies=[Depends(require_session)])
def list_tables() -> TableListResponse:
    return TableListResponse(tables=admin_service.list_table_names())


@router.get("/tables/{table_name}", response_model=TablePageResponse, dependencies=[Depends(require_session)])
async def get_table(
    table_name: str,
    page: int = 1,
    page_size: int = 50,
    session: AsyncSession = Depends(get_session),
) -> TablePageResponse:
    result = await admin_service.get_table_page(session, table_name, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail="알 수 없는 테이블입니다")
    return TablePageResponse(**result)


# --- SSO(OIDC) ---


@router.get("/sso/login")
async def sso_login(request: Request):
    if not SSO_BROKER_CONFIGURED:
        raise HTTPException(status_code=503, detail="SSO가 설정되지 않았습니다(SSO_ISSUER_URL 없음)")
    settings = get_settings()
    redirect_uri = settings.sso_redirect_uri or str(request.url_for("sso_callback"))
    try:
        return await oauth.sso.authorize_redirect(request, redirect_uri)
    except Exception as exc:
        logger.exception("SSO 로그인 시작 실패")
        raise HTTPException(status_code=502, detail="SSO 브로커에 연결하지 못했습니다") from exc


@router.get("/sso/callback", name="sso_callback")
async def sso_callback(
    request: Request,
    session: AsyncSession = Depends(get_session),
    auth_store: AdminAuthStore = Depends(get_auth_store),
):
    if not SSO_BROKER_CONFIGURED:
        raise HTTPException(status_code=503, detail="SSO가 설정되지 않았습니다(SSO_ISSUER_URL 없음)")
    settings = get_settings()

    try:
        token = await oauth.sso.authorize_access_token(request)
    except OAuthError as exc:
        logger.warning("SSO 콜백 인증 거부: %s", exc)
        raise HTTPException(status_code=401, detail="SSO 인증에 실패했습니다") from exc
    except Exception as exc:
        logger.exception("SSO 콜백 처리 중 오류(브로커 통신 실패 등)")
        raise HTTPException(status_code=502, detail="SSO 브로커 통신에 실패했습니다") from exc

    claims = token.get("userinfo") or {}
    sso_id = claims.get(settings.sso_user_id_claim)
    if not sso_id:
        logger.warning(
            "SSO_USER_ID_CLAIM(%s)에 해당하는 클레임을 찾지 못함. 받은 클레임 키: %s",
            settings.sso_user_id_claim,
            list(claims.keys()),
        )
        raise HTTPException(status_code=401, detail="필요한 사용자 식별 정보를 받지 못했습니다")

    if sso_id in settings.sso_admin_allowlist_list:
        user = await access_store.upsert_bootstrap_admin(session, sso_id)
    else:
        user = await access_store.get_by_sso_id(session, sso_id)

    if user is None:
        logger.info("미등록 계정의 로그인 시도: sso_id=%s", sso_id)
        raise HTTPException(status_code=403, detail="등록되지 않은 계정입니다")

    session_token, _ = auth_store.issue_session(is_admin=user.is_admin)
    logger.info("SSO 로그인 성공: sso_id=%s role=%s", sso_id, "admin" if user.is_admin else "user")

    frontend_base = settings.frontend_base_url or ""
    role = "admin" if user.is_admin else "user"
    return RedirectResponse(f"{frontend_base}/admin#token={session_token}&role={role}&name={user.name}")


# --- 접근 권한 관리 (allowed_users CRUD, is_admin 세션만) ---


@router.get("/access-users", response_model=list[AllowedUserOut], dependencies=[Depends(require_admin)])
async def list_access_users(session: AsyncSession = Depends(get_session)) -> list[AllowedUserOut]:
    users = await access_store.list_all(session)
    return [AllowedUserOut.model_validate(u) for u in users]


@router.post("/access-users", response_model=AllowedUserOut, dependencies=[Depends(require_admin)])
async def create_access_user(
    body: AllowedUserCreate, session: AsyncSession = Depends(get_session)
) -> AllowedUserOut:
    user = await access_store.create(session, body.sso_id, body.name, body.team, body.is_admin)
    return AllowedUserOut.model_validate(user)


@router.patch("/access-users/{sso_id}", response_model=AllowedUserOut, dependencies=[Depends(require_admin)])
async def update_access_user(
    sso_id: str, body: AllowedUserUpdate, session: AsyncSession = Depends(get_session)
) -> AllowedUserOut:
    try:
        user = await access_store.update(session, sso_id, name=body.name, team=body.team, is_admin=body.is_admin)
    except LastAdminError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=404, detail="등록된 계정이 아닙니다")
    return AllowedUserOut.model_validate(user)


@router.delete("/access-users/{sso_id}", dependencies=[Depends(require_admin)])
async def delete_access_user(sso_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, bool]:
    try:
        deleted = await access_store.delete(session, sso_id)
    except LastAdminError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="등록된 계정이 아닙니다")
    return {"ok": True}
