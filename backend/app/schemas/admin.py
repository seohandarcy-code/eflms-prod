from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_in: int


class TableListResponse(BaseModel):
    tables: list[str]


class TablePageResponse(BaseModel):
    table_name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


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
