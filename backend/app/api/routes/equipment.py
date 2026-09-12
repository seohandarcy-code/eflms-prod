from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.equipment import EquipmentDetail, EquipmentSummary, SummaryKPI
from app.services import equipment_service

router = APIRouter(prefix="/api", tags=["equipment"])


@router.get("/equipment", response_model=list[EquipmentSummary])
async def list_equipment(
    factory_code: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[EquipmentSummary]:
    return await equipment_service.list_equipment(session, factory_code=factory_code)


@router.get("/equipment/{equipment_id}", response_model=EquipmentDetail)
async def get_equipment(
    equipment_id: int,
    session: AsyncSession = Depends(get_session),
) -> EquipmentDetail:
    detail = await equipment_service.get_equipment_detail(session, equipment_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return detail


@router.get("/summary", response_model=SummaryKPI)
async def get_summary(session: AsyncSession = Depends(get_session)) -> SummaryKPI:
    return await equipment_service.get_summary(session)
