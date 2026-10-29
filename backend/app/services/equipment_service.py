"""라우터는 이 모듈을 통해서만 DB에 접근한다 (직접 쿼리 금지 — 루트 CLAUDE.md 규칙).

공통 테이블(equipment/score_snapshot)만 직접 읽고, 유형별 정보(최근 진단일, 상세, 점수 예측용
입력 복원)는 레지스트리의 설비유형 모듈에 맡긴다(Stage 8-4).
"""
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Equipment, ScoreSnapshot
from app.equipment_types.base import EquipmentTypeModule
from app.equipment_types.registry import UnknownEquipmentTypeError, all_modules, get_module
from app.schemas.equipment import (
    BreakdownItem,
    EquipmentDetail,
    EquipmentStatus,
    EquipmentSummary,
    EquipmentTypeOut,
    ProjectionPoint,
    ScoreSnapshotOut,
    SummaryKPI,
    TypeKPI,
)

PROJECTION_YEARS = 5


def classify_status(pof: int, cof: int, dof: int) -> EquipmentStatus:
    """정상/교체검토/즉시교체 3단계 판정.

    COF·DOF가 둘 다 60 초과면 완화된 POF 기준(정상 >50 / 교체검토 30~50 / 즉시교체 <30)을,
    그렇지 않으면 엄격한 POF 기준(정상 >60 / 교체검토 40~60 / 즉시교체 <40)을 적용한다.
    모든 설비유형에 같은 기준을 쓴다(EF2 도입 시 확인, docs/DATA_DICTIONARY.md).
    """
    if cof > 60 and dof > 60:
        normal_bar, replace_bar = 50, 30
    else:
        normal_bar, replace_bar = 60, 40

    if pof > normal_bar:
        return "normal"
    if pof >= replace_bar:
        return "review"
    return "replace"


async def list_equipment(
    session: AsyncSession, factory_code: str | None = None, ef_code: str | None = None
) -> list[EquipmentSummary]:
    stmt = select(Equipment, ScoreSnapshot).join(ScoreSnapshot, ScoreSnapshot.equipment_id == Equipment.equipment_id)
    if factory_code:
        stmt = stmt.where(Equipment.factory_code == factory_code)
    if ef_code:
        stmt = stmt.where(Equipment.ef_code == ef_code)
    rows = (await session.execute(stmt)).all()

    # 최근 진단일은 유형마다 기준 측정이 달라(EF1 DGA, EF2 SF6) 유형별로 한 번씩 모아서 조회한다.
    ids_by_type: dict[str, list[int]] = defaultdict(list)
    for equipment, _ in rows:
        ids_by_type[equipment.ef_code].append(equipment.equipment_id)
    diag_dates: dict[int, date] = {}
    for code, ids in ids_by_type.items():
        try:
            diag_dates.update(await get_module(code).last_diag_dates(session, ids))
        except UnknownEquipmentTypeError:
            continue  # 레지스트리에서 빠진 유형의 잔여 데이터 — 진단일 없이 표시

    summaries = [
        EquipmentSummary(
            equipment_id=equipment.equipment_id,
            factory_code=equipment.factory_code,
            ef_code=equipment.ef_code,
            equipment_name=equipment.equipment_name,
            voltage=equipment.voltage,
            operation_start_time=equipment.operation_start_time,
            pof=score.pof,
            cof=score.cof,
            dof=score.dof,
            total_score=score.total_score,
            status=classify_status(score.pof, score.cof, score.dof),
            last_diag_date=diag_dates.get(equipment.equipment_id),
        )
        for equipment, score in rows
    ]
    summaries.sort(key=lambda item: item.total_score)
    return summaries


async def _projection(session: AsyncSession, module: EquipmentTypeModule, equipment_id: int) -> list[ProjectionPoint]:
    """저장된 입력으로 기준일만 N년씩 늦춰 같은 공식으로 재계산한다 — 0년차는 저장된 점수와 같다."""
    loaded = await module.load_inputs(session, equipment_id)
    if loaded is None:
        return []
    input_row, base_date = loaded
    points = []
    for years in range(PROJECTION_YEARS + 1):
        # 공식이 경과일수/365로 연수를 계산하므로 365일 단위로 늘려야 정확히 +N년이 된다.
        as_of = base_date + timedelta(days=365 * years)
        calc = module.calculate(input_row, as_of=as_of)
        points.append(
            ProjectionPoint(
                years_ahead=years,
                as_of=as_of,
                pof=calc["pof"],
                cof=calc["cof"],
                dof=calc["dof"],
                total_score=calc["total_score"],
            )
        )
    return points


async def get_equipment_detail(session: AsyncSession, equipment_id: int) -> EquipmentDetail | None:
    equipment = await session.get(Equipment, equipment_id)
    score = await session.get(ScoreSnapshot, equipment_id)
    if equipment is None or score is None:
        return None
    try:
        module = get_module(equipment.ef_code)
    except UnknownEquipmentTypeError:
        return None
    type_detail = await module.load_detail(session, equipment_id)
    if type_detail is None:
        return None

    return EquipmentDetail(
        equipment_id=equipment.equipment_id,
        factory_code=equipment.factory_code,
        ef_code=equipment.ef_code,
        ef_name=module.EF_NAME,
        equipment_name=equipment.equipment_name,
        voltage=equipment.voltage,
        operation_start_time=equipment.operation_start_time,
        status=classify_status(score.pof, score.cof, score.dof),
        score=ScoreSnapshotOut.model_validate(score),
        type_detail=type_detail,
        projection=await _projection(session, module, equipment_id),
    )


async def get_summary(session: AsyncSession, ef_code: str | None = None) -> SummaryKPI:
    stmt = select(
        Equipment.ef_code, ScoreSnapshot.pof, ScoreSnapshot.cof, ScoreSnapshot.dof, ScoreSnapshot.computed_at
    ).join(Equipment, Equipment.equipment_id == ScoreSnapshot.equipment_id)
    if ef_code:
        stmt = stmt.where(Equipment.ef_code == ef_code)
    rows = (await session.execute(stmt)).all()

    statuses_by_type: dict[str, list[EquipmentStatus]] = defaultdict(list)
    for code, pof, cof, dof, _ in rows:
        statuses_by_type[code].append(classify_status(pof, cof, dof))

    names = {module.EF_CODE: module.EF_NAME for module in all_modules()}
    by_type = [
        TypeKPI(
            ef_code=code,
            ef_name=names.get(code, code),
            total_equipment=len(statuses),
            review_count=statuses.count("review"),
            replace_count=statuses.count("replace"),
        )
        for code, statuses in sorted(statuses_by_type.items())
    ]
    return SummaryKPI(
        total_equipment=len(rows),
        review_count=sum(t.review_count for t in by_type),
        replace_count=sum(t.replace_count for t in by_type),
        last_updated=max((computed_at for *_, computed_at in rows), default=None),
        by_type=by_type,
    )


async def list_equipment_types(session: AsyncSession) -> list[EquipmentTypeOut]:
    counts = dict((await session.execute(select(Equipment.ef_code, func.count()).group_by(Equipment.ef_code))).all())
    return [
        EquipmentTypeOut(
            ef_code=module.EF_CODE,
            ef_name=module.EF_NAME,
            equipment_count=counts.get(module.EF_CODE, 0),
            breakdown={axis: [BreakdownItem(**item) for item in items] for axis, items in module.BREAKDOWN.items()},
        )
        for module in all_modules()
    ]
