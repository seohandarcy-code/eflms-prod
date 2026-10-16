"""Stage 8-1 마이그레이션(8a1c4e2f9b70) — equipment 공통 레이어 일반화가 기존 EF1 데이터를
잃지 않고 올라가고, downgrade로 원래 모양까지 되돌아오는지 확인한다.

다른 테스트는 Base.metadata.create_all로 스키마를 만들기 때문에 마이그레이션 경로 자체는
여기서만 검증된다. alembic.ini를 쓰지 않고 Config를 직접 만든다 — ini의 fileConfig가
기존 로거를 꺼버려서 다른 테스트의 caplog를 깨뜨리기 때문.
"""

import sqlite3

import pytest
from alembic import command
from alembic.config import Config

from app.core.config import BACKEND_DIR, get_settings

BEFORE = "3d49abc45e95"
TARGET = "8a1c4e2f9b70"


@pytest.fixture
def alembic_cfg(tmp_path, monkeypatch):
    db_path = tmp_path / "migrate.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    cfg = Config()
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    yield cfg, db_path
    get_settings.cache_clear()


def _columns(conn, table):
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def test_upgrade_moves_ef1_specs_and_downgrade_restores(alembic_cfg):
    cfg, db_path = alembic_cfg
    command.upgrade(cfg, BEFORE)

    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO equipment_type (ef_code, name) VALUES ('EF1', '변압기')")
        conn.executemany(
            "INSERT INTO equipment (factory_code, ef_code, transformer_name, voltage, onan_val, onaf_val, "
            "operation_start_time) VALUES (?, 'EF1', ?, 154000, ?, ?, '2005-01-01')",
            [("H1", "TR1", 25, 30.0), ("H1", "BANK3", 80, 100.0)],
        )

    command.upgrade(cfg, TARGET)

    with sqlite3.connect(db_path) as conn:
        cols = _columns(conn, "equipment")
        assert "equipment_name" in cols
        assert not {"transformer_name", "onan_val", "onaf_val"} & set(cols)
        rows = conn.execute(
            "SELECT e.equipment_name, t.onan_val, t.onaf_val FROM equipment e "
            "JOIN transformer_spec t USING (equipment_id) ORDER BY e.equipment_name"
        ).fetchall()
        assert rows == [("BANK3", 80, 100.0), ("TR1", 25, 30.0)]
        # 자연키가 새 컬럼 이름으로 다시 걸렸는지
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO equipment (factory_code, ef_code, equipment_name, voltage, operation_start_time) "
                "VALUES ('H1', 'EF1', 'TR1', 154000, '2010-01-01')"
            )

    command.downgrade(cfg, BEFORE)

    with sqlite3.connect(db_path) as conn:
        assert "transformer_spec" not in {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
        rows = conn.execute(
            "SELECT transformer_name, onan_val, onaf_val FROM equipment ORDER BY transformer_name"
        ).fetchall()
        assert rows == [("BANK3", 80, 100.0), ("TR1", 25, 30.0)]
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO equipment (factory_code, ef_code, transformer_name, voltage, onan_val, onaf_val, "
                "operation_start_time) VALUES ('H1', 'EF1', 'TR1', 154000, 25, 30.0, '2010-01-01')"
            )
