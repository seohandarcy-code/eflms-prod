"""Stage 15-1 — EF7(배터리) 계산기·적재·임포트 검증.

- 원본(ref_data/schema_eflms_battery.py)과 같은 입력·같은 참고표 → 모든 계산 컬럼이 같은지(감점만 소수 첫째 자리)
- 참고표: 방전인덱스합(같은 사업장 + 설치일 이후), 온도감소계수((1~n년 합 + 소수 보정) × 온도 배율), 빈 표 → 0,
  참고표 없이 호출하면 오류
- 감점 분기별 정답값(mock 범위에선 안 나오는 분기 포함)
- mock 생성값·목업 참고표가 임포트 허용값을 통과하는지, 허용값 밖은 거부되는지
- 전압 컬럼 없는 파일 → equipment.voltage = 0, N/A 배터리실온도 → SOH·BMS·온도 감점 0
- 다른 유형·참고표와 공존(EF7 교체·리셋해도 참고표와 다른 유형 불변), 상세 API, 마이그레이션 왕복
"""
import importlib.util
import random
import sqlite3
import sys
from datetime import date, timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from app.core.config import BACKEND_DIR, get_settings
from app.db.models import (
    BatteryCondition,
    BatteryConsequenceAttribute,
    BatteryDesignAttribute,
    BatteryDischargeHistory,
    BatteryScoreDetail,
    BatterySpec,
    BatteryTempDecayCoef,
    Equipment,
    ScoreSnapshot,
)
from app.equipment_types import ef6_vdp, ef7_battery
from app.equipment_types.rounding import round1
from app.services.dataset_service import count_type, reset_type
from app.services.import_service import _check_allowed, import_file
from app.services.ingest import ingest_row
from app.services.reference_data import calc_options, ensure_mock_reference, mock_reference
from app.services.reference_service import _check_row_extra

from tests.reference_rules import expected_from_reference

REF_PATH = BACKEND_DIR.parent / "ref_data" / "schema_eflms_battery.py"
CALC_NAMES = [c["name"] for c in ef7_battery.CALCULATED_COLUMNS]
MOCK_REF = mock_reference(ef7_battery)
# 원본이 소수를 내는 감점 — 소수 첫째 자리로 반올림한다(2026-11-16 사용자 결정)


@pytest.fixture(scope="module")
def ref():
    """원본 계산 툴을 import만 한다 — ref_data/는 읽기 전용이라 __pycache__도 만들지 않는다."""
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("ref_schema_eflms_battery", REF_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = prev
    return module


def _calc(row, reference=MOCK_REF, **kw):
    return ef7_battery.calculate(row, reference=reference, **kw)


def _expected(ref, row):
    """원본 결과에 우리 반올림 규칙을 적용한 값 — 감점을 먼저 소수 첫째 자리로 반올림하고, 축 감점은
    (반올림된 감점)의 합, 축 점수는 100 + 축 감점이다(화면의 POF = 100 + 감점이 항상 맞도록)."""
    return expected_from_reference(ref, row)


def _years_ago(years):
    return date.today() - timedelta(days=int(years * 365))


def _base_row(**overrides):
    """감점이 0인 기준 입력(오늘 설치, 25℃, 부하 0, 전부 최상) + 덮어쓸 값."""
    row = {
        "factory_code": "H1", "EF_code": "EF7", "eqp_id": "bat1", "line_no": "11L", "manufacturer": "삼성SDI",
        "model_name": "AVC2", "operation_start_time": date.today(), "vol_diff": 0.0, "temp_diff": 0.0,
        "temp_range_over": 0.0, "bat_room_temp": 25.0, "bat_room_humid": 50.0, "capa": 500.0, "load": 0.0,
        "con_rank": "단독", "ins_build_rank": "C", "fire_spread_rank": "B", "emerge_resp": "C", "rep_time": "C",
        "rep_cost": "C", "model_gen": 4, "fire_resist": "O", "ul_auth": "취득", "fac_rel": 3,
        "part_stat_diag": "적용", "bat_server": "적용", "bat_room_fire_resist": "수계",
    }
    row.update(overrides)
    return row


# 방전이력이 없는 사업장 — 온도감소계수·BMS만 따로 볼 때(방전인덱스합 0)
NO_HISTORY = {"factory_code": "Z9"}

# (덮어쓸 입력, 확인할 계산 컬럼, 기대값) — mock 범위에서 한 번도 안 나오는 분기(*)도 전부 포함
BRANCHES = [
    ({"operation_start_time": _years_ago(12.5)}, "age_minus", -12.5),  # 소수 그대로(2026-11-19, 원본은 floor → -12)
    # 방전인덱스합 — 목업 참고표 H1 10건 중 설치일 이후만(원본 코드대로 날짜 비교, 같은 날 포함)
    ({"operation_start_time": date(2005, 1, 1)}, "disch_index", 103.085),  # H1 전체
    ({"operation_start_time": date(2021, 9, 1)}, "disch_index", 40.114),   # 2021-07-21은 설치 전이라 빠짐
    ({"operation_start_time": date(2026, 9, 12)}, "disch_index", 15.88),   # 설치일 당일 방전 포함
    ({"operation_start_time": date(2026, 9, 13)}, "disch_index", 0),
    ({"factory_code": "P1", "operation_start_time": date(2026, 1, 1)}, "disch_index", 0),  # P1은 2025-08-26이 마지막
    # 온도감소계수 — 1~n년 합 + 소수부분 × (n+1)년, 25℃ = 1배
    ({**NO_HISTORY, "operation_start_time": _years_ago(3)}, "temp_dec_coef", 9.8),   # 3.5734+3.2413+2.9401
    ({**NO_HISTORY, "operation_start_time": _years_ago(2.5)}, "temp_dec_coef", 8.3),  # 6.8147 + 0.5×2.9401
    ({**NO_HISTORY, "operation_start_time": _years_ago(0.5)}, "temp_dec_coef", 1.8),  # 0 + 0.5×3.5734
    ({**NO_HISTORY, "operation_start_time": _years_ago(3), "bat_room_temp": 20.0}, "temp_dec_coef", 8.8),  # × 0.901
    ({**NO_HISTORY, "operation_start_time": _years_ago(3), "bat_room_temp": 30.0}, "temp_dec_coef", 10.8),  # × 1.106
    ({**NO_HISTORY, "operation_start_time": _years_ago(25)}, "temp_dec_coef", 33.0),  # * 20년 넘으면 표 끝까지 합
    ({**NO_HISTORY, "operation_start_time": _years_ago(3)}, "soh_minus", -19.6),      # -2 × 9.8
    ({**NO_HISTORY, "operation_start_time": _years_ago(10)}, "bms_minus", -4.6),
    ({**NO_HISTORY, "operation_start_time": _years_ago(10), "bat_room_temp": 30.0}, "bms_minus", -4.8),
    ({"vol_diff": 0.25}, "vol_diff_minus", 0), ({"vol_diff": 0.26}, "vol_diff_minus", -1.2),  # *
    ({"vol_diff": 0.3}, "vol_diff_minus", -6.0),  # *
    ({"temp_diff": 5.0}, "temp_diff_minus", 0), ({"temp_diff": 5.3}, "temp_diff_minus", -0.7),  # * -0.72
    ({"temp_diff": 6.0}, "temp_diff_minus", -2.4),  # *
    ({"temp_range_over": 2.0}, "temp_range_over_minus", -3.0),  # *
    ({"bat_room_temp": 18.0}, "bat_room_temp_minus", -3), ({"bat_room_temp": 18.1}, "bat_room_temp_minus", 0),  # * 경계 포함 감점
    ({"bat_room_temp": 28.0}, "bat_room_temp_minus", -3), ({"bat_room_temp": 30.0}, "bat_room_temp_minus", -3),  # *
    ({"bat_room_humid": 79.9}, "bat_room_humid_minus", 0), ({"bat_room_humid": 80.0}, "bat_room_humid_minus", -3),  # *
    ({"load": 55.0}, "capa_times_load_minus", -3.3), ({"load": 55.0, "capa": 800.0}, "capa_times_load_minus", -5.3),
    ({"con_rank": "공용"}, "con_rank_minus", -3),
    ({"ins_build_rank": "A"}, "ins_build_rank_minus", -6), ({"ins_build_rank": "B"}, "ins_build_rank_minus", -3),
    ({"fire_spread_rank": "A"}, "fire_spread_rank_minus", -3),
    ({"emerge_resp": "A"}, "emerge_resp_minus", -2), ({"emerge_resp": "B"}, "emerge_resp_minus", -1),
    ({"rep_time": "A"}, "rep_time_minus", -2), ({"rep_cost": "B"}, "rep_cost_minus", -1),
    ({"model_gen": 2}, "model_gen_minus", -12), ({"model_gen": 3}, "model_gen_minus", -6),
    ({"fire_resist": "X"}, "fire_resist_minus", -12),
    ({"ul_auth": "미취득"}, "ul_auth_minus", -12),
    ({"fac_rel": 2}, "fac_rel_minus", -8),  # * mock은 4~12
    ({"part_stat_diag": "미적용"}, "part_stat_diag_minus", -4),
    ({"bat_server": "미적용"}, "bat_server_minus", -2),  # *
    ({"bat_room_fire_resist": "가스계"}, "bat_room_fire_resist_minus", -8),
]


@pytest.mark.parametrize(("overrides", "column", "expected"), BRANCHES)
def test_deduction_branches(overrides, column, expected):
    assert _calc(_base_row(**overrides))[column] == expected


def test_base_row_totals():
    base = _calc(_base_row())
    assert (base["pof"], base["cof"], base["dof"], base["total_score"]) == (100, 100, 100, 100)


def test_reference_is_required():
    with pytest.raises(ValueError, match="참고표"):
        ef7_battery.calculate(_base_row())


def test_empty_reference_tables_count_as_zero():
    """원본 수식이 합계 방식이라 빈 참고표는 오류가 아니라 0이다(2026-11-16 결정)."""
    out = _calc(_base_row(operation_start_time=date(2016, 1, 1)), reference={"discharge_history": [], "temp_decay_coef": []})
    assert (out["disch_index"], out["temp_dec_coef"], out["soh_minus"]) == (0, 0, 0)


def test_calculation_follows_the_reference_it_is_given():
    row = _base_row(operation_start_time=date(2016, 1, 1))
    doubled = {
        "discharge_history": [{**h, "disch_index": h["disch_index"] * 2} for h in MOCK_REF["discharge_history"]],
        "temp_decay_coef": [{**t, "gamma_y": t["gamma_y"] * 2} for t in MOCK_REF["temp_decay_coef"]],
    }
    base, more = _calc(row), _calc(row, reference=doubled)
    assert more["disch_index"] == pytest.approx(base["disch_index"] * 2)
    assert more["soh_minus"] < base["soh_minus"]


def test_one_decimal_scores():
    out = _calc(_base_row(temp_diff=5.3, load=55.0))
    assert out["pof_minus"] == -0.7 and out["pof"] == 99.3
    assert out["cof"] == 96.7
    assert out["total_score"] == round1(0.5 * 99.3 + 0.3 * 96.7 + 0.2 * 100)


def test_voltage_is_filled_with_zero_and_reference_is_not_returned():
    out = _calc(_base_row())
    assert "voltage" not in {c["name"] for c in ef7_battery.INPUT_COLUMNS}
    assert out["voltage"] == 0
    assert "_reference" not in out and "_as_of" not in out


def test_na_room_temperature_zeroes_temperature_based_deductions():
    """배터리실온도가 N/A면 온도감소계수(→ SOH 전체)·BMS·배터리실온도 감점이 평가되지 않는다(감점 0)."""
    out = _calc(_base_row(operation_start_time=date(2016, 1, 1), bat_room_temp=None))
    assert (out["soh_minus"], out["bms_minus"], out["bat_room_temp_minus"]) == (0, 0, 0)
    assert out["temp_dec_coef"] is None and out["bms_stat"] is None
    assert out["disch_index"] == 103.085 and out["age_minus"] == -out["operation_year"]


def test_matches_reference_formulas(ref):
    random.seed(20261116)
    rows = [ef7_battery.generate_input_row() for _ in range(300)]
    rows += [_base_row(**overrides) for overrides, _, _ in BRANCHES]
    rows += [_base_row(operation_start_time=date(2015, 1, 1) + timedelta(days=d), factory_code=f, temp_diff=5.3)
             for d in range(0, 4000, 97) for f in ("H1", "H2", "K1", "P1")]
    for row in rows:
        ours = _calc(row)
        theirs = _expected(ref, row)
        for name in CALC_NAMES:
            assert ours[name] == theirs[name], (name, row)


def test_columns_and_mock_reference_match_source(ref):
    assert [c["name"] for c in ef7_battery.INPUT_COLUMNS] == [c["name"] for c in ref.INPUT_COLUMNS]
    assert CALC_NAMES == [c["name"] for c in ref.CALCULATED_COLUMNS]
    assert ef7_battery.MOCK_DISCHARGE_HISTORY == ref.DISCHARGE_HISTORY
    assert ef7_battery.MOCK_TEMP_DECAY_COEF == ref.TEMP_DECAY_COEF


def test_breakdown_covers_every_summed_deduction():
    """메타데이터 항목 = 원본 합계식에 들어가는 감점 전부(그룹 없음 — 원본에 소계가 없다)."""
    bd = ef7_battery.BREAKDOWN
    assert (len(bd["pof"]), len(bd["cof"]), len(bd["dof"])) == (8, 7, 7)
    assert not any("group" in item for axis in bd.values() for item in axis)
    row = _calc(_base_row(
        operation_start_time=date(2016, 5, 1), vol_diff=0.3, temp_diff=6.2, temp_range_over=1.0, bat_room_temp=29.0,
        bat_room_humid=85.0, load=58.0, con_rank="공용", ins_build_rank="A", model_gen=2, ul_auth="미취득", fac_rel=1,
    ))
    for axis in ("pof", "cof", "dof"):
        assert round1(sum(row[i["field"]] for i in bd[axis])) == row[f"{axis}_minus"], axis


def test_mock_rows_pass_import_validation_and_calculate():
    random.seed(7)
    for _ in range(1000):
        row = ef7_battery.generate_input_row()
        for col in ef7_battery.INPUT_COLUMNS:
            assert _check_allowed(row[col["name"]], col) is None, (col["name"], row[col["name"]])
        calc = _calc(row)
        assert 0 <= calc["cof"] <= 100 and 0 <= calc["dof"] <= 100


def test_mock_reference_rows_pass_reference_validation():
    for name, spec in ef7_battery.REFERENCE_TABLES.items():
        assert [c["name"] for c in spec["columns"]] == list(spec["mock_rows"][0])
        keys = [tuple(r[k] for k in spec["key"]) for r in spec["mock_rows"]]
        assert len(keys) == len(set(keys)), name
        for row in spec["mock_rows"]:
            for col in spec["columns"]:
                value = row[col["name"]]
                assert _check_allowed(value, col) is None and _check_row_extra(value, col) is None, (name, col["name"], value)


# ------------------------------------------------------------------ 임포트
def _fmt(v):
    return v.isoformat() if isinstance(v, date) else str(v)


def _write_ef7_dat(tmp_path, rows, name="ef7.dat"):
    names = [c["name"] for c in ef7_battery.INPUT_COLUMNS]
    lines = ["\t".join(names)] + ["\t".join(_fmt(r[n]) for n in names) for r in rows]
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


async def test_import_uses_reference_tables_in_db(session_factory, tmp_path):
    """참고표가 비어 있으면 경고만 하고 0으로 계산, 참고표를 넣은 뒤 다시 넣으면 그 표로 계산한다."""
    row = _base_row(eqp_id="bat9", operation_start_time=date(2016, 1, 1))
    async with session_factory() as session:
        result = await import_file(_write_ef7_dat(tmp_path, [row]), "EF7", session)
        assert result.ok, (result.file_errors, result.row_errors)
        assert len(result.reference_warnings) == 2
        assert (await session.execute(select(BatteryScoreDetail.disch_index))).scalar_one() == 0

        await ensure_mock_reference(session, ef7_battery)
        await session.commit()
        result = await import_file(_write_ef7_dat(tmp_path, [row]), "EF7", session)
        assert result.ok and result.reference_warnings == []
        detail = (await session.execute(select(BatteryScoreDetail))).scalar_one()
        assert detail.disch_index == 103.085
        assert detail.soh_minus == _calc(row)["soh_minus"]


async def test_import_valid_ef7_file_fills_all_battery_tables(session_factory, tmp_path):
    rows = [ef7_battery.generate_input_row() for _ in range(4)]
    async with session_factory() as session:
        await ensure_mock_reference(session, ef7_battery)
        await session.commit()
        result = await import_file(_write_ef7_dat(tmp_path, rows), "EF7", session)
        assert result.ok, (result.file_errors, result.row_errors)
        assert result.imported_rows == 4
        for model in (BatterySpec, BatteryCondition, BatteryConsequenceAttribute, BatteryDesignAttribute, BatteryScoreDetail):
            assert await session.scalar(select(func.count()).select_from(model)) == 4, model.__tablename__
        stored = (await session.execute(select(Equipment).where(Equipment.ef_code == "EF7"))).scalars().all()
        assert sorted(e.equipment_name for e in stored) == sorted(r["eqp_id"] for r in rows)
        assert {e.voltage for e in stored} == {0}


@pytest.mark.parametrize(
    ("column", "bad_value", "reason_part"),
    [
        ("con_rank", "공유", "허용값 아님"),
        ("fire_spread_rank", "C", "허용값 아님"),  # 원본 판정은 A·B뿐
        ("model_gen", 5, "허용값 아님"),
        ("ul_auth", "UI", "허용값 아님"),
        ("bat_room_fire_resist", "분말", "허용값 아님"),
        ("bat_room_humid", 100.5, "초과"),
        ("vol_diff", -0.1, "미만"),
        ("fac_rel", -1, "미만"),
        ("line_no", "", "빈 값"),
    ],
)
async def test_import_rejects_out_of_range_values(session_factory, tmp_path, column, bad_value, reason_part):
    rows = [ef7_battery.generate_input_row() for _ in range(3)]
    rows[1][column] = bad_value
    async with session_factory() as session:
        result = await import_file(_write_ef7_dat(tmp_path, rows), "EF7", session)
        assert not result.ok
        assert [(e.row_number, e.column) for e in result.row_errors] == [(3, column)]
        assert reason_part in result.row_errors[0].reason
        assert await count_type(session, "EF7") == 0


async def test_import_na_room_temperature_is_stored_as_null(session_factory, tmp_path):
    rows = [ef7_battery.generate_input_row() for _ in range(2)]
    rows[0]["bat_room_temp"] = "N/A"
    async with session_factory() as session:
        result = await import_file(_write_ef7_dat(tmp_path, rows), "EF7", session)
        assert result.ok, result.row_errors
        assert result.na_values == {"bat_room_temp": 1}
        temps = (await session.execute(select(BatteryCondition.bat_room_temp))).scalars().all()
        assert None in temps


# ------------------------------------------------------------------ 다른 유형·참고표와 공존
async def _seed(session, n):
    await ensure_mock_reference(session, ef7_battery)
    options = await calc_options(session, ef7_battery)
    for _ in range(n):
        await ingest_row(ef7_battery.calculate(ef7_battery.generate_input_row(), **options), session)


async def _others_fingerprint(session):
    return (
        await session.execute(
            select(Equipment.equipment_id, Equipment.ef_code, Equipment.equipment_name, ScoreSnapshot.total_score)
            .join(ScoreSnapshot, ScoreSnapshot.equipment_id == Equipment.equipment_id)
            .where(Equipment.ef_code != "EF7")
            .order_by(Equipment.equipment_id)
        )
    ).all()


async def _reference_counts(session):
    return [await session.scalar(select(func.count()).select_from(m)) for m in (BatteryDischargeHistory, BatteryTempDecayCoef)]


async def test_ef7_replace_import_and_reset_keep_reference_and_other_types(client, session_factory, tmp_path):
    async with session_factory() as session:
        for _ in range(2):
            await ingest_row(ef6_vdp.calculate(ef6_vdp.generate_input_row()), session)
        await _seed(session, 5)
        await session.commit()
        before = await _others_fingerprint(session)
        assert {r.ef_code for r in before} == {"EF1", "EF6"} and await count_type(session, "EF7") == 5
        assert await _reference_counts(session) == [40, 20]

        result = await import_file(_write_ef7_dat(tmp_path, [ef7_battery.generate_input_row() for _ in range(2)]), "EF7", session, replace=True)
        assert result.ok and result.replaced_rows == 5 and result.imported_rows == 2
        assert await count_type(session, "EF7") == 2
        assert await _others_fingerprint(session) == before
        assert await _reference_counts(session) == [40, 20]  # 설비 교체는 참고표를 건드리지 않는다

        assert await reset_type(session, "EF7") == 2
        await session.commit()
        assert await count_type(session, "EF7") == 0
        assert await _reference_counts(session) == [40, 20]  # 설비 리셋도 참고표는 남긴다
        assert await _others_fingerprint(session) == before


async def test_ef7_detail_and_metadata_api(client, session_factory):
    async with session_factory() as session:
        await ensure_mock_reference(session, ef7_battery)
        options = await calc_options(session, ef7_battery)
        row = _base_row(eqp_id="bat77", operation_start_time=date(2018, 3, 1), temp_diff=5.3)
        eq_id = await ingest_row(ef7_battery.calculate(row, **options), session)
        await session.commit()

    body = (await client.get(f"/api/equipment/{eq_id}")).json()
    assert body["ef_code"] == "EF7" and body["ef_name"] == "배터리"
    td = body["type_detail"]
    assert td["ef_code"] == "EF7"
    assert {"spec", "condition", "consequence", "design", "score_detail"} <= td.keys()
    assert td["score_detail"]["temp_diff_minus"] == -0.7
    assert td["score_detail"]["disch_index"] == _calc(row)["disch_index"]
    assert body["score"]["pof"] == round1(body["score"]["pof"])
    projection = body["projection"]
    assert projection[0]["total_score"] == body["score"]["total_score"]  # 0년차 = 저장 점수(같은 참고표)
    assert projection[-1]["pof"] < projection[0]["pof"]  # 년수가 늘면 온도감소계수가 커진다

    items = (await client.get("/api/equipment", params={"ef_code": "EF7"})).json()
    assert [i["ef_code"] for i in items] == ["EF7"]
    assert items[0]["last_diag_date"] == date.today().isoformat()
    types = {t["ef_code"]: t for t in (await client.get("/api/equipment-types")).json()}
    assert types["EF7"]["equipment_count"] == 1 and types["EF7"]["ef_name"] == "배터리"
    assert types["EF7"]["breakdown"]["pof"][1] == {"field": "soh_minus", "label": "SOH", "group": None, "summed": True}


# ------------------------------------------------------------------ 마이그레이션
def test_battery_migration_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "battery_migrate.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    def tables():
        with sqlite3.connect(db_path) as conn:
            return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    try:
        cfg = Config()
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        battery_tables = {m.__tablename__ for m in ef7_battery.DOMAIN_TABLES} | {
            s["model"].__tablename__ for s in ef7_battery.REFERENCE_TABLES.values()
        }
        assert len(battery_tables) == 7

        command.upgrade(cfg, "head")
        assert battery_tables <= tables()

        command.downgrade(cfg, "95615a3edbeb")
        assert not battery_tables & tables()
        assert {"vdp_spec", "ups_spec", "switchgear_spec", "transformer_spec", "equipment"} <= tables()

        command.upgrade(cfg, "head")
        assert battery_tables <= tables()
    finally:
        get_settings.cache_clear()
