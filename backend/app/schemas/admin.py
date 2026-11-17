from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_in: int
    is_admin: bool
    role: str = "admin"


class AuthConfigResponse(BaseModel):
    auth_mode: str
    local_login_available: bool
    # AUTH_MODE=sso면 대시보드도 로그인해야 보인다(Stage 16-1) — 프론트가 로그인 화면을 띄울지 결정
    dashboard_login_required: bool = False


class TableListResponse(BaseModel):
    tables: list[str]


class TablePageResponse(BaseModel):
    table_name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class SqlQueryRequest(BaseModel):
    sql: str


class SqlQueryResponse(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    elapsed_ms: int
    max_rows: int


class AllowedUserCreate(BaseModel):
    sso_id: str
    name: str
    team: str | None = None
    is_admin: bool = False


class AllowedUserUpdate(BaseModel):
    name: str | None = None
    team: str | None = None
    is_admin: bool | None = None


class AllowedUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sso_id: str
    name: str
    team: str | None
    is_admin: bool
    created_at: datetime
