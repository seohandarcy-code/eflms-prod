"""관리자 입력 변경 이력·되돌리기 API (2026-11-19, Stage 21-4) — admin 세션만.

- `GET  /api/admin/changes`             — 최근 변경 목록(임포트·교체·행 편집·참고표 넣기/리셋·되돌리기)
- `GET  /api/admin/changes/{id}`        — 변경 상세(행별 바뀌기 전후 값) + 되돌릴 수 있는지(undo_check)
- `POST /api/admin/changes/{id}/undo`   — 되돌리기. {"check": true}면 미리보기(되돌릴 수 있는지만), false면 실행.
  못 되돌리면(이미 되돌림·그 뒤 같은 데이터를 바꾼 변경·다른 작업 진행 중·DB 업그레이드 필요) 409.

실제 기록·되돌리기는 app/services/change_service.py. 되돌리기는 데이터 작업 잠금을 잡고 한 트랜잭션으로 한다.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.services import change_service, job_lock
from app.services.schema_check import UPGRADE_HINT, schema_status

router = APIRouter(prefix="/api/admin/changes", tags=["admin-changes"], dependencies=[Depends(require_admin)])


async def _require_schema(session: AsyncSession) -> None:
    if not (await schema_status(session)).ok:
        raise HTTPException(status_code=409, detail=UPGRADE_HINT)


@router.get("")
async def list_changes(limit: int = 100, session: AsyncSession = Depends(get_session)) -> list[dict]:
    await _require_schema(session)
    return await change_service.list_changes(session, limit=max(1, min(limit, 500)))


@router.get("/{change_id}")
async def get_change(change_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    await _require_schema(session)
    detail = await change_service.change_detail(session, change_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="없는 변경입니다")
    return detail


class UndoRequest(BaseModel):
    check: bool = True


@router.post("/{change_id}/undo")
async def undo_change(change_id: int, body: UndoRequest, session: AsyncSession = Depends(get_session)) -> dict:
    await _require_schema(session)
    detail = await change_service.change_detail(session, change_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="없는 변경입니다")
    if body.check:
        return {"change_id": change_id, "check": True, **detail["undo_check"]}
    if not detail["undo_check"]["possible"]:
        raise HTTPException(status_code=409, detail=detail["undo_check"]["reason"])
    try:
        token = await job_lock.acquire(session, f"되돌리기 #{change_id}")
    except job_lock.DataJobError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    try:
        try:
            undo_id = await change_service.undo_change(session, change_id, actor="admin")
            await session.commit()
        except change_service.UndoError as exc:
            await session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (DBAPIError, KeyError, ValueError) as exc:
            await session.rollback()
            raise HTTPException(status_code=500, detail=f"되돌리기 중 오류로 전체 취소: {type(exc).__name__}: {exc}") from exc
    finally:
        await job_lock.release(session, token)
    return {"change_id": change_id, "check": False, "possible": True, "undo_change_id": undo_id}
