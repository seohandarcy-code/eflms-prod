"""관리자 전용 조회 로직 — 화이트리스트에 있는 테이블만 페이지네이션 조회를 허용한다
(임의 테이블명 노출·SQL 인젝션 방지). 편집 기능은 없음(조회 전용).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models  # noqa: F401  (Base.metadata에 전체 테이블 등록)
from app.db.base import Base

ALLOWED_TABLES: list[str] = [
    "equipment_type",
    "equipment",
    "score_snapshot",
    "transformer_score_detail",
    "dga_reading",
    "furan_reading",
    "dielectric_test",
    "oil_test",
    "load_condition",
    "periodic_inspection",
    "design_attribute",
    "equipment_extra_attribute",
]


def list_table_names() -> list[str]:
    return list(ALLOWED_TABLES)


async def get_table_page(
    session: AsyncSession, table_name: str, page: int, page_size: int
) -> dict[str, Any] | None:
    if table_name not in ALLOWED_TABLES:
        return None

    table = Base.metadata.tables[table_name]
    total = await session.scalar(select(func.count()).select_from(table))

    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size

    result = await session.execute(select(table).offset(offset).limit(page_size))
    rows = [dict(row._mapping) for row in result]

    return {
        "table_name": table_name,
        "columns": [c.name for c in table.columns],
        "rows": rows,
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }
