"""Stage 13-0 — 점수 지표(POF·COF·DOF 감점/점수, 종합점수) 소수 첫째 자리.

- 반올림은 엑셀 ROUND처럼 5에서 올린다(-0.25 → -0.3)
- 모든 유형의 calculate()가 점수 지표를 소수 첫째 자리로 내고, 원본이 정수인 값은 그대로다
- score_snapshot 6개 컬럼은 FLOAT, 되돌리기는 소수 값이 없을 때만
"""
import random
import sqlite3

import pytest
from alembic import command
from alembic.config import Config

from app.core.config import BACKEND_DIR, get_settings
from app.equipment_types.registry import all_modules
from app.equipment_types.rounding import SCORE_FIELDS, round1
from app.services.equipment_service import classify_status


@pytest.mark.parametrize(
    ("value", "expected"),
    [(-0.25, -0.3), (0.25, 0.3), (-24.75, -24.8), (62.800000000000004, 62.8), (69.19999999999999, 69.2), (-13, -13.0), (0, 0.0), (1.05, 1.1)],
)
def test_round1_rounds_half_away_from_zero(value, expected):
    assert round1(value) == expected


@pytest.mark.parametrize("module", all_modules(), ids=lambda m: m.EF_CODE)
def test_calculate_returns_one_decimal_scores(module):
    random.seed(12)
    for _ in range(20):
        out = module.calculate(module.generate_input_row())
        for name in SCORE_FIELDS:
            assert out[name] == round1(out[name]), (name, out[name])
        assert out["pof"] == round1(100 + out["pof_minus"])
        assert out["total_score"] == round1(0.5 * out["pof"] + 0.3 * out["cof"] + 0.2 * out["dof"])


def test_classify_status_with_decimal_scores():
    assert classify_status(60.0, 50, 50) == "review"
    assert classify_status(60.1, 50, 50) == "normal"
    assert classify_status(45.0, 60.3, 61) == "review"  # COF·DOF 60 초과 → 완화 기준(정상 >50)
    assert classify_status(29.9, 60.3, 61) == "replace"


def test_score_migration_round_trip_and_downgrade_guard(tmp_path, monkeypatch):
    db_path = tmp_path / "score_precision.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    def coltype(column):
        with sqlite3.connect(db_path) as conn:
            return {r[1]: r[2] for r in conn.execute("PRAGMA table_info(score_snapshot)")}[column]

    try:
        cfg = Config()
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        command.upgrade(cfg, "b7f98e26abb7")
        with sqlite3.connect(db_path) as conn:
            conn.execute("INSERT INTO equipment_type (ef_code, name) VALUES ('EF4', '수배전반')")
            conn.execute(
                "INSERT INTO equipment (equipment_id, factory_code, ef_code, equipment_name, voltage, operation_start_time, created_at)"
                " VALUES (1, 'H1', 'EF4', 'eqp1', 0, '2010-01-01', '2026-11-06')"
            )
            conn.execute(
                "INSERT INTO score_snapshot (equipment_id, pof_minus, pof, cof_minus, cof, dof_minus, dof, total_score)"
                " VALUES (1, -38, 62, -30, 70, -13, 87, 69.19999999999999)"
            )
        command.upgrade(cfg, "head")
        assert coltype("pof") == "FLOAT"
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT pof, total_score FROM score_snapshot").fetchone() == (62, 69.2)
            conn.execute("UPDATE score_snapshot SET pof = 61.5")
        with pytest.raises(RuntimeError, match="score_snapshot.pof"):
            command.downgrade(cfg, "b7f98e26abb7")

        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE score_snapshot SET pof = 62")
        command.downgrade(cfg, "b7f98e26abb7")
        assert coltype("pof") == "INTEGER"
        command.upgrade(cfg, "head")
        assert coltype("pof") == "FLOAT"
    finally:
        get_settings.cache_clear()
