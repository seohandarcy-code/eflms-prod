from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_viewer
from app.db.session import get_session
from app.schemas.equipment import EquipmentDetail, EquipmentSummary, EquipmentTypeOut, ScoreHistoryPoint, SummaryKPI
from app.services import equipment_service

# AUTH_MODE=sso면 로그인한 사람만(역할 무관) 조회할 수 있다 — none/local은 지금처럼 공개(Stage 16-1).
router = APIRouter(prefix="/api", tags=["equipment"], dependencies=[Depends(require_viewer)])


@router.get("/equipment-types", response_model=list[EquipmentTypeOut])
async def list_equipment_types(session: AsyncSession = Depends(get_session)) -> list[EquipmentTypeOut]:
    """등록된 설비유형, 유형별 설비 수, 감점 항목 메타데이터(화면 라벨용)."""
    return await equipment_service.list_equipment_types(session)


@router.get("/equipment", response_model=list[EquipmentSummary])
async def list_equipment(
    factory_code: str | None = None,
    ef_code: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[EquipmentSummary]:
    """ef_code를 주면 그 설비유형만, 없으면 모든 유형."""
    return await equipment_service.list_equipment(session, factory_code=factory_code, ef_code=ef_code)


@router.get("/equipment/{equipment_id}", response_model=EquipmentDetail)
async def get_equipment(
    equipment_id: int,
    session: AsyncSession = Depends(get_session),
) -> EquipmentDetail:
    detail = await equipment_service.get_equipment_detail(session, equipment_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return detail


@router.get("/equipment/{equipment_id}/history", response_model=list[ScoreHistoryPoint])
async def get_equipment_history(equipment_id: int, session: AsyncSession = Depends(get_session)) -> list[ScoreHistoryPoint]:
    """설비의 점수 이력(점수 기준일 오름차순) — 점수를 계산·갱신할 때마다 그날 점수가 남는다(Stage 21-3)."""
    history = await equipment_service.get_score_history(session, equipment_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return history


@router.get("/summary", response_model=SummaryKPI)
async def get_summary(ef_code: str | None = None, session: AsyncSession = Depends(get_session)) -> SummaryKPI:
    """ef_code를 주면 그 유형만 집계. by_type에 유형별 합계가 함께 온다."""
    return await equipment_service.get_summary(session, ef_code=ef_code)
