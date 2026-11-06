"""Stage 14 — EF6(VDP) 계산기·적재·임포트 검증.

- 원본(ref_data/schema_eflms_vdp.py)과 같은 입력 → 모든 계산 컬럼이 같은지(원본 공식 그대로, 단 소수 첫째 자리 반올림)
- 감점 분기별 정답값(mock 범위에선 안 나오는 분기 포함)
- mock 생성값이 임포트 허용값을 통과하는지, 허용값 밖은 거부되는지
- 전압 컬럼 없는 파일 → 공통 equipment.voltage = 0, N/A 온도 → 부품 고장확률 감점 0
- 다른 유형과 공존(EF6만 교체해도 다른 유형 불변), 마이그레이션 왕복
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
    Equipment,
    ScoreSnapshot,
    VdpCondition,
    VdpConsequenceAttribute,
    VdpDesignAttribute,
    VdpScoreDetail,
    VdpSpec,
)
from app.equipment_types import ef5_ups, ef6_vdp
from app.equipment_types.rounding import round1
from app.services.dataset_service import count_type
from app.services.import_service import _check_allowed, import_file
from app.services.ingest import ingest_row

REF_PATH = BACKEND_DIR.parent / "ref_data" / "schema_eflms_vdp.py"
CALC_NAMES = [c["name"] for c in ef6_vdp.CALCULATED_COLUMNS]
# 원본이 소수를 내는 감점 — 소수 첫째 자리로 반올림한다(2026-11-06 사용자 결정)
ROUNDED_DEDUCTIONS = {"capa_times_load_minus", "thermal_img_chk_minus", "ex_box_chk_minus"}
WEIBULL = ["cb_stat_minus", "cap_stat_minus", "fan_stat_minus", "igbt_stat_minus", "board_stat_minus"]


@pytest.fixture(scope="module")
def ref():
    """원본 계산 툴을 import만 한다 — ref_data/는 읽기 전용이라 __pycache__도 만들지 않는다."""
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("ref_schema_eflms_vdp", REF_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = prev
    return module


def _ref_calculate(ref, row):
    row = dict(row)
    for col in ref.CALCULATED_COLUMNS:
        row[col["name"]] = col["formula"](row)
    return row


def _expected(ref, row):
    """원본 결과에 우리 반올림 규칙을 적용한 값 — 감점을 먼저 소수 첫째 자리로 반올림하고, 축 점수는
    100 + (반올림된 감점)이다(화면의 POF = 100 + 감점이 항상 맞도록). 예: 원본 COF 감점 -40.05 → -40.1,
    COF 59.9(원본 COF 59.95를 바로 반올림한 60.0이 아님)."""
    exp = _ref_calculate(ref, row)
    for name in ROUNDED_DEDUCTIONS:
        exp[name] = round1(exp[name])
    for axis in ("pof", "cof", "dof"):
        exp[f"{axis}_minus"] = round1(exp[f"{axis}_minus"])
        exp[axis] = round1(100 + exp[f"{axis}_minus"])
    exp["total_score"] = round1(0.5 * exp["pof"] + 0.3 * exp["cof"] + 0.2 * exp["dof"])
    return exp


def _years_ago(years):
    return date.today() - timedelta(days=int(years * 365))


def _base_row(**overrides):
    """감점이 0인 기준 입력(오늘 설치, 25℃, 부하 0, 전부 최상) + 덮어쓸 값."""
    row = {
        "factory_code": "H1", "EF_code": "EF6", "eqp_id": "vdp1", "line_no": "11L", "manufacturer": "ABB",
        "model_name": "AVC2", "operation_start_time": date.today(), "fan_replace_no": 0,
        "elec_room_max_temp": 25.0, "load": 0.0, "mod_cir_curr": 0, "mod_vol_diff": 0, "noise": 0,
        "thermal_img_chk": "정상", "ex_box_chk": "정상", "capa": 2500, "ins_build_rank": "C",
        "fire_spread_rank": "C", "emerge_resp": "C", "rep_time": "C", "rep_cost": "C", "sys_rel": "N+N",
        "emerge_sys": "타설비", "fac_rel": "N+1", "part_shortage": "공급가능", "model_type": "공용배터리",
        "switching_type": "3레벨PWM", "igbt_rev": "1200V", "online_diag": "적용",
    }
    row.update(overrides)
    return row


# (덮어쓸 입력, 확인할 계산 컬럼, 기대값) — mock 범위에서 한 번도 안 나오는 분기(*)도 전부 포함
BRANCHES = [
    ({"operation_start_time": _years_ago(12.5)}, "age_minus", -12),
    ({"operation_start_time": _years_ago(12.5)}, "cb_replace_no", 1),
    ({"operation_start_time": _years_ago(7)}, "cb_replace_no", 0),
    ({"operation_start_time": _years_ago(20)}, "cb_replace_no", 1),  # 교체는 최대 1회
    ({"operation_start_time": _years_ago(3.8)}, "board_stat_minus", -14),
    ({"operation_start_time": _years_ago(3.8), "elec_room_max_temp": 28.0}, "board_stat_minus", -17),  # 더울수록 수명 단축
    ({"operation_start_time": _years_ago(3.8)}, "igbt_stat_minus", -2),
    ({"operation_start_time": _years_ago(20), "fan_replace_no": 5}, "fan_life_year", 0),  # * max(0, …)
    ({"operation_start_time": _years_ago(20), "fan_replace_no": 5}, "fan_stat_minus", 0),  # *
    ({"elec_room_max_temp": 22.0}, "elec_room_max_temp_minus", 4),  # 가점, Python round(4.5) → 4
    ({"elec_room_max_temp": 27.0}, "elec_room_max_temp_minus", -3),
    ({"elec_room_max_temp": 28.0}, "elec_room_max_temp_minus", -4),  # round(-4.5) → -4
    ({"load": 95.0}, "load_minus", 0), ({"load": 96.0}, "load_minus", 0),  # * int(-0.75) → 0
    ({"load": 100.0}, "load_minus", -3),  # *
    ({"mod_cir_curr": 6}, "mod_cir_curr_minus", 0), ({"mod_cir_curr": 7}, "mod_cir_curr_minus", -1),  # *
    ({"mod_vol_diff": 9}, "mod_vol_diff_minus", -2),  # *
    ({"noise": 80}, "noise_minus", 0), ({"noise": 84}, "noise_minus", -1),  # *
    ({"thermal_img_chk": "이상"}, "thermal_img_chk_minus", -0.5),  # *
    ({"ex_box_chk": "이상"}, "ex_box_chk_minus", -0.3),  # *  -0.25 → -0.3(엑셀 ROUND식)
    ({"load": 55.0}, "capa_times_load_minus", -24.8),  # -24.75 → -24.8
    ({"load": 40.0}, "capa_times_load_minus", -18.0),
    ({"ins_build_rank": "A"}, "ins_build_rank_minus", -6), ({"ins_build_rank": "B"}, "ins_build_rank_minus", -3),
    ({"fire_spread_rank": "A"}, "fire_spread_rank_minus", -3), ({"fire_spread_rank": "B"}, "fire_spread_rank_minus", 0),
    ({"emerge_resp": "A"}, "emerge_resp_minus", -2), ({"emerge_resp": "B"}, "emerge_resp_minus", -1),
    ({"rep_time": "A"}, "rep_time_minus", -2), ({"rep_cost": "B"}, "rep_cost_minus", -1),
    ({"sys_rel": "N"}, "sys_rel_minus", -4), ({"sys_rel": "N+1"}, "sys_rel_minus", -2),
    ({"emerge_sys": "불가"}, "emerge_sys_minus", -4), ({"emerge_sys": "EMG"}, "emerge_sys_minus", -2),  # 불가는 *
    ({"fac_rel": "N"}, "fac_rel_minus", -9),  # *
    ({"part_shortage": "단종"}, "part_shortage_minus", -9),
    ({"model_type": "콘덴서"}, "model_type_minus", -2),  # mock은 전부 콘덴서
    ({"switching_type": "2레벨PWM"}, "switching_type_minus", -1),
    ({"igbt_rev": "600V"}, "igbt_rev_minus", -1),  # *
    ({"online_diag": "미적용"}, "online_diag_minus", -9),
]


@pytest.mark.parametrize(("overrides", "column", "expected"), BRANCHES)
def test_deduction_branches(overrides, column, expected):
    assert ef6_vdp.calculate(_base_row(**overrides))[column] == expected


def test_base_row_totals():
    base = ef6_vdp.calculate(_base_row())
    assert (base["pof"], base["cof"], base["dof"], base["total_score"]) == (100, 100, 100, 100)


def test_one_decimal_scores():
    out = ef6_vdp.calculate(_base_row(thermal_img_chk="이상", ex_box_chk="이상", load=55.0))
    assert out["pof_minus"] == -0.8 and out["pof"] == 99.2  # -0.5 + -0.3
    assert out["cof"] == 75.2  # 100 - 24.8
    assert out["total_score"] == round1(0.5 * 99.2 + 0.3 * 75.2 + 0.2 * 100)  # 92.16 → 92.2
    assert out["total_score"] == 92.2


def test_worst_case_scores_can_go_negative_and_are_kept():
    worst = _base_row(operation_start_time=_years_ago(25), elec_room_max_temp=30.0)
    assert ef6_vdp.calculate(worst)["pof"] < 0  # 원본대로 음수 저장(분포도에서만 0~100으로 자름)


def test_voltage_is_filled_with_zero():
    assert "voltage" not in {c["name"] for c in ef6_vdp.INPUT_COLUMNS}
    assert ef6_vdp.calculate(_base_row())["voltage"] == 0


def test_na_temperature_zeroes_every_part_failure_deduction():
    """전기실최대온도가 N/A면 온도 보정 와이블 5종과 온도 감점이 모두 평가되지 않는다(감점 0)."""
    aged = _base_row(operation_start_time=_years_ago(16), elec_room_max_temp=None)
    out = ef6_vdp.calculate(aged)
    assert all(out[name] == 0 for name in WEIBULL + ["elec_room_max_temp_minus"])
    assert out["cap_stat"] is None and out["age_minus"] == -16


def test_matches_reference_formulas(ref):
    random.seed(20261106)
    rows = [ef6_vdp.generate_input_row() for _ in range(300)]
    rows += [_base_row(**overrides) for overrides, _, _ in BRANCHES]
    rows += [_base_row(thermal_img_chk="이상", ex_box_chk="이상", load=float(l)) for l in range(40, 101, 3)]
    for row in rows:
        ours = ef6_vdp.calculate(row)
        theirs = _expected(ref, row)
        for name in CALC_NAMES:
            assert ours[name] == theirs[name], (name, row)


def test_columns_match_reference_names(ref):
    assert [c["name"] for c in ef6_vdp.INPUT_COLUMNS] == [c["name"] for c in ref.INPUT_COLUMNS]
    assert CALC_NAMES == [c["name"] for c in ref.CALCULATED_COLUMNS]


def test_breakdown_covers_every_summed_deduction():
    """메타데이터 항목 = 원본 합계식에 들어가는 감점 전부(그룹 없음 — 원본에 소계가 없다)."""
    bd = ef6_vdp.BREAKDOWN
    assert (len(bd["pof"]), len(bd["cof"]), len(bd["dof"])) == (13, 6, 8)
    assert not any("group" in item for axis in bd.values() for item in axis)
    row = ef6_vdp.calculate(_base_row(
        operation_start_time=date(2008, 5, 1), elec_room_max_temp=27.5, load=97.0, noise=90, thermal_img_chk="이상",
        ex_box_chk="이상", ins_build_rank="A", emerge_resp="B", sys_rel="N", fac_rel="N", igbt_rev="600V",
    ))
    for axis in ("pof", "cof", "dof"):
        assert round1(sum(row[i["field"]] for i in bd[axis])) == row[f"{axis}_minus"], axis


def test_mock_rows_pass_import_validation_and_calculate():
    random.seed(7)
    for _ in range(1000):
        row = ef6_vdp.generate_input_row()
        for col in ef6_vdp.INPUT_COLUMNS:
            assert _check_allowed(row[col["name"]], col) is None, (col["name"], row[col["name"]])
        calc = ef6_vdp.calculate(row)
        assert 0 <= calc["cof"] <= 100 and 0 <= calc["dof"] <= 100  # PoF는 노후·고온이면 원본대로 음수 가능


# ------------------------------------------------------------------ 임포트
def _fmt(v):
    return v.isoformat() if isinstance(v, date) else str(v)


def _write_ef6_dat(tmp_path, rows, name="ef6.dat"):
    names = [c["name"] for c in ef6_vdp.INPUT_COLUMNS]
    lines = ["\t".join(names)] + ["\t".join(_fmt(r[n]) for n in names) for r in rows]
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


async def test_import_valid_ef6_file_fills_all_vdp_tables(session_factory, tmp_path):
    rows = [ef6_vdp.generate_input_row() for _ in range(4)]
    async with session_factory() as session:
        result = await import_file(_write_ef6_dat(tmp_path, rows), "EF6", session)
        assert result.ok, (result.file_errors, result.row_errors)
        assert result.imported_rows == 4
        for model in (VdpSpec, VdpCondition, VdpConsequenceAttribute, VdpDesignAttribute, VdpScoreDetail):
            assert await session.scalar(select(func.count()).select_from(model)) == 4, model.__tablename__
        stored = (await session.execute(select(Equipment).where(Equipment.ef_code == "EF6"))).scalars().all()
        assert sorted(e.equipment_name for e in stored) == sorted(r["eqp_id"] for r in rows)  # 설비코드 = 설비명
        assert {e.voltage for e in stored} == {0}  # 파일에 전압 컬럼이 없다
        models = (await session.execute(select(VdpSpec.model_name))).scalars().all()
        assert sorted(models) == sorted(r["model_name"] for r in rows)


@pytest.mark.parametrize(
    ("column", "bad_value", "reason_part"),
    [
        ("model_type", "무변압기", "허용값 아님"),   # UPS 값은 VDP에서 받지 않는다
        ("thermal_img_chk", "양호", "허용값 아님"),   # 원본은 '이상' 외 전부 무감점 → 오타가 조용히 통과
        ("ins_build_rank", "a", "허용값 아님"),      # 소문자
        ("sys_rel", "N+2", "허용값 아님"),
        ("emerge_sys", "emg", "허용값 아님"),
        ("online_diag", "실시", "허용값 아님"),
        ("load", -0.1, "미만"),
        ("fan_replace_no", -1, "미만"),
        ("line_no", "", "빈 값"),
        ("eqp_id", "", "빈 값"),
    ],
)
async def test_import_rejects_out_of_range_values(session_factory, tmp_path, column, bad_value, reason_part):
    rows = [ef6_vdp.generate_input_row() for _ in range(3)]
    rows[1][column] = bad_value
    async with session_factory() as session:
        result = await import_file(_write_ef6_dat(tmp_path, rows), "EF6", session)
        assert not result.ok
        assert [(e.row_number, e.column) for e in result.row_errors] == [(3, column)]
        assert reason_part in result.row_errors[0].reason
        assert await count_type(session, "EF6") == 0


async def test_import_accepts_decimal_temperature_but_not_decimal_noise(session_factory, tmp_path):
    """전기실최대온도·부하율은 소수, 소음 등은 원본 샘플대로 정수(2026-11-06 결정)."""
    rows = [ef6_vdp.generate_input_row() for _ in range(2)]
    rows[0]["elec_room_max_temp"] = 26.3
    rows[1]["noise"] = 70.5
    async with session_factory() as session:
        result = await import_file(_write_ef6_dat(tmp_path, rows), "EF6", session)
        assert [(e.row_number, e.column) for e in result.row_errors] == [(3, "noise")]


async def test_import_na_temperature_is_stored_as_null(session_factory, tmp_path):
    rows = [ef6_vdp.generate_input_row() for _ in range(2)]
    rows[0]["elec_room_max_temp"] = "N/A"
    async with session_factory() as session:
        result = await import_file(_write_ef6_dat(tmp_path, rows), "EF6", session)
        assert result.ok, result.row_errors
        assert result.na_values == {"elec_room_max_temp": 1}
        temps = (await session.execute(select(VdpCondition.elec_room_max_temp))).scalars().all()
        assert None in temps


# ------------------------------------------------------------------ 다른 유형과 공존
async def _others_fingerprint(session):
    rows = (
        await session.execute(
            select(Equipment.equipment_id, Equipment.ef_code, Equipment.equipment_name, ScoreSnapshot.total_score)
            .join(ScoreSnapshot, ScoreSnapshot.equipment_id == Equipment.equipment_id)
            .where(Equipment.ef_code != "EF6")
            .order_by(Equipment.equipment_id)
        )
    ).all()
    return rows


async def test_ef6_replace_import_keeps_other_types_intact(client, session_factory, tmp_path):
    async with session_factory() as session:
        for _ in range(2):
            await ingest_row(ef5_ups.calculate(ef5_ups.generate_input_row()), session)
        for _ in range(5):
            await ingest_row(ef6_vdp.calculate(ef6_vdp.generate_input_row()), session)
        await session.commit()
        before = await _others_fingerprint(session)
        assert {r.ef_code for r in before} == {"EF1", "EF5"} and await count_type(session, "EF6") == 5

        real_rows = [ef6_vdp.generate_input_row() for _ in range(2)]
        result = await import_file(_write_ef6_dat(tmp_path, real_rows), "EF6", session, replace=True)

        assert result.ok and result.replaced_rows == 5 and result.imported_rows == 2
        assert await count_type(session, "EF6") == 2
        assert await session.scalar(select(func.count()).select_from(VdpScoreDetail)) == 2
        assert await _others_fingerprint(session) == before


async def test_ef6_detail_and_metadata_api(client, session_factory):
    async with session_factory() as session:
        row = ef6_vdp.generate_input_row()
        row["ex_box_chk"] = "이상"
        eq_id = await ingest_row(ef6_vdp.calculate(row), session)
        await session.commit()

    body = (await client.get(f"/api/equipment/{eq_id}")).json()
    assert body["ef_code"] == "EF6" and body["ef_name"] == "VDP"
    td = body["type_detail"]
    assert td["ef_code"] == "EF6"
    assert {"spec", "condition", "consequence", "design", "score_detail"} <= td.keys()
    assert {"line_no", "manufacturer", "model_name", "capa"} <= td["spec"].keys()
    assert td["score_detail"]["ex_box_chk_minus"] == -0.3
    assert body["score"]["pof"] == round1(body["score"]["pof"])  # 소수 첫째 자리
    assert len(body["projection"]) > 1  # 저장값으로 복원한 입력으로 5년 예측이 계산된다

    items = (await client.get("/api/equipment", params={"ef_code": "EF6"})).json()
    assert [i["ef_code"] for i in items] == ["EF6"]
    assert items[0]["last_diag_date"] == date.today().isoformat()  # 점검결과 반영 기준일
    types = {t["ef_code"]: t for t in (await client.get("/api/equipment-types")).json()}
    assert types["EF6"]["equipment_count"] == 1 and types["EF6"]["ef_name"] == "VDP"
    assert types["EF6"]["breakdown"]["pof"][0] == {"field": "age_minus", "label": "경과년수", "group": None, "summed": True}


# ------------------------------------------------------------------ 마이그레이션
def test_vdp_migration_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "vdp_migrate.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    def tables():
        with sqlite3.connect(db_path) as conn:
            return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    try:
        cfg = Config()
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        vdp_tables = {m.__tablename__ for m in ef6_vdp.DOMAIN_TABLES}

        command.upgrade(cfg, "head")
        assert vdp_tables <= tables()

        command.downgrade(cfg, "7edeafa442e4")
        assert not vdp_tables & tables()
        assert {"ups_spec", "switchgear_spec", "cable_spec", "gis_operation", "transformer_spec", "equipment"} <= tables()

        command.upgrade(cfg, "head")
        assert vdp_tables <= tables()
    finally:
        get_settings.cache_clear()
