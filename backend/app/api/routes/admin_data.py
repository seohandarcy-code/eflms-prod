"""관리자 데이터 입력·내보내기 API (Stage 16-2/16-3, 16-6 붙여넣기) — admin 세션만.

- `GET  /api/admin/data/targets`  — 설비유형·참고표 목록과 현재 건수
- `GET  /api/admin/data/template` — 붙여넣기 양식(헤더·컬럼 설명·허용값)
- `POST /api/admin/data/import`   — 붙여넣은 탭 구분 텍스트(JSON). `check=true`면 검증만(+행별 추가/갱신), 아니면 반영
- `GET  /api/admin/data/rows`     — 지금 데이터를 표(JSON)로 — 행 편집(Stage 18). 저장은 고친 행만 `/import`로
- `GET  /api/admin/data/export`   — 지금 DB 내용을 입력파일과 같은 dat로 내려받기
- `GET  /api/admin/data/export-sql` — 전체 DB를 psql로 복원할 수 있는 PostgreSQL용 .sql로 내려받기(Stage 16-8)

실제 검증·계산·반영은 CLI와 같은 서비스(`import_service`·`reference_service`)가 한다.
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.services import data_admin_service, db_dump_service
from app.services.data_admin_service import MAX_TEXT_BYTES, DataAdminError

router = APIRouter(prefix="/api/admin/data", tags=["admin-data"], dependencies=[Depends(require_admin)])


@router.get("/targets")
async def list_targets(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await data_admin_service.list_targets(session)


class DataImportRequest(BaseModel):
    ef_code: str
    table: str = ""  # 빈 값 = 설비 데이터
    replace: bool = False
    check: bool = True  # 기본은 검증만 — 반영하려면 화면이 check=false로 한 번 더 보낸다
    text: str  # 엑셀에서 복사한 탭 구분 내용(첫 줄 헤더)


@router.get("/template")
async def get_template(ef_code: str, table: str = "") -> dict:
    try:
        return data_admin_service.template(ef_code, table or None)
    except DataAdminError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/rows")
async def list_rows(ef_code: str, table: str = "", session: AsyncSession = Depends(get_session)) -> dict:
    try:
        return await data_admin_service.list_rows(session, ef_code.strip(), table.strip() or None)
    except DataAdminError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/import")
async def import_data(body: DataImportRequest, session: AsyncSession = Depends(get_session)) -> dict:
    if len(body.text.encode("utf-8")) > MAX_TEXT_BYTES:
        raise HTTPException(status_code=413, detail=f"내용이 너무 큽니다(최대 {MAX_TEXT_BYTES // (1024 * 1024)}MB)")
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="붙여넣은 내용이 없습니다")
    try:
        return await data_admin_service.import_text(
            session,
            text=body.text,
            ef_code=body.ef_code.strip(),
            table=body.table.strip() or None,
            replace=body.replace,
            check=body.check,
        )
    except DataAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/export-sql")
async def export_full_sql(session: AsyncSession = Depends(get_session)) -> Response:
    """전체 DB(모든 테이블 + alembic_version)를 PostgreSQL용 .sql 하나로 — 새 DB에서
    `psql -v ON_ERROR_STOP=1 -d <새 DB> -f <파일>`로 복원한다. 형식은 `app/services/db_dump_service.py`."""
    now = datetime.now()
    result = await db_dump_service.build_dump(session, generated_at=now)
    filename = f"eflms_full_{now:%Y%m%d_%H%M}.sql"
    return Response(
        content=result.sql.encode("utf-8"),
        media_type="application/sql; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Table-Count": str(len(result.table_rows)),
            "X-Row-Count": str(result.total_rows),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Table-Count, X-Row-Count",
        },
    )


@router.get("/export")
async def export_data(ef_code: str, table: str = "", session: AsyncSession = Depends(get_session)) -> Response:
    """table이 비면 설비 데이터, 있으면 그 참고표. 엑셀에서 한글이 깨지지 않게 UTF-8 BOM을 붙인다(임포트는 BOM을 뗀다)."""
    try:
        if table:
            text, count = await data_admin_service.export_reference(session, ef_code, table)
        else:
            text, count = await data_admin_service.export_equipment(session, ef_code)
    except DataAdminError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    filename = f"{ef_code}_{table or 'equipment'}_{date.today():%Y%m%d}.dat"
    return Response(
        content=("﻿" + text).encode("utf-8"),
        media_type="text/tab-separated-values; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Row-Count": str(count),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Row-Count",
        },
    )
