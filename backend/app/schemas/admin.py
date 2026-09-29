from typing import Any

from pydantic import BaseModel


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
