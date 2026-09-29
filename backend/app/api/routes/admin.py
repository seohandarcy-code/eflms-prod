from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.auth.state import AccountLockedError, AdminAuthStore, InvalidCredentialsError, get_auth_store
from app.core.config import get_settings
from app.db.session import get_session
from app.schemas.admin import LoginRequest, LoginResponse, TableListResponse, TablePageResponse
from app.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, auth_store: AdminAuthStore = Depends(get_auth_store)) -> LoginResponse:
    if get_settings().auth_mode == "none":
        raise HTTPException(status_code=503, detail="관리자 기능이 비활성화돼 있습니다(AUTH_MODE=none)")
    try:
        token, expires_in = auth_store.login(body.password)
    except AccountLockedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return LoginResponse(token=token, expires_in=expires_in)


@router.post("/logout")
def logout(
    authorization: str | None = Header(default=None),
    auth_store: AdminAuthStore = Depends(get_auth_store),
) -> dict[str, bool]:
    if authorization and authorization.startswith("Bearer "):
        auth_store.logout(authorization.removeprefix("Bearer "))
    return {"ok": True}


@router.get("/tables", response_model=TableListResponse, dependencies=[Depends(require_admin)])
def list_tables() -> TableListResponse:
    return TableListResponse(tables=admin_service.list_table_names())


@router.get("/tables/{table_name}", response_model=TablePageResponse, dependencies=[Depends(require_admin)])
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
