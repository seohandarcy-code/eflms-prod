"""감점 소수 계산 (2026-11-19 사용자 결정) — 모든 설비유형 공통.

- 감점 항목(`_minus`)은 전부 float이고 소수 첫째 자리다(정수 반올림 없이 계산, 결과만 소수 첫째 자리).
- 경과연수 감점 = -운전년수(원본은 -floor) — 소수 부분이 그대로 감점에 들어간다.
- 합산되는 항목 감점을 더하면 축 감점과 정확히 같다(항목마다 반올림한 뒤 합친다).
- EF1~EF4 감점 컬럼 INTEGER → FLOAT 마이그레이션 왕복, 저장 점수를 새 규칙으로 맞추는 재계산 명령.
"""
import random
import sqlite3
from datetime import date, timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, update

from app.core.config import BACKEND_DIR, get_settings
from app.db import recalculate
from app.db.models import ScoreSnapshot, SwitchgearScoreDetail, TransformerScoreDetail
from app.equipment_types import ef1_transformer, ef4_switchgear, ef5_ups
from app.equipment_types.registry import all_modules
from app.equipment_types.rounding import round1
from app.services.ingest import ingest_row
from app.services.reference_data import has_reference, mock_reference

DB_TO_CALC = {"oltc_96t_minus": "oltc_96T_minus", "first_voltage_minus": "1st_voltage_minus"}
FLOAT_MIGRATION = "f3b8d1e6a9c4"
SCORE_DETAIL_TABLES = ("transformer_score_detail", "gis_score_detail", "cable_score_detail", "switchgear_score_detail")


def _calc(module, row, **kwargs):
    if has_reference(module):
        kwargs["reference"] = mock_reference(module)
    return module.calculate(row, **kwargs)


def _leaves(module, axis):
    return [DB_TO_CALC.get(i["field"], i["field"]) for i in module.BREAKDOWN[axis] if i.get("summed", True)]


@pytest.mark.parametrize("module", all_modules(), ids=lambda m: m.EF_CODE)
def test_every_deduction_is_a_one_decimal_float_and_items_add_up(module):
    random.seed(20261119)
    for _ in range(200):
        out = _calc(module, module.generate_input_row())
        for name, value in out.items():
            if name.endswith("_minus"):
                assert type(value) is float, (name, value)
                assert value == round1(value), (name, value)
        for axis in ("pof", "cof", "dof"):
            assert round1(sum(out[f] for f in _leaves(module, axis))) == out[f"{axis}_minus"], axis
            assert out[axis] == round1(100 + out[f"{axis}_minus"])


@pytest.mark.parametrize("module", all_modules(), ids=lambda m: m.EF_CODE)
def test_age_deduction_keeps_the_fraction_of_a_year(module):
    row = module.generate_input_row()
    row["operation_start_time"] = date.today() - timedelta(days=int(12.7 * 365))
    out = _calc(module, row)
    assert out["operation_year"] == 12.7
    assert out["age_minus"] == -12.7  # 원본은 -floor(12.7) = -12


def test_na_deduction_is_float_zero():
    row = ef1_transformer.generate_input_row()
    row["coil_max_temp"] = None
    out = ef1_transformer.calculate(row)
    assert out["temp_minus"] == 0 and type(out["temp_minus"]) is float


# ------------------------------------------------------------------ 재계산 명령
async def test_recalculate_restores_scores_with_current_rules(session_factory, monkeypatch):
    modules = (ef1_transformer, ef4_switchgear, ef5_ups)
    async with session_factory() as session:
        expected = {}
        for module in modules:
            row = module.calculate(module.generate_input_row())
            eq_id = await ingest_row(row, session)
            expected[eq_id] = (row["pof"], row["total_score"], row["age_minus"])
            assert row["age_minus"] != -1.0
        await session.commit()
        # 예전(정수) 규칙으로 저장된 상태를 흉내 낸다
        await session.execute(update(ScoreSnapshot).values(pof=0.0, total_score=0.0))
        await session.execute(update(TransformerScoreDetail).values(age_minus=-1.0))
        await session.execute(update(SwitchgearScoreDetail).values(age_minus=-1.0))
        await session.commit()

    monkeypatch.setattr(recalculate, "async_session_factory", session_factory)
    assert await recalculate.run("all") is True

    async with session_factory() as session:
        stored = {r.equipment_id: (r.pof, r.total_score) for r in (await session.execute(select(ScoreSnapshot))).scalars()}
        assert stored == {eq_id: exp[:2] for eq_id, exp in expected.items()}
        for model in (TransformerScoreDetail, SwitchgearScoreDetail):
            for eq_id, age in (await session.execute(select(model.equipment_id, model.age_minus))).all():
                assert age == expected[eq_id][2]


async def test_recalculate_rejects_unknown_type(monkeypatch, session_factory):
    monkeypatch.setattr(recalculate, "async_session_factory", session_factory)
    with pytest.raises(Exception):
        await recalculate.run("EF99")


# ------------------------------------------------------------------ 마이그레이션
def test_score_detail_float_migration_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "deduction_float.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    def col_type(table, column="age_minus"):
        with sqlite3.connect(db_path) as conn:
            return {r[1]: r[2] for r in conn.execute(f"PRAGMA table_info({table})")}[column]

    try:
        cfg = Config()
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        command.upgrade(cfg, "head")
        assert {col_type(t) for t in SCORE_DETAIL_TABLES} == {"FLOAT"}
        assert col_type("switchgear_score_detail", "scale_dam_chk_minus") == "FLOAT"

        command.downgrade(cfg, "-1")  # 소수 감점이 없으면 되돌릴 수 있다
        assert {col_type(t) for t in SCORE_DETAIL_TABLES} == {"INTEGER"}

        command.upgrade(cfg, "head")
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            cols = [r[1] for r in conn.execute("PRAGMA table_info(cable_score_detail)")]
            values = {c: 0.0 for c in cols} | {
                "equipment_id": 1, "computed_at": "2026-11-19 00:00:00", "today": "2026-11-19",
                "operation_year": 12.7, "age_minus": -12.7,
            }
            conn.execute(
                f"INSERT INTO cable_score_detail ({', '.join(values)}) VALUES ({', '.join('?' * len(values))})",
                list(values.values()),
            )
        with pytest.raises(RuntimeError, match="cable_score_detail.age_minus"):
            command.downgrade(cfg, "-1")
        assert col_type("cable_score_detail") == "FLOAT"
    finally:
        get_settings.cache_clear()
