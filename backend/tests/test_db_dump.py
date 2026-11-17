"""Stage 16-8 — 전체 DB를 psql용 PostgreSQL .sql로 내려받기."""
import re
from datetime import date, datetime, time
from decimal import Decimal

import pytest

from app.auth.state import AdminAuthStore, get_auth_store
from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.services.db_dump_service import copy_value


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "local")
    get_settings.cache_clear()
    s = AdminAuthStore()
    app.dependency_overrides[get_auth_store] = lambda: s
    yield s
    app.dependency_overrides.pop(get_auth_store, None)
    get_settings.cache_clear()


@pytest.fixture
def admin(store):
    token, _ = store.issue_session("admin")
    return {"Authorization": f"Bearer {token}"}


def _copy_blocks(sql: str) -> dict[str, list[list[str]]]:
    blocks: dict[str, list[list[str]]] = {}
    for m in re.finditer(r"^COPY (\S+) \((.*?)\) FROM stdin;\n(.*?)^\\\.$", sql, re.S | re.M):
        rows = [line.split("\t") for line in m.group(3).splitlines() if line]
        blocks[m.group(1).strip('"')] = rows
    return blocks


def test_copy_value_escaping():
    assert copy_value(None) == r"\N"
    assert copy_value(True) == "t" and copy_value(False) == "f"
    assert copy_value(3) == "3" and copy_value(Decimal("1.50")) == "1.50"
    assert copy_value(0.1) == "0.1" and copy_value(float("nan")) == "NaN" and copy_value(float("-inf")) == "-Infinity"
    assert copy_value(date(2020, 6, 1)) == "2020-06-01"
    assert copy_value(datetime(2026, 11, 17, 9, 5, 3)) == "2026-11-17 09:05:03"
    assert copy_value(time(9, 5)) == "09:05:00"
    assert copy_value("홍\t길동\n2줄\r\\끝") == "홍\\t길동\\n2줄\\r\\\\끝"
    assert copy_value(r"\N") == r"\\N"  # 글자 그대로의 \N은 null과 구분된다
    assert copy_value(b"\x01\xff") == "\\\\x01ff"


async def test_dump_requires_admin(client, store):
    assert (await client.get("/api/admin/data/export-sql")).status_code == 401
    token, _ = store.issue_session("user")
    resp = await client.get("/api/admin/data/export-sql", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


async def test_dump_structure_and_data(client, admin):
    # 불리언·한글·특수문자가 들어간 행을 하나 넣어 둔다
    body = {"sso_id": "kim@company.com", "name": "김\t철수\\팀", "team": None, "is_admin": True}
    assert (await client.post("/api/admin/access-users", json=body, headers=admin)).status_code == 200

    resp = await client.get("/api/admin/data/export-sql", headers=admin)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/sql")
    assert re.search(r'filename="eflms_full_\d{8}_\d{4}\.sql"', resp.headers["content-disposition"])
    sql = resp.content.decode("utf-8")

    tables = Base.metadata.sorted_tables
    assert resp.headers["x-table-count"] == str(len(tables))
    assert "\\set ON_ERROR_STOP on" in sql and "SET client_encoding = 'UTF8';" in sql
    assert sql.index("BEGIN;") < sql.index("CREATE TABLE") < sql.index("COPY ") < sql.rindex("COMMIT;")
    assert "DROP " not in sql  # 빈 DB에 복원 — 기존 것을 지우지 않는다

    # 모든 테이블의 생성문과 COPY 블록, 외래키 의존 순서
    for t in tables:
        assert f"CREATE TABLE {t.name} (" in sql, t.name
    assert sql.index("CREATE TABLE equipment_type (") < sql.index("CREATE TABLE equipment (")
    assert "equipment_id SERIAL NOT NULL" in sql
    assert "CREATE TABLE alembic_version (" in sql

    blocks = _copy_blocks(sql)
    assert set(blocks) == {t.name for t in tables}
    assert len(blocks["equipment"]) == 3  # conftest의 EF1 3건
    assert int(resp.headers["x-row-count"]) == sum(len(r) for r in blocks.values())
    assert "-- 테이블별 행 수:" in sql and "--   equipment: 3" in sql

    # 칸 수가 컬럼 수와 같고, 날짜는 ISO, 불리언은 t/f, 특수문자는 이스케이프
    eq_cols = [c.name for c in Base.metadata.tables["equipment"].columns]
    for row in blocks["equipment"]:
        assert len(row) == len(eq_cols)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[eq_cols.index("operation_start_time")])
    user_cols = [c.name for c in Base.metadata.tables["allowed_users"].columns]
    (user,) = blocks["allowed_users"]
    assert user[user_cols.index("is_admin")] == "t"
    assert user[user_cols.index("name")] == "김\\t철수\\\\팀"
    assert user[user_cols.index("team")] == r"\N"

    # SERIAL 시퀀스 맞추기 — 자동 번호 테이블만
    assert "pg_get_serial_sequence('equipment', 'equipment_id')" in sql
    assert "pg_get_serial_sequence('battery_temp_decay_coef'" not in sql
    assert "pg_get_serial_sequence('allowed_users'" not in sql

    # 테스트 DB는 마이그레이션 없이 만들어서 버전 행은 없다(실제 DB면 INSERT INTO alembic_version)
    assert "INSERT INTO alembic_version" not in sql
