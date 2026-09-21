"""라우터는 이 모듈을 통해서만 DB에 접근한다 (직접 쿼리 금지 — 루트 CLAUDE.md 규칙)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    DesignAttribute,
    DgaReading,
    DielectricTest,
    Equipment,
    FuranReading,
    LoadCondition,
    OilTest,
    PeriodicInspection,
    ScoreSnapshot,
    TransformerScoreDetail,
)
from app.schemas.equipment import (
    DesignAttributeOut,
    DgaReadingOut,
    DielectricTestOut,
    EquipmentDetail,
    EquipmentStatus,
    EquipmentSummary,
    FuranReadingOut,
    LoadConditionOut,
    OilTestOut,
    PeriodicInspectionOut,
    ScoreSnapshotOut,
    SummaryKPI,
    TransformerScoreDetailOut,
)


def classify_status(pof: int, cof: int, dof: int) -> EquipmentStatus:
    """정상/교체검토/즉시교체 3단계 판정.

    COF·DOF가 둘 다 60 초과면 완화된 POF 기준(정상 >50 / 교체검토 30~50 / 즉시교체 <30)을,
    그렇지 않으면 엄격한 POF 기준(정상 >60 / 교체검토 40~60 / 즉시교체 <40)을 적용한다.
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


async def list_equipment(session: AsyncSession, factory_code: str | None = None) -> list[EquipmentSummary]:
    stmt = (
        select(Equipment, ScoreSnapshot, DgaReading.diag_time)
        .join(ScoreSnapshot, ScoreSnapshot.equipment_id == Equipment.equipment_id)
        .join(DgaReading, DgaReading.equipment_id == Equipment.equipment_id)
    )
    if factory_code:
        stmt = stmt.where(Equipment.factory_code == factory_code)

    rows = (await session.execute(stmt)).all()
    summaries = [
        EquipmentSummary(
            equipment_id=equipment.equipment_id,
            factory_code=equipment.factory_code,
            ef_code=equipment.ef_code,
            transformer_name=equipment.transformer_name,
            voltage=equipment.voltage,
            pof=score.pof,
            cof=score.cof,
            dof=score.dof,
            total_score=score.total_score,
            status=classify_status(score.pof, score.cof, score.dof),
            last_diag_date=diag_time,
        )
        for equipment, score, diag_time in rows
    ]
    summaries.sort(key=lambda item: item.total_score)
    return summaries


async def get_equipment_detail(session: AsyncSession, equipment_id: int) -> EquipmentDetail | None:
    equipment = await session.get(Equipment, equipment_id)
    if equipment is None:
        return None

    dga = await session.get(DgaReading, equipment_id)
    furan = await session.get(FuranReading, equipment_id)
    dielectric = await session.get(DielectricTest, equipment_id)
    oil = await session.get(OilTest, equipment_id)
    load = await session.get(LoadCondition, equipment_id)
    inspection = await session.get(PeriodicInspection, equipment_id)
    design = await session.get(DesignAttribute, equipment_id)
    score = await session.get(ScoreSnapshot, equipment_id)
    detail = await session.get(TransformerScoreDetail, equipment_id)

    return EquipmentDetail(
        equipment_id=equipment.equipment_id,
        factory_code=equipment.factory_code,
        ef_code=equipment.ef_code,
        transformer_name=equipment.transformer_name,
        voltage=equipment.voltage,
        onan_val=equipment.onan_val,
        onaf_val=equipment.onaf_val,
        operation_start_time=equipment.operation_start_time,
        status=classify_status(score.pof, score.cof, score.dof),
        dga=DgaReadingOut.model_validate(dga),
        furan=FuranReadingOut.model_validate(furan),
        dielectric=DielectricTestOut.model_validate(dielectric),
        oil=OilTestOut.model_validate(oil),
        load=LoadConditionOut.model_validate(load),
        inspection=PeriodicInspectionOut.model_validate(inspection),
        design=DesignAttributeOut.model_validate(design),
        score=ScoreSnapshotOut.model_validate(score),
        score_detail=TransformerScoreDetailOut.model_validate(detail),
    )


async def get_summary(session: AsyncSession) -> SummaryKPI:
    stmt = select(ScoreSnapshot.pof, ScoreSnapshot.cof, ScoreSnapshot.dof, ScoreSnapshot.computed_at)
    rows = (await session.execute(stmt)).all()
    total = len(rows)
    statuses = [classify_status(pof, cof, dof) for pof, cof, dof, _ in rows]
    review = sum(1 for s in statuses if s == "review")
    replace = sum(1 for s in statuses if s == "replace")
    last_updated = max((computed_at for *_, computed_at in rows), default=None)
    return SummaryKPI(total_equipment=total, review_count=review, replace_count=replace, last_updated=last_updated)
