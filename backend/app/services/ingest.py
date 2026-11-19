"""공용 데이터 적재 매퍼.

mock 시드(app/db/seed.py)와 사내 입력파일 임포트(app/services/import_service.py)가 동일하게
사용하는 함수. `row`는 설비유형 모듈의 calculate()가 만든 "입력+계산 전체" flat dict.

공통 테이블(equipment_type/equipment/score_snapshot)만 여기서 다루고, 유형 전용 테이블은
row["EF_code"]로 찾은 설비유형 모듈의 ingest_domain()에 맡긴다(Stage 8-2, registry.py).

**commit하지 않는다** — 호출하는 쪽이 파일/배치 단위로 한 번만 commit해서, 중간에 실패하면
통째로 rollback되게 한다(부분 반영 금지).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now_kst_naive, today_kst
from app.db.models import Equipment, EquipmentType, ScoreHistory, ScoreSnapshot
from app.equipment_types.base import EquipmentTypeModule
from app.equipment_types.registry import get_module


async def _ensure_equipment_type(module: EquipmentTypeModule, session: AsyncSession) -> None:
    if await session.get(EquipmentType, module.EF_CODE) is None:
        session.add(EquipmentType(ef_code=module.EF_CODE, name=module.EF_NAME))
        await session.flush()


async def _get_or_create_equipment(row: dict, module: EquipmentTypeModule, session: AsyncSession) -> Equipment:
    # 유형마다 이름 컬럼이 다르다(EF1 transformer_name 등) — 공통 equipment_name으로 모은다.
    name = row[module.NAME_FIELD]
    stmt = select(Equipment).where(
        Equipment.factory_code == row["factory_code"],
        Equipment.ef_code == module.EF_CODE,
        Equipment.equipment_name == name,
    )
    equipment = (await session.execute(stmt)).scalar_one_or_none()

    if equipment is None:
        equipment = Equipment(
            factory_code=row["factory_code"],
            ef_code=module.EF_CODE,
            equipment_name=name,
            voltage=row["voltage"],
            operation_start_time=row["operation_start_time"],
        )
        session.add(equipment)
    else:
        equipment.voltage = row["voltage"]
        equipment.operation_start_time = row["operation_start_time"]

    await session.flush()  # equipment_id 확보
    return equipment


async def ingest_row(row: dict, session: AsyncSession) -> int:
    """flat dict 한 건을 공통 + 유형 전용 테이블들에 upsert한다. equipment_id를 반환. commit하지 않음."""
    module = get_module(row["EF_code"])
    await _ensure_equipment_type(module, session)

    equipment = await _get_or_create_equipment(row, module, session)
    eq_id = equipment.equipment_id

    await module.ingest_domain(row, eq_id, session)
    await _merge_snapshot(row, eq_id, session)
    await session.flush()
    return eq_id


async def save_scores(row: dict, equipment_id: int, session: AsyncSession) -> None:
    """점수만 저장한다 — 계산 결과 테이블(모듈 ingest_scores) + score_snapshot. 입력 테이블·equipment·미등록
    컬럼은 건드리지 않아 '최근 진단일'(입력 테이블 날짜)이 그대로 남는다(점수 갱신·재계산, Stage 21-1).
    commit하지 않는다."""
    module = get_module(row["EF_code"])
    await module.ingest_scores(row, equipment_id, session)
    await _merge_snapshot(row, equipment_id, session)
    await session.flush()


async def _merge_snapshot(row: dict, equipment_id: int, session: AsyncSession) -> None:
    await _record_history(row, equipment_id, session)
    await session.merge(
        ScoreSnapshot(
            equipment_id=equipment_id,
            pof_minus=row["pof_minus"],
            pof=row["pof"],
            cof_minus=row["cof_minus"],
            cof=row["cof"],
            dof_minus=row["dof_minus"],
            dof=row["dof"],
            total_score=row["total_score"],
        )
    )


async def _record_history(row: dict, equipment_id: int, session: AsyncSession) -> None:
    """점수 이력(Stage 21-3) — 설비(유형·사업장·이름)·점수 기준일마다 한 행, 같은 날 다시 계산하면 마지막 값으로."""
    from app.services.equipment_service import classify_status  # 순환 import 방지

    module = get_module(row["EF_code"])
    key = dict(ef_code=module.EF_CODE, factory_code=row["factory_code"], equipment_name=row[module.NAME_FIELD], as_of=row.get("today") or today_kst())
    values = dict(
        equipment_id=equipment_id,
        pof=row["pof"],
        cof=row["cof"],
        dof=row["dof"],
        total_score=row["total_score"],
        status=classify_status(row["pof"], row["cof"], row["dof"]),
        recorded_at=now_kst_naive(),
    )
    stmt = select(ScoreHistory).where(*(getattr(ScoreHistory, k) == v for k, v in key.items()))
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is None:
        session.add(ScoreHistory(**key, **values))
    else:
        for name, value in values.items():
            setattr(existing, name, value)
