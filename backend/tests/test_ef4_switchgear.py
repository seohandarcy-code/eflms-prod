"""Stage 10 — EF4(수배전반) 계산기·적재·임포트 검증.

- 원본(ref_data/schema_eflms_subaejeon.py)과 같은 입력 → 모든 계산 컬럼이 같은지(원본 공식 그대로)
- 감점 분기별 정답값(mock 범위에선 안 나오는 분기 포함)
- mock 생성값이 임포트 허용값을 통과하는지, 허용값 밖은 거부되는지
- 전압 컬럼 없는 파일 → 공통 equipment.voltage = 0
- EF1~EF3과 공존(EF4만 교체해도 다른 유형 불변), 마이그레이션 왕복
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
    SwitchgearCondition,
    SwitchgearConsequenceAttribute,
    SwitchgearDesignAttribute,
    SwitchgearScoreDetail,
    SwitchgearSpec,
)
from app.equipment_types import ef3_cable, ef4_switchgear
from app.services.dataset_service import count_type
from app.services.import_service import _check_allowed, import_file
from app.services.ingest import ingest_row

REF_PATH = BACKEND_DIR.parent / "ref_data" / "schema_eflms_subaejeon.py"
CALC_NAMES = [c["name"] for c in ef4_switchgear.CALCULATED_COLUMNS]


@pytest.fixture(scope="module")
def ref():
    """원본 계산 툴을 import만 한다 — ref_data/는 읽기 전용이라 __pycache__도 만들지 않는다."""
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("ref_schema_eflms_subaejeon", REF_PATH)
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


def _years_ago(years):
    return date.today() - timedelta(days=int(years * 365))


def _base_row(**overrides):
    """감점이 0인 기준 입력(오늘 가동 → 관통형CT·장수명FAN·조명등 모두 적용, 전부 최상) + 덮어쓸 값."""
    row = {
        "factory_code": "H1", "EF_code": "EF4", "eqp_id": "eqp1", "eqp_id_name": "hvcb1",
        "eqp_building": "화성UT1동", "operation_start_time": date.today(),
        "part_thermal_chk": "양호", "elec_room_avg_temp": 25, "temp_diff_chk": 0, "max_temp_chk": 20,
        "load_chk": 0.0, "ex_box_chk": "양호", "noise_chk": "양호", "bolt_chk": "양호",
        "eqp_disting": "10U", "eqp_floor": "1F", "scale_dam_chk": 0.0, "install_building": "사무동",
        "sup_sys_chk": "일반", "prod_chk": "비생산", "op_chk": "비가동", "replace_chk": 0.0,
        "recovery_time_chk": 0.0, "replace_time_chk": 0, "reliability": "O", "ato": "적용",
        "cb_inspect": "실시", "relay_chk": "실시", "online_diag": "적용", "part_shortage": "공급가능",
    }
    row.update(overrides)
    return row


# (덮어쓸 입력, 확인할 계산 컬럼, 기대값) — mock 범위에서 한 번도 안 나오는 분기(*)도 전부 포함
BRANCHES = [
    ({"operation_start_time": _years_ago(12.5)}, "age_minus", -12),
    ({"operation_start_time": _years_ago(12.5)}, "cb_stat_minus", 0),
    ({"operation_start_time": _years_ago(20)}, "cb_stat_minus", -4),
    ({"operation_start_time": _years_ago(30)}, "cb_stat_minus", -63),  # *
    ({"part_thermal_chk": "불량"}, "part_thermal_chk_minus", -4),  # *
    ({"elec_room_avg_temp": 30}, "elec_room_avg_temp_minus", 0), ({"elec_room_avg_temp": 31}, "elec_room_avg_temp_minus", -2),  # *
    ({"elec_room_avg_temp": 35}, "elec_room_avg_temp_minus", -10),  # *
    ({"temp_diff_chk": 3}, "temp_diff_chk_minus", 0), ({"temp_diff_chk": 4}, "temp_diff_chk_minus", -4),  # *
    ({"temp_diff_chk": 6}, "temp_diff_chk_minus", -8),  # *
    ({"max_temp_chk": 30}, "max_temp_chk_minus", 0), ({"max_temp_chk": 31}, "max_temp_chk_minus", -4),  # *
    ({"max_temp_chk": 41}, "max_temp_chk_minus", -8),  # *
    ({"load_chk": 0.5}, "load_minus", 0), ({"load_chk": 0.51}, "load_minus", -4),
    ({"load_chk": 0.81}, "load_minus", -8),  # *
    ({"ex_box_chk": "불량"}, "ex_box_chk_minus", -1), ({"noise_chk": "불량"}, "noise_chk_minus", -1),  # *
    ({"bolt_chk": "불량"}, "bolt_chk_minus", -1),  # *
    ({"scale_dam_chk": 100.0}, "scale_dam_chk_minus", -1),
    ({"scale_dam_chk": 750.0}, "scale_dam_chk_minus", -4),  # Python round: -4.5 → -4(짝수 쪽, 원본대로)
    ({"scale_dam_chk": 1250.0}, "scale_dam_chk_minus", -8),  # *  -7.5 → -8
    ({"scale_dam_chk": 5000.0}, "scale_dam_chk_minus", -30), ({"scale_dam_chk": 5001.0}, "scale_dam_chk_minus", -30),  # *
    ({"install_building": "FAB동"}, "install_building_minus", -12), ({"install_building": "UT동"}, "install_building_minus", -8),
    ({"install_building": "GCS동"}, "install_building_minus", -8),  # *
    ({"install_building": "변전소"}, "install_building_minus", -8), ({"install_building": "그린동"}, "install_building_minus", -4),
    ({"install_building": "기타"}, "install_building_minus", 0),
    ({"sup_sys_chk": "비상"}, "sup_sys_chk_minus", -3), ({"prod_chk": "생산"}, "prod_chk_minus", -4),
    ({"op_chk": "가동"}, "op_chk_minus", -3),
    ({"replace_chk": 0.5}, "replace_chk_minus", 0), ({"replace_chk": 0.8}, "replace_chk_minus", -2),
    ({"replace_chk": 1.2}, "replace_chk_minus", -6),
    ({"recovery_time_chk": 0.5}, "recovery_time_chk_minus", -3), ({"recovery_time_chk": 1.1}, "recovery_time_chk_minus", -6),  # *
    ({"recovery_time_chk": 5.1}, "recovery_time_chk_minus", -9),  # *
    ({"replace_time_chk": 1}, "replace_time_chk_minus", 0), ({"replace_time_chk": 2}, "replace_time_chk_minus", -2),  # *
    ({"replace_time_chk": 11}, "replace_time_chk_minus", -4), ({"replace_time_chk": 31}, "replace_time_chk_minus", -6),  # *
    ({"reliability": "X"}, "reliability_minus", -4), ({"ato": "미적용"}, "ato_minus", -4),
    ({"cb_inspect": "미실시"}, "cb_inspect_minus", -2), ({"relay_chk": "미실시"}, "relay_chk_minus", -1),
    ({"online_diag": "미적용"}, "online_diag_minus", -2), ({"part_shortage": "단종"}, "part_shortage_minus", -1),  # *
    ({"operation_start_time": date(2009, 12, 31)}, "ct_use_minus", -1),
    ({"operation_start_time": date(2010, 1, 1)}, "ct_use_minus", 0),
    ({"operation_start_time": date(2014, 12, 31)}, "spec_use_minus", -1),  # 장수명FAN 미적용
    ({"operation_start_time": date(2017, 12, 31)}, "spec_use_minus", -1),  # *  조명등 미적용
    ({"operation_start_time": date(2018, 1, 1)}, "spec_use_minus", 0),  # *
]


@pytest.mark.parametrize(("overrides", "column", "expected"), BRANCHES)
def test_deduction_branches(overrides, column, expected):
    assert ef4_switchgear.calculate(_base_row(**overrides))[column] == expected


def test_base_row_totals_and_subtotals():
    base = ef4_switchgear.calculate(_base_row())
    assert (base["pof"], base["cof"], base["dof"], base["total_score"]) == (100, 100, 100, 100)
    aged = ef4_switchgear.calculate(_base_row(operation_start_time=_years_ago(20), load_chk=0.6))
    # 내구성 = 경과년수 + 차단기고장확률, 열적 = 부하율 등 — 원본 소계 그대로 PoF에 합산
    assert aged["durability_minus"] == -20 - 4 and aged["thermal_minus"] == -4
    assert aged["pof"] == 100 - 24 - 4


def test_worst_case_scores_can_go_negative_and_are_kept():
    worst = _base_row(operation_start_time=_years_ago(35), elec_room_avg_temp=40)
    assert ef4_switchgear.calculate(worst)["pof"] < 0  # 원본대로 음수 저장(분포도에서만 0~100으로 자름)


def test_voltage_is_filled_with_zero():
    """원본에 전압 입력이 없다 — 공통 equipment.voltage(필수)에 0을 넣는다(Stage 10-0)."""
    assert "voltage" not in {c["name"] for c in ef4_switchgear.INPUT_COLUMNS}
    assert ef4_switchgear.calculate(_base_row())["voltage"] == 0


def test_matches_reference_formulas(ref):
    random.seed(20261029)
    rows = [ef4_switchgear.generate_input_row() for _ in range(300)]
    rows += [_base_row(**overrides) for overrides, _, _ in BRANCHES]
    for row in rows:
        ours = ef4_switchgear.calculate(row)
        theirs = _ref_calculate(ref, row)
        for name in CALC_NAMES:
            assert ours[name] == theirs[name], (name, row)


def test_columns_match_reference_names(ref):
    assert [c["name"] for c in ef4_switchgear.INPUT_COLUMNS] == [c["name"] for c in ref.INPUT_COLUMNS]
    assert CALC_NAMES == [c["name"] for c in ref.CALCULATED_COLUMNS]


def test_breakdown_covers_every_summed_deduction_and_groups_match_subtotals():
    """메타데이터 항목 = 원본 합계식에 들어가는 감점 전부, 그룹 합 = 원본 소계."""
    bd = ef4_switchgear.BREAKDOWN
    assert (len(bd["pof"]), len(bd["cof"]), len(bd["dof"])) == (10, 8, 8)
    row = ef4_switchgear.calculate(_base_row(
        operation_start_time=date(2008, 5, 1), load_chk=0.9, bolt_chk="불량", scale_dam_chk=2000.0,
        install_building="FAB동", prod_chk="생산", recovery_time_chk=0.5, reliability="X", cb_inspect="미실시",
        part_shortage="단종",
    ))
    for axis in ("pof", "cof", "dof"):
        assert sum(row[i["field"]] for i in bd[axis]) == row[f"{axis}_minus"], axis
    subtotal = {
        ("pof", "내구성"): "durability_minus", ("pof", "열적"): "thermal_minus", ("pof", "물리적"): "phy_minus",
        ("cof", "계통"): "cof_sys_minus", ("cof", "비용"): "cof_cost_minus", ("cof", "기간"): "cof_recov_minus",
        ("dof", "계통"): "dof_sys_minus", ("dof", "비용"): "dof_cost_minus", ("dof", "복구시간"): "dof_recov_minus",
    }
    for (axis, group), field in subtotal.items():
        assert sum(row[i["field"]] for i in bd[axis] if i["group"] == group) == row[field], (axis, group)


def test_mock_rows_pass_import_validation_and_calculate():
    random.seed(7)
    for _ in range(1000):
        row = ef4_switchgear.generate_input_row()
        for col in ef4_switchgear.INPUT_COLUMNS:
            assert _check_allowed(row[col["name"]], col) is None, (col["name"], row[col["name"]])
        calc = ef4_switchgear.calculate(row)
        assert 0 <= calc["pof"] <= 100 and 0 <= calc["cof"] <= 100 and 0 <= calc["dof"] <= 100


# ------------------------------------------------------------------ 임포트
def _fmt(v):
    return v.isoformat() if isinstance(v, date) else str(v)


def _write_ef4_dat(tmp_path, rows, name="ef4.dat"):
    names = [c["name"] for c in ef4_switchgear.INPUT_COLUMNS]
    lines = ["\t".join(names)] + ["\t".join(_fmt(r[n]) for n in names) for r in rows]
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


async def test_import_valid_ef4_file_fills_all_switchgear_tables(session_factory, tmp_path):
    rows = [ef4_switchgear.generate_input_row() for _ in range(4)]
    async with session_factory() as session:
        result = await import_file(_write_ef4_dat(tmp_path, rows), "EF4", session)
        assert result.ok, (result.file_errors, result.row_errors)
        assert result.imported_rows == 4
        for model in (SwitchgearSpec, SwitchgearCondition, SwitchgearConsequenceAttribute,
                      SwitchgearDesignAttribute, SwitchgearScoreDetail):
            assert await session.scalar(select(func.count()).select_from(model)) == 4, model.__tablename__
        stored = (await session.execute(select(Equipment).where(Equipment.ef_code == "EF4"))).scalars().all()
        assert sorted(e.equipment_name for e in stored) == sorted(r["eqp_id"] for r in rows)  # 설비코드 = 설비명
        assert {e.voltage for e in stored} == {0}  # 파일에 전압 컬럼이 없다
        names = (await session.execute(select(SwitchgearSpec.eqp_id_name))).scalars().all()
        assert sorted(names) == sorted(r["eqp_id_name"] for r in rows)


@pytest.mark.parametrize(
    ("column", "bad_value", "reason_part"),
    [
        ("part_thermal_chk", "이상", "허용값 아님"),   # 원본은 '양호' 외 전부 감점 → 오타도 감점됨
        ("install_building", "UT 동", "허용값 아님"),  # 원본은 모르는 건물을 조용히 0점
        ("reliability", "o", "허용값 아님"),           # 소문자
        ("cb_inspect", "실시함", "허용값 아님"),
        ("load_chk", -0.1, "미만"),
        ("eqp_building", "", "빈 값"),
        ("eqp_id", "", "빈 값"),
    ],
)
async def test_import_rejects_out_of_range_values(session_factory, tmp_path, column, bad_value, reason_part):
    rows = [ef4_switchgear.generate_input_row() for _ in range(3)]
    rows[1][column] = bad_value
    async with session_factory() as session:
        result = await import_file(_write_ef4_dat(tmp_path, rows), "EF4", session)
        assert not result.ok
        assert [(e.row_number, e.column) for e in result.row_errors] == [(3, column)]
        assert reason_part in result.row_errors[0].reason
        assert await count_type(session, "EF4") == 0


async def test_import_rejects_decimal_temperature_as_int_column(session_factory, tmp_path):
    """온도는 원본 양식대로 int(2026-10-29 결정) — 소수는 줄 번호와 함께 거부된다."""
    rows = [ef4_switchgear.generate_input_row() for _ in range(2)]
    rows[0]["max_temp_chk"] = 25.5
    async with session_factory() as session:
        result = await import_file(_write_ef4_dat(tmp_path, rows), "EF4", session)
        assert not result.ok
        assert [(e.row_number, e.column) for e in result.row_errors] == [(2, "max_temp_chk")]


# ------------------------------------------------------------------ 다른 유형과 공존
async def _others_fingerprint(session):
    rows = (
        await session.execute(
            select(Equipment.equipment_id, Equipment.ef_code, Equipment.equipment_name, ScoreSnapshot.total_score)
            .join(ScoreSnapshot, ScoreSnapshot.equipment_id == Equipment.equipment_id)
            .where(Equipment.ef_code != "EF4")
            .order_by(Equipment.equipment_id)
        )
    ).all()
    return rows


async def test_ef4_replace_import_keeps_other_types_intact(client, session_factory, tmp_path):
    async with session_factory() as session:
        for _ in range(2):
            await ingest_row(ef3_cable.calculate(ef3_cable.generate_input_row()), session)
        for _ in range(5):
            await ingest_row(ef4_switchgear.calculate(ef4_switchgear.generate_input_row()), session)
        await session.commit()
        before = await _others_fingerprint(session)
        assert {r.ef_code for r in before} == {"EF1", "EF3"} and await count_type(session, "EF4") == 5

        real_rows = [ef4_switchgear.generate_input_row() for _ in range(2)]
        result = await import_file(_write_ef4_dat(tmp_path, real_rows), "EF4", session, replace=True)

        assert result.ok and result.replaced_rows == 5 and result.imported_rows == 2
        assert await count_type(session, "EF4") == 2
        assert await session.scalar(select(func.count()).select_from(SwitchgearScoreDetail)) == 2
        assert await _others_fingerprint(session) == before


async def test_ef4_detail_and_metadata_api(client, session_factory):
    async with session_factory() as session:
        eq_id = await ingest_row(ef4_switchgear.calculate(ef4_switchgear.generate_input_row()), session)
        await session.commit()

    body = (await client.get(f"/api/equipment/{eq_id}")).json()
    assert body["ef_code"] == "EF4" and body["ef_name"] == "수배전반"
    td = body["type_detail"]
    assert td["ef_code"] == "EF4"
    assert {"spec", "condition", "consequence", "design", "score_detail"} <= td.keys()
    assert {"eqp_id_name", "eqp_building", "eqp_floor", "eqp_disting"} <= td["spec"].keys()
    assert len(body["projection"]) > 1  # 저장값으로 복원한 입력으로 5년 예측이 계산된다

    items = (await client.get("/api/equipment", params={"ef_code": "EF4"})).json()
    assert [i["ef_code"] for i in items] == ["EF4"]
    assert items[0]["last_diag_date"] == date.today().isoformat()  # 점검결과 반영 기준일
    types = {t["ef_code"]: t for t in (await client.get("/api/equipment-types")).json()}
    assert types["EF4"]["equipment_count"] == 1
    assert types["EF4"]["breakdown"]["pof"][0] == {"field": "age_minus", "label": "경과년수", "group": "내구성", "summed": True}


# ------------------------------------------------------------------ 마이그레이션
def test_switchgear_migration_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "switchgear_migrate.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    def tables():
        with sqlite3.connect(db_path) as conn:
            return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    try:
        cfg = Config()
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        switchgear_tables = {m.__tablename__ for m in ef4_switchgear.DOMAIN_TABLES}

        command.upgrade(cfg, "head")
        assert switchgear_tables <= tables()

        command.downgrade(cfg, "90a898f21182")
        assert not switchgear_tables & tables()
        assert {"cable_spec", "gis_operation", "transformer_spec", "equipment"} <= tables()

        command.upgrade(cfg, "head")
        assert switchgear_tables <= tables()
    finally:
        get_settings.cache_clear()
