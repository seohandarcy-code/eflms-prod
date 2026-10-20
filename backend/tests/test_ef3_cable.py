"""Stage 9 — EF3(초고압케이블) 계산기·적재·임포트 검증.

- 원본(ref_data/schema_eflms_cable.py)과 같은 입력 → 모든 계산 컬럼이 같은지(원본 공식 그대로)
- 감점 분기별 정답값(mock 범위에선 안 나오는 분기 포함)
- mock 생성값이 임포트 허용값을 통과하는지, 허용값 밖은 거부되는지
- EF1·EF2와 공존(EF3만 교체해도 다른 유형 불변), 마이그레이션 왕복
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
    CableCondition,
    CableConsequenceAttribute,
    CableDesignAttribute,
    CableScoreDetail,
    CableSpec,
    Equipment,
    ScoreSnapshot,
)
from app.equipment_types import ef2_gis, ef3_cable
from app.services.dataset_service import count_type
from app.services.import_service import _check_allowed, import_file
from app.services.ingest import ingest_row

REF_PATH = BACKEND_DIR.parent / "ref_data" / "schema_eflms_cable.py"
CALC_NAMES = [c["name"] for c in ef3_cable.CALCULATED_COLUMNS]


@pytest.fixture(scope="module")
def ref():
    """원본 계산 툴을 import만 한다 — ref_data/는 읽기 전용이라 __pycache__도 만들지 않는다."""
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("ref_schema_eflms_cable", REF_PATH)
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
    """감점이 최소인 기준 입력(오늘 가동, 전부 최상) + 덮어쓸 값.
    원본상 감점 0이 될 수 없는 항목: 사고영향성(용량×-0.01), 사고복구비용(최소 -2)."""
    row = {
        "factory_code": "H1", "EF_code": "EF3", "tl_name": "tl1", "voltage": 154000,
        "cable_sq": 1600, "cable_per_phase": 2, "cable_mva": 100,
        "operation_start_time": date.today(), "max_load": 0, "max_temp": 20.0, "diff_temp": 0.0,
        "failure_rate": 0.0, "pd_num": 0, "sys_cycle_curr": 0.0, "svl_leak_curr": 0.0,
        "joint_ex_damage": "양호", "cable_move": 0.0, "cable_length": 100, "laying_type": "전력구",
        "mid_joint": 0, "end_joint": "DEBG", "emerge_resp": "1초내", "rep_time": "3개월이하",
        "reliability": 4, "temp_diag": "O", "pd_diag": "O", "live_line_diag": "O", "cable_move_diag": "O",
        "offline_diag": "1년이내", "longlife_insul": "O",
    }
    row.update(overrides)
    return row


# (덮어쓸 입력, 확인할 계산 컬럼, 기대값) — mock 범위에서 한 번도 안 나오는 분기(*)도 전부 포함
BRANCHES = [
    ({"max_load": 80}, "load_minus", 0), ({"max_load": 81}, "load_minus", -5),  # * (용량 100 → 부하율 = 부하)
    ({"max_load": 91}, "load_minus", -10), ({"max_load": 101}, "load_minus", -20),  # *
    ({"max_temp": 70.0}, "temp_minus", 0), ({"max_temp": 70.1}, "temp_minus", -5),  # *
    ({"max_temp": 80.1}, "temp_minus", -10), ({"max_temp": 90.1}, "temp_minus", -20),  # *
    ({"diff_temp": 5.0}, "diff_temp_minus", 0), ({"diff_temp": 5.1}, "diff_temp_minus", -5),  # *
    ({"diff_temp": 10.1}, "diff_temp_minus", -10),  # *
    ({"failure_rate": 0.0006}, "failure_rate_minus", -1), ({"failure_rate": 0.007}, "failure_rate_minus", -7),
    ({"pd_num": 1}, "pd_minus", -10), ({"pd_num": 3}, "pd_minus", -20),
    ({"sys_cycle_curr": 50.0}, "sys_cycle_curr_minus", 0), ({"sys_cycle_curr": 50.1}, "sys_cycle_curr_minus", -5),  # *
    ({"sys_cycle_curr": 100.1}, "sys_cycle_curr_minus", -10),  # *
    ({"svl_leak_curr": 0.5}, "svl_leak_curr_minus", 0), ({"svl_leak_curr": 0.51}, "svl_leak_curr_minus", -5),  # *
    ({"svl_leak_curr": 1.01}, "svl_leak_curr_minus", -10),  # *
    ({"joint_ex_damage": "이상"}, "joint_ex_damage_minus", -5),
    ({"cable_move": 1.0}, "cable_move_minus", 0), ({"cable_move": 1.1}, "cable_move_minus", -5),
    ({"cable_move": 3.1}, "cable_move_minus", -10), ({"cable_move": 5.1}, "cable_move_minus", -15),
    ({"cable_move": 10.1}, "cable_move_minus", -20),  # *
    ({"cable_mva": 414}, "risk_mva_minus", -4), ({"cable_mva": 984}, "risk_mva_minus", -10),
    ({"laying_type": "철탑"}, "laying_type_minus", -30),  # *
    ({"laying_type": "공동구"}, "laying_type_minus", -20), ({"laying_type": "관로구"}, "laying_type_minus", -10),
    ({"mid_joint": 7}, "mid_joint_minus", -7),
    ({"end_joint": "WEBG"}, "end_joint_minus", -30), ({"end_joint": "DEBG, EBA"}, "end_joint_minus", -5),
    ({"emerge_resp": "24시간이하"}, "emerge_resp_minus", -10), ({"emerge_resp": "12시간이하"}, "emerge_resp_minus", -5),  # *
    ({"emerge_resp": "1시간이하"}, "emerge_resp_minus", -3),  # *
    ({"cable_length": 370}, "rep_cost_minus", -2), ({"cable_length": 371}, "rep_cost_minus", -4),  # 비용 = 길이×0.0135
    ({"cable_length": 741}, "rep_cost_minus", -6), ({"cable_length": 1482}, "rep_cost_minus", -8),
    ({"cable_length": 3704}, "rep_cost_minus", -10), ({"cable_length": 7408}, "rep_cost_minus", -12),
    ({"rep_time": "3개월초과"}, "rep_time_minus", -10),  # *
    ({"reliability": 3}, "reliability_minus", 0), ({"reliability": 2}, "reliability_minus", -20),
    ({"reliability": 1}, "reliability_minus", -20),  # *
    ({"temp_diag": "X"}, "temp_diag_minus", -10), ({"pd_diag": "X"}, "pd_diag_minus", -10),  # *
    ({"live_line_diag": "X"}, "live_line_diag_minus", -10), ({"cable_move_diag": "X"}, "cable_move_diag_minus", -10),
    ({"offline_diag": "미실시"}, "offline_diag_minus", -20), ({"offline_diag": "3년이내"}, "offline_diag_minus", -10),  # *
    ({"longlife_insul": "X"}, "longlife_insul_minus", -10),
    ({"operation_start_time": date.today() - timedelta(days=int(12.5 * 365))}, "age_minus", -12),
]


@pytest.mark.parametrize(("overrides", "column", "expected"), BRANCHES)
def test_deduction_branches(overrides, column, expected):
    assert ef3_cable.calculate(_base_row(**overrides))[column] == expected


def test_base_row_totals_and_age_in_pof():
    base = ef3_cable.calculate(_base_row())
    assert base["pof"] == 100
    assert base["cof"] == 100 - 1 - 2  # 사고영향성 round(-1.0), 사고복구비용 최소 -2
    assert base["dof"] == 100
    # 경과연수는 원본대로 PoF에 바로 합산된다(EF1과 같고, GIS 원본과는 다름)
    aged = ef3_cable.calculate(_base_row(operation_start_time=date.today() - timedelta(days=20 * 365)))
    assert aged["age_minus"] == -20 and aged["pof"] == 80
    assert aged["total_score"] == pytest.approx(0.5 * 80 + 0.3 * 97 + 0.2 * 100)


def test_worst_case_scores_can_go_negative_and_are_kept():
    worst = _base_row(
        max_load=200, max_temp=95.0, diff_temp=11.0, failure_rate=0.01, pd_num=3, sys_cycle_curr=101.0,
        svl_leak_curr=1.1, joint_ex_damage="이상", cable_move=11.0,
        operation_start_time=date.today() - timedelta(days=30 * 365),
    )
    assert ef3_cable.calculate(worst)["pof"] == 100 - (30 + 20 + 20 + 10 + 10 + 20 + 10 + 10 + 5 + 20)  # 원본대로 음수 저장


def test_matches_reference_formulas(ref):
    random.seed(20261020)
    rows = [ef3_cable.generate_input_row() for _ in range(300)]
    rows += [_base_row(**overrides) for overrides, _, _ in BRANCHES]
    for row in rows:
        ours = ef3_cable.calculate(row)
        theirs = _ref_calculate(ref, row)
        for name in CALC_NAMES:
            assert ours[name] == theirs[name], (name, row)


def test_columns_match_reference_names(ref):
    assert [c["name"] for c in ef3_cable.INPUT_COLUMNS] == [c["name"] for c in ref.INPUT_COLUMNS]
    assert CALC_NAMES == [c["name"] for c in ref.CALCULATED_COLUMNS]


def test_breakdown_covers_every_summed_deduction():
    """메타데이터 항목 = 원본 합계식에 들어가는 감점 전부(빠지거나 남는 것 없이)."""
    fields = {axis: {i["field"] for i in items} for axis, items in ef3_cable.BREAKDOWN.items()}
    assert len(fields["pof"]) == 10 and len(fields["cof"]) == 7 and len(fields["dof"]) == 7
    row = ef3_cable.calculate(_base_row(operation_start_time=date.today() - timedelta(days=3650), pd_num=1))
    for axis in ("pof", "cof", "dof"):
        assert sum(row[f] for f in fields[axis]) == row[f"{axis}_minus"], axis


def test_mock_rows_pass_import_validation_and_calculate():
    random.seed(7)
    for _ in range(1000):
        row = ef3_cable.generate_input_row()
        for col in ef3_cable.INPUT_COLUMNS:
            assert _check_allowed(row[col["name"]], col) is None, (col["name"], row[col["name"]])
        calc = ef3_cable.calculate(row)
        assert 0 <= calc["pof"] <= 100 and 0 <= calc["cof"] <= 100 and 0 <= calc["dof"] <= 100


# ------------------------------------------------------------------ 임포트
def _fmt(v):
    return v.isoformat() if isinstance(v, date) else str(v)


def _write_ef3_dat(tmp_path, rows, name="ef3.dat"):
    names = [c["name"] for c in ef3_cable.INPUT_COLUMNS]
    lines = ["\t".join(names)] + ["\t".join(_fmt(r[n]) for n in names) for r in rows]
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


async def test_import_valid_ef3_file_fills_all_cable_tables(session_factory, tmp_path):
    rows = [ef3_cable.generate_input_row() for _ in range(4)]
    rows[0]["end_joint"] = "DEBG, EBA"  # 쉼표 든 값도 탭 구분 파일에선 한 칸
    async with session_factory() as session:
        result = await import_file(_write_ef3_dat(tmp_path, rows), "EF3", session)
        assert result.ok, (result.file_errors, result.row_errors)
        assert result.imported_rows == 4
        for model in (CableSpec, CableCondition, CableConsequenceAttribute, CableDesignAttribute, CableScoreDetail):
            assert await session.scalar(select(func.count()).select_from(model)) == 4, model.__tablename__
        names = (await session.execute(select(Equipment.equipment_name).where(Equipment.ef_code == "EF3"))).scalars().all()
        assert sorted(names) == sorted(r["tl_name"] for r in rows)
        assert "DEBG, EBA" in (await session.execute(select(CableSpec.end_joint))).scalars().all()


@pytest.mark.parametrize(
    ("column", "bad_value", "reason_part"),
    [
        ("laying_type", "지중", "허용값 아님"),      # 원본 판정에 없는 값 → 원본은 조용히 0점
        ("end_joint", "DEBG,EBA", "허용값 아님"),   # 공백 빠진 표기
        ("temp_diag", "o", "허용값 아님"),          # 소문자
        ("offline_diag", "2년이내", "허용값 아님"),
        ("cable_mva", 0, "미만"),                  # 부하율 분모
        ("pd_num", -1, "미만"),
        ("tl_name", "", "빈 값"),
    ],
)
async def test_import_rejects_out_of_range_values(session_factory, tmp_path, column, bad_value, reason_part):
    rows = [ef3_cable.generate_input_row() for _ in range(3)]
    rows[1][column] = bad_value
    async with session_factory() as session:
        result = await import_file(_write_ef3_dat(tmp_path, rows), "EF3", session)
        assert not result.ok
        assert [(e.row_number, e.column) for e in result.row_errors] == [(3, column)]
        assert reason_part in result.row_errors[0].reason
        assert await count_type(session, "EF3") == 0


# ------------------------------------------------------------------ 다른 유형과 공존
async def _others_fingerprint(session):
    rows = (
        await session.execute(
            select(Equipment.equipment_id, Equipment.ef_code, Equipment.equipment_name, ScoreSnapshot.total_score)
            .join(ScoreSnapshot, ScoreSnapshot.equipment_id == Equipment.equipment_id)
            .where(Equipment.ef_code != "EF3")
            .order_by(Equipment.equipment_id)
        )
    ).all()
    return rows


async def test_ef3_replace_import_keeps_other_types_intact(client, session_factory, tmp_path):
    async with session_factory() as session:
        for _ in range(2):
            await ingest_row(ef2_gis.calculate(ef2_gis.generate_input_row()), session)
        for _ in range(5):
            await ingest_row(ef3_cable.calculate(ef3_cable.generate_input_row()), session)
        await session.commit()
        before = await _others_fingerprint(session)
        assert {r.ef_code for r in before} == {"EF1", "EF2"} and await count_type(session, "EF3") == 5

        real_rows = [ef3_cable.generate_input_row() for _ in range(2)]
        result = await import_file(_write_ef3_dat(tmp_path, real_rows), "EF3", session, replace=True)

        assert result.ok and result.replaced_rows == 5 and result.imported_rows == 2
        assert await count_type(session, "EF3") == 2
        assert await session.scalar(select(func.count()).select_from(CableScoreDetail)) == 2
        assert await _others_fingerprint(session) == before


async def test_ef3_detail_and_metadata_api(client, session_factory):
    async with session_factory() as session:
        eq_id = await ingest_row(ef3_cable.calculate(ef3_cable.generate_input_row()), session)
        await session.commit()

    body = (await client.get(f"/api/equipment/{eq_id}")).json()
    assert body["ef_code"] == "EF3" and body["ef_name"] == "초고압케이블"
    td = body["type_detail"]
    assert td["ef_code"] == "EF3"
    assert {"spec", "condition", "consequence", "design", "score_detail"} <= td.keys()
    assert "rep_cost" in td["score_detail"]

    items = (await client.get("/api/equipment", params={"ef_code": "EF3"})).json()
    assert [i["ef_code"] for i in items] == ["EF3"]
    assert items[0]["last_diag_date"] == date.today().isoformat()  # 상태값 측정일(반영 기준일)
    types = {t["ef_code"]: t for t in (await client.get("/api/equipment-types")).json()}
    assert types["EF3"]["equipment_count"] == 1
    assert [i["label"] for i in types["EF3"]["breakdown"]["pof"]][0] == "경과연수"


# ------------------------------------------------------------------ 마이그레이션
def test_cable_migration_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "cable_migrate.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    def tables():
        with sqlite3.connect(db_path) as conn:
            return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    try:
        cfg = Config()
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        cable_tables = {m.__tablename__ for m in ef3_cable.DOMAIN_TABLES}

        command.upgrade(cfg, "head")
        assert cable_tables <= tables()

        command.downgrade(cfg, "d7a2c5e8f1b4")
        assert not cable_tables & tables()
        assert {"gis_operation", "transformer_spec", "equipment"} <= tables()

        command.upgrade(cfg, "head")
        assert cable_tables <= tables()
    finally:
        get_settings.cache_clear()
