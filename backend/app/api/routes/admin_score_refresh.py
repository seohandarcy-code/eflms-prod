"""관리자 점수 갱신 API (2026-11-19, Stage 21-1) — admin 세션만.

- `GET  /api/admin/score-refresh` — 마지막 실행과 최근 기록(score_refresh_run), 지금 다른 데이터 작업이 도는지,
  DB 버전(최신이 아니면 기록 대신 업그레이드 안내), 서버 자동 갱신 설정(Stage 21-1b)
- `POST /api/admin/score-refresh` — 한국 시간 오늘 기준으로 지금 갱신(전 유형, 점수 테이블만). 바로 실행해서 결과를 돌려준다.
  다른 데이터 작업이 진행 중이면 409.

실제 계산·저장·기록은 명령(`python -m app.db.recalculate`)과 같은 서비스(score_refresh_service)가 한다.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.clock import today_kst
from app.core.config import get_settings
from app.db.session import get_session
from app.equipment_types.registry import registered_codes
from app.services import job_lock, score_refresh_service
from app.services.schema_check import UPGRADE_HINT, schema_status

router = APIRouter(prefix="/api/admin/score-refresh", tags=["admin-score-refresh"], dependencies=[Depends(require_admin)])


@router.get("")
async def refresh_status(session: AsyncSession = Depends(get_session)) -> dict:
    factory = job_lock.factory_for(session)
    schema = await schema_status(session)
    settings = get_settings()
    body = {
        "today": today_kst(),
        # DB가 예전 버전이면(마이그레이션 전) 실행 기록 테이블이 없다 — 500 대신 업그레이드 안내(Stage 21-1b)
        "schema": schema.as_dict() | {"hint": None if schema.ok else UPGRADE_HINT},
        "auto": {"enabled": settings.score_refresh_auto, "check_minutes": settings.score_refresh_check_minutes},
        "running": None,
        "runs": [],
    }
    if schema.ok:
        lock = await job_lock.current_holder(session)
        body["running"] = None if lock is None else {"holder": lock.holder, "acquired_at": lock.acquired_at}
        body["runs"] = await score_refresh_service.recent_runs(factory)
    return body


@router.post("")
async def refresh_now(session: AsyncSession = Depends(get_session)) -> dict:
    factory = job_lock.factory_for(session)
    result = await score_refresh_service.refresh_scores(
        factory, registered_codes(), today_kst(), trigger="admin", requested_by="admin"
    )
    if result.status in ("busy", "unavailable"):  # 다른 작업 진행 중 / DB 업그레이드 필요
        raise HTTPException(status_code=409, detail=result.message)
    return {
        "run_id": result.run_id,
        "status": result.status,
        "as_of": result.as_of,
        "equipment_count": result.equipment_count,
        "types": [{"ef_code": t.ef_code, "count": t.count, "error": t.error} for t in result.types],
    }
