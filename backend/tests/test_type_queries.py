"""Stage 8-4 — 설비유형별 조회 API.

- 저장값으로 복원한 입력(load_inputs)을 다시 계산하면 저장된 점수·세부 감점과 같아야 한다
  (DB가 계산 입력을 빠짐없이 보관하는지에 대한 검증이기도 하다)
- 점수 예측: 0년차 = 저장 점수, 이후는 같은 공식으로 기준일만 +N년
- /equipment-types 메타데이터, /summary by_type, 유형별 상세 union
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.db.models import Equipment, GisScoreDetail, ScoreSnapshot, TransformerScoreDetail
from app.equipment_types import ef1_transformer, ef2_gis
from app.services.ingest import ingest_row

MODULES = {"EF1": (ef1_transformer, TransformerScoreDetail), "EF2": (ef2_gis, GisScoreDetail)}
# EF1은 계산 결과 키와 DB 컬럼 이름이 다른 항목이 있다(ef1_transformer.ingest_domain의 매핑). EF2는 전부 같다.
DB_TO_CALC = {"oltc_96t_minus": "oltc_96T_minus", "first_voltage": "1st_voltage", "first_voltage_minus": "1st_voltage_minus"}


async def _seed_ef2(session, n=3):
    ids = [await ingest_row(ef2_gis.calculate(ef2_gis.generate_input_row()), session) for _ in range(n)]
    await session.commit()
    return ids


@pytest.mark.parametrize("ef_code", ["EF1", "EF2"])
async def test_load_inputs_round_trip_reproduces_stored_scores(client, session_factory, ef_code):
    module, detail_model = MODULES[ef_code]
    async with session_factory() as session:
        if ef_code == "EF2":
            await _seed_ef2(session)
        ids = (await session.execute(select(Equipment.equipment_id).where(Equipment.ef_code == ef_code))).scalars().all()
        assert ids
        detail_columns = [c.name for c in detail_model.__table__.columns if c.name not in ("equipment_id", "computed_at")]
        for eq_id in ids:
            input_row, as_of = await module.load_inputs(session, eq_id)
            recalculated = module.calculate(input_row, as_of=as_of)
            score = await session.get(ScoreSnapshot, eq_id)
            stored_detail = await session.get(detail_model, eq_id)
            for name in ("pof_minus", "pof", "cof_minus", "cof", "dof_minus", "dof", "total_score"):
                assert recalculated[name] == getattr(score, name), (eq_id, name)
            for name in detail_columns:
                calc_value = recalculated[DB_TO_CALC.get(name, name)]
                assert calc_value == pytest.approx(getattr(stored_detail, name)), (eq_id, name)


@pytest.mark.parametrize("module", [ef1_transformer, ef2_gis])
def test_as_of_default_is_today_and_shifts_operation_year(module):
    row = module.generate_input_row()
    assert module.calculate(row) == module.calculate(row, as_of=date.today())
    now = module.calculate(row)
    later = module.calculate(row, as_of=date.today() + timedelta(days=365))
    assert later["operation_year"] == pytest.approx(now["operation_year"] + 1)
    assert "_as_of" not in now


async def test_detail_projection_starts_at_stored_score(client, session_factory):
    async with session_factory() as session:
        ef2_id = (await _seed_ef2(session, n=1))[0]
        ef1_id = (await session.execute(select(Equipment.equipment_id).where(Equipment.ef_code == "EF1"))).scalars().first()

    for eq_id in (ef1_id, ef2_id):
        body = (await client.get(f"/api/equipment/{eq_id}")).json()
        projection = body["projection"]
        assert [p["years_ahead"] for p in projection] == [0, 1, 2, 3, 4, 5]
        assert projection[0]["pof"] == body["score"]["pof"]
        assert projection[0]["total_score"] == body["score"]["total_score"]
        assert projection[1]["as_of"] > projection[0]["as_of"]
        # 주의: 측정값 고정 재계산이라 시간이 지나면 점수가 오를 수도 있다(EF1 Furan은 총량÷사용년수로 판정)
        # — 그래서 화면은 이 값을 쓰지 않는다(ProjectionPoint docstring).


async def test_ef2_detail_shape(client, session_factory):
    async with session_factory() as session:
        eq_id = (await _seed_ef2(session, n=1))[0]
    body = (await client.get(f"/api/equipment/{eq_id}")).json()
    assert body["ef_code"] == "EF2" and body["ef_name"] == "GIS"
    td = body["type_detail"]
    assert td["ef_code"] == "EF2"
    assert {"operation", "diagnosis", "sf6", "consequence", "design", "score_detail"} <= td.keys()
    assert "cb_stat_minus" in td["score_detail"]


async def test_list_last_diag_date_comes_from_each_type(client, session_factory):
    async with session_factory() as session:
        await _seed_ef2(session, n=2)
    items = (await client.get("/api/equipment")).json()
    by_type = {}
    for item in items:
        by_type.setdefault(item["ef_code"], []).append(item["last_diag_date"])
    assert all(d is not None for d in by_type["EF1"])
    assert set(by_type["EF2"]) == {"2024-11-01"}  # EF2 mock의 SF6 진단일


async def test_summary_by_type_adds_up(client, session_factory):
    async with session_factory() as session:
        await _seed_ef2(session, n=4)
    body = (await client.get("/api/summary")).json()
    by_type = {t["ef_code"]: t for t in body["by_type"]}
    assert by_type["EF1"]["total_equipment"] == 3 and by_type["EF2"]["total_equipment"] == 4
    assert by_type["EF2"]["ef_name"] == "GIS"
    assert body["total_equipment"] == 7
    assert body["review_count"] == sum(t["review_count"] for t in body["by_type"])
    assert body["replace_count"] == sum(t["replace_count"] for t in body["by_type"])


async def test_equipment_types_metadata(client, session_factory):
    async with session_factory() as session:
        await _seed_ef2(session, n=2)
    types = {t["ef_code"]: t for t in (await client.get("/api/equipment-types")).json()}
    assert types["EF1"]["equipment_count"] == 3 and types["EF2"]["equipment_count"] == 2
    ef1_pof = {i["field"]: i for i in types["EF1"]["breakdown"]["pof"]}
    assert ef1_pof["dga_minus"]["summed"] is False  # 원본에서 PoF 합산 제외
    ef2_pof = types["EF2"]["breakdown"]["pof"]
    assert {i["group"] for i in ef2_pof} == {"기계적", "전기적", "화학적"}
    # 메타데이터의 모든 필드는 실제 계산 결과에 존재해야 한다
    for code, (module, _) in MODULES.items():
        calc = module.calculate(module.generate_input_row())
        for axis in ("pof", "cof", "dof"):
            for item in types[code]["breakdown"][axis]:
                assert DB_TO_CALC.get(item["field"], item["field"]) in calc, (code, item["field"])
