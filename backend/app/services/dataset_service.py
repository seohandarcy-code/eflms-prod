"""설비유형 단위 데이터셋 관리 (Stage 8-2).

리셋을 설비유형 단위로 한다 — EF2 mock을 지웠다 다시 만들어도 EF1 데이터는 그대로 남는다.
commit하지 않는다(호출하는 쪽이 같은 트랜잭션 안에서 재적재까지 마친 뒤 commit).
"""
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Equipment, EquipmentExtraAttribute, ScoreSnapshot
from app.equipment_types.registry import get_module


async def count_type(session: AsyncSession, ef_code: str) -> int:
    return await session.scalar(select(func.count()).select_from(Equipment).where(Equipment.ef_code == ef_code))


async def is_type_empty(session: AsyncSession, ef_code: str) -> bool:
    return await count_type(session, ef_code) == 0


async def reset_type(session: AsyncSession, ef_code: str) -> int:
    """해당 유형 설비와 그 설비에 딸린 행만 지운다. 지운 설비 수를 반환한다.

    순서: 유형 전용 테이블 → 공통 자식(score_snapshot, equipment_extra_attribute) → equipment.
    equipment_type 행(마스터)은 남긴다.
    """
    module = get_module(ef_code)
    equipment_ids = select(Equipment.equipment_id).where(Equipment.ef_code == ef_code)
    removed = await count_type(session, ef_code)

    for model in [*module.DOMAIN_TABLES, ScoreSnapshot, EquipmentExtraAttribute]:
        await session.execute(delete(model).where(model.equipment_id.in_(equipment_ids)))
    await session.execute(delete(Equipment).where(Equipment.ef_code == ef_code))
    return removed
