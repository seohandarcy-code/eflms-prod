"""Stage 8-3 — EF2(GIS) 계산기·적재·임포트 검증.

- 원본(ref_data/schema_eflms_gis.py)과 같은 입력 → 모든 계산 컬럼이 같은지
- 감점 분기별 정답값(mock 범위에선 안 나오는 분기 포함)
- mock 생성값이 임포트 허용값을 통과하는지, 허용값 밖은 거부되는지
- EF1과 공존(EF2만 교체해도 EF1 불변), 8-4 전 조회 API 안전장치
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
    GisConsequenceAttribute,
    GisDesignAttribute,
    GisDiagnosis,
    GisOperation,
    GisScoreDetail,
    GisSf6Reading,
    ScoreSnapshot,
    TransformerSpec,
)
from app.equipment_types import ef2_gis
from app.services.dataset_service import count_type
from app.services.import_service import _check_allowed, import_file
from app.services.ingest import ingest_row

REF_PATH = BACKEND_DIR.parent / "ref_data" / "schema_eflms_gis.py"
CALC_NAMES = [c["name"] for c in ef2_gis.CALCULATED_COLUMNS]


@pytest.fixture(scope="module")
def ref():
    """원본 계산 툴을 import만 한다 — ref_data/는 읽기 전용이라 __pycache__도 만들지 않는다."""
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("ref_schema_eflms_gis", REF_PATH)
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


def _base_row(**overrides):
    """감점이 하나도 없는 기준 입력(수분 ≤150, 전부 최상 등급) + 덮어쓸 값."""
    row = {
        "factory_code": "H1", "EF_code": "EF2", "gis_name": "cb1", "voltage": 154000, "op_type": "공압식",
        "cb_op_num": 0, "operation_start_time": date.today() - timedelta(days=365),
        "rated_trip_count": 0, "cum_trip_current": 0, "cb_op_char_over": "N", "load_percent": 0.0,
        "leakage_curr": 0.0, "part_dischar_pat": "N", "sf6_diag_time": date(2024, 11, 1), "sf6_so2": 0.0,
        "sf6_leak": "없음", "sf6_h2o": 100.0, "sf6_purity": 99.9, "elec_room_max_temp": 25,
        "in_vol": "C", "capa_times_load": "E", "fire_spread": "B", "env_loc": "C", "emerge_resp_pat": "E",
        "rep_cost": "E", "rep_time": "E", "in_line_num": "C", "ato": "Y", "reliability": "B",
        "online_diag": "D", "offline_diag": "Y", "tbm": "Y", "conn_rev": "Y", "leak_str": "Y",
        "insul_str": "Y", "vt_la_str": "Y",
    }
    row.update(overrides)
    return row


# (덮어쓸 입력, 확인할 계산 컬럼, 기대값) — mock 범위에서 한 번도 안 나오는 분기(*)도 전부 포함
BRANCHES = [
    ({"cb_op_num": 299}, "cb_op_num_minus", 0), ({"cb_op_num": 300}, "cb_op_num_minus", -2),  # *
    ({"cb_op_num": 500}, "cb_op_num_minus", -4), ({"cb_op_num": 1000}, "cb_op_num_minus", -6),  # *
    ({"cb_op_num": 2000}, "cb_op_num_minus", -8),  # *
    ({"rated_trip_count": 4}, "rated_trip_count_minus", 0), ({"rated_trip_count": 5}, "rated_trip_count_minus", -6),
    ({"rated_trip_count": 10}, "rated_trip_count_minus", -12),
    ({"cum_trip_current": 24}, "cum_trip_current_minus", 0), ({"cum_trip_current": 25}, "cum_trip_current_minus", -8),
    ({"cum_trip_current": 101}, "cum_trip_current_minus", -8), ({"cum_trip_current": 102}, "cum_trip_current_minus", -12),
    ({"cum_trip_current": 501}, "cum_trip_current_minus", -16),
    ({"cb_op_char_over": "Y"}, "cb_op_char_over_minus", -9),
    ({"load_percent": 70.0}, "load_minus", 0), ({"load_percent": 70.1}, "load_minus", -10),
    ({"load_percent": 80.1}, "load_minus", -20), ({"load_percent": 90.1}, "load_minus", -30),
    ({"leakage_curr": 0.53}, "leakage_curr_minus", 0), ({"leakage_curr": 0.54}, "leakage_curr_minus", -6),  # *
    ({"voltage": 345000, "leakage_curr": 1.19}, "leakage_curr_minus", 0),
    ({"voltage": 345000, "leakage_curr": 1.2}, "leakage_curr_minus", -6),  # *
    ({"part_dischar_pat": "Y"}, "part_dischar_minus", -15),
    # SF6 (*) — 수분 ≤150이면 순도 무시(원본대로), so2·누기는 별도 합산
    ({"sf6_h2o": 150.0, "sf6_purity": 90.0}, "sf6_minus", 0),
    ({"sf6_h2o": 151.0, "sf6_purity": 99.0}, "sf6_minus", -10),
    ({"sf6_h2o": 151.0, "sf6_purity": 95.0}, "sf6_minus", -15),
    ({"sf6_h2o": 301.0, "sf6_purity": 99.0}, "sf6_minus", -15),
    ({"sf6_so2": 1.0}, "sf6_minus", -20), ({"sf6_leak": "있음"}, "sf6_minus", -12),
    ({"sf6_so2": 1.0, "sf6_leak": "있음", "sf6_h2o": 400.0}, "sf6_minus", -47),
    ({"elec_room_max_temp": 29}, "elec_room_minus", 0), ({"elec_room_max_temp": 30}, "elec_room_minus", -4),  # *
    ({"in_vol": "A"}, "in_vol_minus", -16), ({"in_vol": "B"}, "in_vol_minus", -8),
    ({"capa_times_load": "A"}, "productivity_minus", -16), ({"capa_times_load": "D"}, "productivity_minus", -4),
    ({"fire_spread": "A"}, "fire_spread_minus", -6),
    ({"env_loc": "A"}, "env_minus", -6), ({"env_loc": "B"}, "env_minus", -3),
    ({"emerge_resp_pat": "A"}, "emerge_resp_minus", -6), ({"emerge_resp_pat": "D"}, "emerge_resp_minus", -1),
    ({"rep_cost": "A"}, "rep_cost_minus", -8), ({"rep_cost": "D"}, "rep_cost_minus", -2),
    ({"rep_time": "A"}, "rep_time_minus", -4), ({"rep_time": "D"}, "rep_time_minus", -1),
    ({"in_line_num": "A"}, "in_line_minus", -30), ({"in_line_num": "B"}, "in_line_minus", -15),  # *
    ({"ato": "N"}, "ato_minus", -30),  # *
    ({"reliability": "A"}, "reliability_minus", -16),
    ({"online_diag": "A"}, "online_diag_minus", -15), ({"online_diag": "C"}, "online_diag_minus", -5),
    ({"offline_diag": "N"}, "offline_diag_minus", -15), ({"tbm": "N"}, "tbm_minus", -12),  # *(tbm)
    ({"conn_rev": "N"}, "conn_rev_minus", -4), ({"leak_str": "N"}, "leak_str_minus", -4),
    ({"insul_str": "N"}, "insul_str_minus", -4), ({"vt_la_str": "N"}, "vt_la_minus", -3),
]


@pytest.mark.parametrize(("overrides", "column", "expected"), BRANCHES)
def test_deduction_branches(overrides, column, expected):
    assert ef2_gis.calculate(_base_row(**overrides))[column] == expected


def test_weibull_aging_and_totals_at_30_years():
    row = ef2_gis.calculate(_base_row(operation_start_time=date.today() - timedelta(days=30 * 365)))
    assert row["operation_year"] == 30.0
    assert row["age_minus"] == -30
    assert row["cb_stat_minus"] == -6       # e^-((30/72)^3.21) = 0.9416
    assert row["insul_stat_minus"] == -5    # e^-((30/4199)^0.75) = 0.9757, ×2
    assert row["gis_mech_minus"] == -11
    # age_minus는 PoF에 합산하지 않는다(원본대로) — 노화는 와이블 감점이 담당
    assert row["pof"] == 100 - 11
    assert row["cof"] == 100 and row["dof"] == 100
    assert row["total_score"] == pytest.approx(0.5 * 89 + 0.3 * 100 + 0.2 * 100)


def test_worst_case_scores_can_go_negative_and_are_kept():
    worst = _base_row(
        in_line_num="A", ato="N", reliability="A", online_diag="A", offline_diag="N", tbm="N",
        conn_rev="N", leak_str="N", insul_str="N", vt_la_str="N",
    )
    assert ef2_gis.calculate(worst)["dof"] == 100 - 133  # 원본대로 음수 그대로 저장(차트만 클램프)


def test_matches_reference_formulas(ref):
    random.seed(20261016)
    rows = [ef2_gis.generate_input_row() for _ in range(300)]
    rows += [_base_row(**overrides) for overrides, _, _ in BRANCHES]
    rows.append(_base_row(operation_start_time=date.today() - timedelta(days=45 * 365)))
    for row in rows:
        ours = ef2_gis.calculate(row)
        theirs = _ref_calculate(ref, row)
        for name in CALC_NAMES:
            assert ours[name] == theirs[name], (name, row)


def test_input_columns_match_reference_names(ref):
    assert [c["name"] for c in ef2_gis.INPUT_COLUMNS] == [c["name"] for c in ref.INPUT_COLUMNS]
    assert CALC_NAMES == [c["name"] for c in ref.CALCULATED_COLUMNS]


def test_mock_rows_pass_import_validation_and_calculate():
    random.seed(7)
    for _ in range(1000):
        row = ef2_gis.generate_input_row()
        for col in ef2_gis.INPUT_COLUMNS:
            assert _check_allowed(row[col["name"]], col) is None, (col["name"], row[col["name"]])
        calc = ef2_gis.calculate(row)
        assert 0 <= calc["pof"] <= 100 and 0 <= calc["cof"] <= 100 and 0 <= calc["dof"] <= 100


# ------------------------------------------------------------------ 임포트
def _fmt(v):
    return v.isoformat() if isinstance(v, date) else str(v)


def _write_ef2_dat(tmp_path, rows, name="ef2.dat"):
    names = [c["name"] for c in ef2_gis.INPUT_COLUMNS]
    lines = ["\t".join(names)] + ["\t".join(_fmt(r[n]) for n in names) for r in rows]
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


async def test_import_valid_ef2_file_fills_all_gis_tables(session_factory, tmp_path):
    rows = [ef2_gis.generate_input_row() for _ in range(4)]
    async with session_factory() as session:
        result = await import_file(_write_ef2_dat(tmp_path, rows), "EF2", session)
        assert result.ok, (result.file_errors, result.row_errors)
        assert result.imported_rows == 4
        for model in (GisOperation, GisDiagnosis, GisSf6Reading, GisConsequenceAttribute, GisDesignAttribute, GisScoreDetail):
            assert await session.scalar(select(func.count()).select_from(model)) == 4, model.__tablename__
        names = (await session.execute(select(Equipment.equipment_name).where(Equipment.ef_code == "EF2"))).scalars().all()
        assert sorted(names) == sorted(r["gis_name"] for r in rows)


@pytest.mark.parametrize(
    ("column", "bad_value", "reason_part"),
    [
        ("in_vol", "c", "허용값 아님"),          # 소문자 오기
        ("voltage", 220000, "허용값 아님"),      # 154k/345k만
        ("sf6_purity", 100.5, "초과"),
        ("load_percent", -1.0, "미만"),
        ("sf6_leak", "모름", "허용값 아님"),
        ("gis_name", "", "빈 값"),
    ],
)
async def test_import_rejects_out_of_range_values(session_factory, tmp_path, column, bad_value, reason_part):
    rows = [ef2_gis.generate_input_row() for _ in range(3)]
    rows[1][column] = bad_value
    async with session_factory() as session:
        result = await import_file(_write_ef2_dat(tmp_path, rows), "EF2", session)
        assert not result.ok
        assert [(e.row_number, e.column) for e in result.row_errors] == [(3, column)]
        assert reason_part in result.row_errors[0].reason
        assert await count_type(session, "EF2") == 0


# ------------------------------------------------------------------ EF1과 공존
async def _ef1_fingerprint(session):
    rows = (
        await session.execute(
            select(Equipment.equipment_id, Equipment.equipment_name, ScoreSnapshot.total_score)
            .join(ScoreSnapshot, ScoreSnapshot.equipment_id == Equipment.equipment_id)
            .where(Equipment.ef_code == "EF1")
            .order_by(Equipment.equipment_id)
        )
    ).all()
    return rows, await session.scalar(select(func.count()).select_from(TransformerSpec))


async def test_ef2_replace_import_keeps_ef1_intact(client, session_factory, tmp_path):
    async with session_factory() as session:
        for _ in range(5):  # EF2 mock
            await ingest_row(ef2_gis.calculate(ef2_gis.generate_input_row()), session)
        await session.commit()
        before = await _ef1_fingerprint(session)
        assert len(before[0]) == 3 and await count_type(session, "EF2") == 5

        real_rows = [ef2_gis.generate_input_row() for _ in range(2)]
        result = await import_file(_write_ef2_dat(tmp_path, real_rows), "EF2", session, replace=True)

        assert result.ok and result.replaced_rows == 5 and result.imported_rows == 2
        assert await count_type(session, "EF2") == 2
        assert await session.scalar(select(func.count()).select_from(GisScoreDetail)) == 2
        assert await _ef1_fingerprint(session) == before


async def test_read_apis_stay_ef1_only_until_stage_8_4(client, session_factory):
    async with session_factory() as session:
        eq_id = await ingest_row(ef2_gis.calculate(ef2_gis.generate_input_row()), session)
        await session.commit()

    items = (await client.get("/api/equipment")).json()
    assert {item["ef_code"] for item in items} == {"EF1"}
    assert (await client.get("/api/summary")).json()["total_equipment"] == 3
    assert (await client.get(f"/api/equipment/{eq_id}")).status_code == 404


# ------------------------------------------------------------------ 마이그레이션
def test_gis_migration_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "gis_migrate.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    try:
        cfg = Config()
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        gis_tables = {m.__tablename__ for m in ef2_gis.DOMAIN_TABLES}

        command.upgrade(cfg, "b3f7d2a8c615")
        with sqlite3.connect(db_path) as conn:
            assert gis_tables <= {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        command.downgrade(cfg, "8a1c4e2f9b70")
        with sqlite3.connect(db_path) as conn:
            assert not gis_tables & {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        get_settings.cache_clear()
