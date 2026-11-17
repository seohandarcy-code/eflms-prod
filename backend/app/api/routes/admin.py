import logging
import urllib.parse

import jwt
from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, require_session
from app.auth import access_store
from app.auth.access_store import DuplicateAllowedUserError, LastAdminError
from app.auth.oidc import SSO_BROKER_CONFIGURED, build_broker_authorize_url, oauth, verify_broker_id_token
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
    SqlQueryRequest,
    SqlQueryResponse,
    TableListResponse,
    TablePageResponse,
)
from app.services import admin_service, sql_query_service
from app.services.sql_query_service import SqlQueryError

logger = logging.getLogger("eflms.admin")

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/auth-config", response_model=AuthConfigResponse)
def auth_config() -> AuthConfigResponse:
    """비인증 공개 엔드포인트 — 프론트가 비밀번호 폼/SSO 버튼 중 뭘 보여줄지 결정하는 데 씀."""
    settings = get_settings()
    local_login_available = settings.auth_mode == "local" or (
        settings.auth_mode == "sso" and settings.sso_allow_local_login
    )
    return AuthConfigResponse(
        auth_mode=settings.auth_mode,
        local_login_available=local_login_available,
        dashboard_login_required=settings.auth_mode == "sso",
    )


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
    return LoginResponse(token=token, expires_in=expires_in, is_admin=True, role="admin")


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


@router.post("/sql", response_model=SqlQueryResponse, dependencies=[Depends(require_admin)])
async def run_sql(body: SqlQueryRequest, session: AsyncSession = Depends(get_session)) -> SqlQueryResponse:
    """조회(SELECT/WITH) 한 문장만 — 허용 목록 테이블, 최대 1,000행, 5초(Stage 16-5, admin만).

    안전장치는 글자 검사가 아니라 DB 쪽(SQLite 읽기 전용 연결 + authorizer, PostgreSQL 읽기 전용 트랜잭션)이다
    — `app/services/sql_query_service.py`.
    """
    try:
        result = await sql_query_service.run_select_sql(session, body.sql)
    except SqlQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SqlQueryResponse(**result.__dict__, max_rows=sql_query_service.MAX_ROWS)


# --- SSO(OIDC) ---


def _exc_detail(exc: Exception) -> str:
    """예외 타입/메시지를 진단 배너용으로 잘라 URL-safe하게 인코딩한다.

    토큰/자격증명이 아니라 순수 네트워크·TLS 진단 메시지라 노출해도 안전하다
    (a-ims-prod가 실제 ADFS 연동 중 이 정보 없이는 매번 서버 로그를 직접 봐야
    했던 문제를 겪고 추가한 패턴).
    """
    return urllib.parse.quote_plus(f"{type(exc).__name__}: {exc}"[:300])


def _safe_next(value: object) -> str:
    """로그인 뒤 돌아갈 화면 경로 — 같은 사이트 안의 경로만 받는다(외부 주소로 보내는 open redirect 방지).

    `/`로 시작하는 경로만 허용하고 `//host`·역슬래시·URL 프래그먼트는 버린다. 아니면 대시보드(`/`).
    """
    if not isinstance(value, str) or not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/"
    return value.split("#", 1)[0][:200] or "/"


@router.get("/sso/login")
async def sso_login(request: Request, next: str = "/"):
    """`next`: 로그인 뒤 돌아갈 화면(대시보드 `/`, 관리자 `/admin` 등). OAuth state와 같은 세션 쿠키에 잠시 담는다."""
    settings = get_settings()
    next_path = _safe_next(next)
    if not SSO_BROKER_CONFIGURED:
        return RedirectResponse(f"{settings.frontend_base_url}{next_path}#error=sso_not_configured")
    request.session["sso_next"] = next_path
    redirect_uri = settings.sso_redirect_uri or str(request.url_for("sso_callback"))
    if settings.sso_flow_mode == "implicit_form_post":
        # discovery 미지원 자체 브로커 — URL 조립 자체는 네트워크 호출이 없어
        # 실패할 일이 없다(app/auth/oidc.py의 build_broker_authorize_url()).
        return RedirectResponse(build_broker_authorize_url(redirect_uri))
    try:
        return await oauth.sso.authorize_redirect(request, redirect_uri)
    except Exception as exc:
        # 리다이렉트 URL을 만들기 전에 authlib이 SSO_ISSUER_URL의
        # .well-known/openid-configuration을 백엔드가 직접 실시간으로 fetch한다 —
        # 브로커에 도달 못하거나(DNS/네트워크/타임아웃) 비정상 응답이면 여기서
        # 예외가 그대로 터진다. 이 버튼은 브라우저 navigation 전용이라 JSON 에러
        # 바디를 읽을 소비자가 없으므로, raw 502 대신 로그인 화면으로 되돌려
        # 보내 에러 배너로 보여준다.
        logger.warning("SSO 로그인 시작 실패: %s: %s", type(exc).__name__, exc)
        return RedirectResponse(
            f"{settings.frontend_base_url}{next_path}#error=broker_unreachable&detail={_exc_detail(exc)}"
        )


@router.api_route("/sso/callback", methods=["GET", "POST"], name="sso_callback")
async def sso_callback(
    request: Request,
    session: AsyncSession = Depends(get_session),
    auth_store: AdminAuthStore = Depends(get_auth_store),
):
    settings = get_settings()
    # 로그인을 시작한 화면으로 돌려보낸다. implicit_form_post는 IdP가 다른 사이트에서 POST로 돌아와
    # 브라우저가 세션 쿠키(SameSite=lax)를 안 보낼 수 있다 — 그때는 대시보드(`/`)로 간다.
    next_path = _safe_next(request.session.pop("sso_next", None))
    frontend_base = settings.frontend_base_url or ""

    # 콜백은 브라우저 리다이렉트 도중이라, 실패해도 raw JSON을 보여주지 않고 항상
    # 화면으로 되돌려보낸다 — 프론트가 #error=코드를 보고 이해할 수 있는 메시지를 띄운다.
    def error_redirect(code: str, detail: str | None = None) -> RedirectResponse:
        url = f"{frontend_base}{next_path}#error={code}"
        if detail:
            url += f"&detail={detail}"
        return RedirectResponse(url)

    if not SSO_BROKER_CONFIGURED:
        return error_redirect("sso_not_configured")

    if settings.sso_flow_mode == "implicit_form_post":
        # discovery 미지원 자체 브로커 — GET이 아니라 POST로 id_token을 form
        # body에 실어 보낸다(authorization code 교환 단계 자체가 없음,
        # app/auth/oidc.py의 verify_broker_id_token() 참고).
        form = await request.form()
        id_token = str(form.get("id_token", ""))
        try:
            claims = verify_broker_id_token(id_token)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as exc:
            logger.warning("SSO 콜백 인증 거부: %s", exc)
            return error_redirect("auth_failed")
        except Exception as exc:
            # JWKS 조회 네트워크 실패 등 — auth_code 모드의 일반 Exception
            # 분기와 같은 원칙으로 "브로커 통신 실패"로 구분한다.
            logger.warning("SSO 콜백 중 브로커 통신 실패: %s: %s", type(exc).__name__, exc)
            return error_redirect("broker_unreachable", _exc_detail(exc))
    else:
        try:
            token = await oauth.sso.authorize_access_token(request)
        except OAuthError as exc:
            logger.warning("SSO 콜백 인증 거부: %s", exc)
            return error_redirect("auth_failed")
        except Exception as exc:
            # OAuthError가 아닌 실패(토큰/JWKS 엔드포인트 네트워크 오류 등) — IdP가
            # 로그인을 "거부"한 게 아니라 브로커에 도달조차 못한 경우라 구분해서
            # 알려준다(/sso/login의 authorize_redirect 예외 처리와 같은 원칙).
            logger.warning("SSO 콜백 중 브로커 통신 실패: %s: %s", type(exc).__name__, exc)
            return error_redirect("broker_unreachable", _exc_detail(exc))

        claims = token.get("userinfo") or {}

    sso_id = str(claims.get(settings.sso_user_id_claim) or "").strip()
    if not sso_id:
        logger.warning(
            "SSO_USER_ID_CLAIM(%s)에 해당하는 클레임을 찾지 못함. 받은 클레임 키: %s",
            settings.sso_user_id_claim,
            list(claims.keys()),
        )
        return error_redirect("missing_claim")

    claim_name = str(claims.get("name") or "").strip() or None
    if sso_id in settings.sso_admin_allowlist_list:
        user = await access_store.upsert_bootstrap_admin(session, sso_id, default_name=claim_name)
    else:
        user = await access_store.get_by_sso_id(session, sso_id)

    if user is None:
        if settings.sso_deny_unregistered_users:
            logger.info("미등록 계정의 로그인 시도(거부): sso_id=%s", sso_id)
            return error_redirect("not_registered")
        # 기본: SSO 인증은 성공했으므로 대시보드 조회 전용(general)으로 통과 — 관리자 화면은 막힌다.
        role, display_name = "general", claim_name or sso_id
        logger.info("SSO 인증 성공(미등록 계정) — 조회 전용으로 통과: sso_id=%s", sso_id)
    else:
        role, display_name = ("admin" if user.is_admin else "user"), user.name
        logger.info("SSO 로그인 성공: sso_id=%s role=%s", sso_id, role)

    session_token, _ = auth_store.issue_session(role)
    # 토큰은 쿼리스트링이 아니라 URL 프래그먼트(#)에 싣는다 — 브라우저가 서버로 보내지 않아 접근 로그·리퍼러에
    # 남지 않는다. 이름은 한글·공백·&가 있어도 깨지지 않게 인코딩한다.
    return RedirectResponse(
        f"{frontend_base}{next_path}#token={session_token}&role={role}&name={urllib.parse.quote(display_name)}"
    )


# --- 접근 권한 관리 (allowed_users CRUD, is_admin 세션만) ---


@router.get("/access-users", response_model=list[AllowedUserOut], dependencies=[Depends(require_admin)])
async def list_access_users(session: AsyncSession = Depends(get_session)) -> list[AllowedUserOut]:
    users = await access_store.list_all(session)
    return [AllowedUserOut.model_validate(u) for u in users]


@router.post("/access-users", response_model=AllowedUserOut, dependencies=[Depends(require_admin)])
async def create_access_user(
    body: AllowedUserCreate, session: AsyncSession = Depends(get_session)
) -> AllowedUserOut:
    try:
        user = await access_store.create(session, body.sso_id.strip(), body.name, body.team, body.is_admin)
    except DuplicateAllowedUserError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
