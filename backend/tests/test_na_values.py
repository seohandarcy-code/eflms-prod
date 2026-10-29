"""Stage 11 — 값 없음(N/A → null) 처리.

- 임포트: `N/A`·`n/a`·`#N/A`는 null로 저장, 필수 컬럼(사업장·설비유형·설비명·가동년월·전압)은 거부, 빈 칸은 계속 오류
- 계산(모든 유형): null 입력은 그 값을 쓰는 감점만 0으로 만들고, 다른 감점은 바꾸지 않는다
- 저장값(null 포함)으로 복원해 재계산해도 저장 점수와 같고, 상세 API는 null을 그대로 준다
- 마이그레이션: null이 남아 있으면 되돌리기를 멈춘다
"""
import random
import sqlite3
from datetime import date

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.core.config import BACKEND_DIR, get_settings
from app.db.models import DgaReading, Equipment, PeriodicInspection, ScoreSnapshot, SwitchgearCondition
from app.equipment_types import ef1_transformer, ef4_switchgear
from app.equipment_types.na import is_na_token
from app.equipment_types.registry import all_modules
from app.services.dataset_service import count_type
from app.services.import_service import NOT_NULLABLE_COLUMNS, import_file

# EF1은 계산 결과 키와 메타데이터(DB 컬럼) 이름이 다른 항목이 있다(test_type_queries와 같은 매핑).
DB_TO_CALC = {"oltc_96t_minus": "oltc_96T_minus", "first_voltage": "1st_voltage", "first_voltage_minus": "1st_voltage_minus"}


def _nullable_inputs(module):
    fixed = NOT_NULLABLE_COLUMNS | {module.NAME_FIELD}
    return [c["name"] for c in module.INPUT_COLUMNS if c["name"] not in fixed]


@pytest.mark.parametrize("raw", ["N/A", "n/a", " N/A ", "#N/A", "#n/a"])
def test_na_tokens(raw):
    assert is_na_token(raw)


@pytest.mark.parametrize("raw", ["", "NA", "없음", "N/A값", "-"])
def test_not_na_tokens(raw):
    assert not is_na_token(raw)


@pytest.mark.parametrize("module", all_modules(), ids=lambda m: m.EF_CODE)
def test_null_input_only_zeroes_the_deductions_that_use_it(module):
    """어떤 입력이 null이어도 계산이 멈추지 않고, 감점 항목은 원래 값 그대로이거나 0이 된다."""
    random.seed(11)
    leaves = [DB_TO_CALC.get(i["field"], i["field"]) for axis in module.BREAKDOWN.values() for i in axis]
    for _ in range(15):
        row = module.generate_input_row()
        base = module.calculate(row)
        for name in _nullable_inputs(module):
            out = module.calculate({**row, name: None})
            for field in leaves:
                assert out[field] in (base[field], 0), (name, field, base[field], out[field])
            assert all(out[k] is not None for k in out if k.endswith("_minus")), name
            assert out["pof"] == 100 + out["pof_minus"]


def test_ef1_na_judgement_no_longer_scores_as_bad():
    """예전엔 'N/A'라는 글자가 '양호'가 아니라서 부분방전 -20이 붙었다 — 이제 null → 감점 0."""
    random.seed(1)
    row = ef1_transformer.generate_input_row()
    row["part_discharge_diag"] = "양호"
    assert ef1_transformer.calculate({**row, "part_discharge_diag": "N/A"})["part_discharge_minus"] == -20
    assert ef1_transformer.calculate({**row, "part_discharge_diag": None})["part_discharge_minus"] == 0


def test_derived_values_become_null_and_their_deductions_zero():
    random.seed(2)
    row = ef1_transformer.generate_input_row()
    out = ef1_transformer.calculate({**row, "dga_h2": None})
    assert out["dga_tcg"] is None and out["dga_diag"] is None and out["dga_minus"] == 0
    out = ef1_transformer.calculate({**row, "dielec_str_te_3": None})
    assert out["dielec_str_te_avg"] is None and out["dielec_str_te_minus"] == 0


# ------------------------------------------------------------------ 임포트
def _fmt(v):
    return v.isoformat() if isinstance(v, date) else str(v)


def _write_dat(tmp_path, module, rows, name="na.dat"):
    names = [c["name"] for c in module.INPUT_COLUMNS]
    lines = ["\t".join(names)] + ["\t".join(_fmt(r[n]) for n in names) for r in rows]
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


async def test_import_stores_na_as_null_and_scores_zero(client, session_factory, tmp_path):
    random.seed(5)
    rows = [ef4_switchgear.generate_input_row() for _ in range(3)]
    rows[0]["max_temp_chk"] = 45   # 원래라면 -8
    rows[1]["max_temp_chk"] = "N/A"
    rows[1]["install_building"] = "#N/A"
    rows[2]["eqp_building"] = "n/a"
    async with session_factory() as session:
        result = await import_file(_write_dat(tmp_path, ef4_switchgear, rows), "EF4", session)
        assert result.ok, result.row_errors
        assert result.na_values == {"max_temp_chk": 1, "install_building": 1, "eqp_building": 1}
        by_name = {
            e.equipment_name: e.equipment_id
            for e in (await session.execute(select(Equipment).where(Equipment.ef_code == "EF4"))).scalars()
        }
        temps = dict((await session.execute(select(SwitchgearCondition.equipment_id, SwitchgearCondition.max_temp_chk))).all())
        assert temps[by_name[rows[1]["eqp_id"]]] is None
        assert temps[by_name[rows[0]["eqp_id"]]] == 45

    na_id = by_name[rows[1]["eqp_id"]]
    body = (await client.get(f"/api/equipment/{na_id}")).json()
    td = body["type_detail"]
    assert td["condition"]["max_temp_chk"] is None and td["spec"]["install_building"] is None
    assert td["score_detail"]["max_temp_chk_minus"] == 0 and td["score_detail"]["install_building_minus"] == 0
    assert len(body["projection"]) > 1  # null 포함 저장값으로도 예측 재계산이 된다


async def test_load_inputs_with_nulls_reproduces_stored_scores(session_factory, tmp_path):
    random.seed(6)
    rows = [ef1_transformer.generate_input_row() for _ in range(2)]
    rows[0]["dga_h2"] = "N/A"
    rows[0]["oltc_type"] = "N/A"
    rows[1]["coil_max_temp"] = "N/A"
    async with session_factory() as session:
        result = await import_file(_write_dat(tmp_path, ef1_transformer, rows), "EF1", session, replace=True)
        assert result.ok, result.row_errors
        ids = (await session.execute(select(Equipment.equipment_id).where(Equipment.ef_code == "EF1"))).scalars().all()
        for eq_id in ids:
            input_row, as_of = await ef1_transformer.load_inputs(session, eq_id)
            recalculated = ef1_transformer.calculate(input_row, as_of=as_of)
            score = await session.get(ScoreSnapshot, eq_id)
            assert recalculated["total_score"] == pytest.approx(score.total_score)
        assert None in (await session.execute(select(DgaReading.dga_h2))).scalars().all()
        assert None in (await session.execute(select(PeriodicInspection.oltc_type))).scalars().all()


@pytest.mark.parametrize("column", ["factory_code", "eqp_id", "operation_start_time"])
async def test_import_rejects_na_in_required_columns(session_factory, tmp_path, column):
    rows = [ef4_switchgear.generate_input_row() for _ in range(2)]
    rows[1][column] = "N/A"
    async with session_factory() as session:
        result = await import_file(_write_dat(tmp_path, ef4_switchgear, rows), "EF4", session)
        assert not result.ok
        assert [(e.row_number, e.column, e.reason) for e in result.row_errors] == [(3, column, "N/A 불가(필수 컬럼)")]
        assert await count_type(session, "EF4") == 0


async def test_import_rejects_na_voltage(session_factory, tmp_path):
    rows = [ef1_transformer.generate_input_row() for _ in range(2)]
    rows[0]["voltage"] = "N/A"
    async with session_factory() as session:
        result = await import_file(_write_dat(tmp_path, ef1_transformer, rows), "EF1", session)
        assert [(e.row_number, e.column) for e in result.row_errors] == [(2, "voltage")]


async def test_blank_cell_is_still_an_error(session_factory, tmp_path):
    """빈 칸은 실수로 빠뜨린 값일 수 있어 N/A로 보지 않는다(2026-10-29 결정)."""
    rows = [ef4_switchgear.generate_input_row() for _ in range(2)]
    rows[0]["max_temp_chk"] = ""
    async with session_factory() as session:
        result = await import_file(_write_dat(tmp_path, ef4_switchgear, rows), "EF4", session)
        assert [(e.row_number, e.column) for e in result.row_errors] == [(2, "max_temp_chk")]
        assert "빈 값" in result.row_errors[0].reason


# ------------------------------------------------------------------ 마이그레이션
def test_na_migration_round_trip_and_downgrade_guard(tmp_path, monkeypatch):
    db_path = tmp_path / "na_migrate.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    def notnull(table, column):
        with sqlite3.connect(db_path) as conn:
            return {r[1]: r[3] for r in conn.execute(f"PRAGMA table_info({table})")}[column]

    try:
        cfg = Config()
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        command.upgrade(cfg, "head")
        assert notnull("switchgear_condition", "max_temp_chk") == 0
        assert notnull("switchgear_condition", "measured_at") == 1  # 계산 기준일 컬럼은 그대로
        assert notnull("switchgear_score_detail", "max_temp_chk_minus") == 1  # 감점은 그대로

        with sqlite3.connect(db_path) as conn:
            conn.execute("INSERT INTO equipment_type (ef_code, name) VALUES ('EF4', '수배전반')")
            conn.execute(
                "INSERT INTO equipment (equipment_id, factory_code, ef_code, equipment_name, voltage, operation_start_time, created_at)"
                " VALUES (1, 'H1', 'EF4', 'eqp1', 0, '2010-01-01', '2026-10-29')"
            )
            conn.execute(
                "INSERT INTO switchgear_condition (equipment_id, measured_at, part_thermal_chk, elec_room_avg_temp,"
                " temp_diff_chk, max_temp_chk, load_chk, ex_box_chk, noise_chk, bolt_chk)"
                " VALUES (1, '2026-10-29', '양호', 25, 0, NULL, 0.3, '양호', '양호', '양호')"
            )
        with pytest.raises(RuntimeError, match="switchgear_condition.max_temp_chk"):
            command.downgrade(cfg, "6e6b51952ee7")

        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE switchgear_condition SET max_temp_chk = 25")
        command.downgrade(cfg, "6e6b51952ee7")
        assert notnull("switchgear_condition", "max_temp_chk") == 1
        command.upgrade(cfg, "head")
        assert notnull("switchgear_condition", "max_temp_chk") == 0
    finally:
        get_settings.cache_clear()
