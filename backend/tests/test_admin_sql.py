"""Stage 16-5 — 관리자 SQL 조회: 조회만·허용 목록 테이블만·행/시간 제한·admin만."""
import pytest

from app.auth.state import AdminAuthStore, get_auth_store
from app.core.config import get_settings
from app.main import app
from app.services import sql_query_service
from app.services.sql_query_service import SqlQueryError, normalize_sql


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


async def _sql(client, headers, sql):
    return await client.post("/api/admin/sql", json={"sql": sql}, headers=headers)


async def test_select_returns_columns_and_rows(client, admin):
    resp = await _sql(client, admin, "SELECT equipment_id, ef_code, equipment_name FROM equipment ORDER BY equipment_id;")
    body = resp.json()
    assert resp.status_code == 200
    assert body["columns"] == ["equipment_id", "ef_code", "equipment_name"]
    assert body["row_count"] == 3 and len(body["rows"]) == 3
    assert body["rows"][0][1] == "EF1"
    assert body["truncated"] is False and body["max_rows"] == 1000
    assert isinstance(body["elapsed_ms"], int)


async def test_joins_ctes_comments_and_nulls(client, admin):
    sql = """
    -- 점수 붙여 보기
    /* 여러 줄
       주석 */
    WITH s AS (SELECT equipment_id, total_score FROM score_snapshot)
    SELECT e.equipment_name, s.total_score, NULL AS memo
    FROM equipment e JOIN s ON s.equipment_id = e.equipment_id
    """
    body = (await _sql(client, admin, sql)).json()
    assert body["columns"] == ["equipment_name", "total_score", "memo"]
    assert body["row_count"] == 3 and body["rows"][0][2] is None

    body = (await _sql(client, admin, "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<5) SELECT count(*) FROM n")).json()
    assert body["rows"] == [[5]]


async def test_row_limit_truncates(client, admin):
    sql = "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<1500) SELECT x FROM n"
    body = (await _sql(client, admin, sql)).json()
    assert body["row_count"] == 1000 and body["truncated"] is True


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM equipment",
        "UPDATE equipment SET equipment_name='x'",
        "INSERT INTO equipment_type(ef_code) VALUES ('X')",
        "DROP TABLE equipment",
        "PRAGMA table_info(equipment)",
        "ATTACH DATABASE 'x.db' AS x",
        "",
        "   ",
    ],
)
async def test_non_select_rejected_before_running(client, admin, sql):
    resp = await _sql(client, admin, sql)
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "sql",
    [
        # SELECT/WITH로 시작해도 DB 쪽에서 막힌다(읽기 전용 연결 + authorizer)
        "WITH x AS (SELECT 1) DELETE FROM equipment",
        "WITH x AS (SELECT 1) UPDATE equipment SET equipment_name = 'hacked'",
        "SELECT * FROM allowed_users",
        "WITH x AS (SELECT * FROM allowed_users) SELECT * FROM x",
        "SELECT * FROM equipment WHERE equipment_id IN (SELECT 1 FROM allowed_users)",
        "SELECT count(*) FROM allowed_users",
        "SELECT (SELECT count(*) FROM alembic_version)",
        "SELECT * FROM alembic_version",
        "SELECT name FROM sqlite_master",
        "SELECT * FROM pragma_table_info('equipment')",
        "SELECT 1; DELETE FROM equipment",
    ],
)
async def test_db_level_guards(client, admin, sql):
    resp = await _sql(client, admin, sql)
    assert resp.status_code == 400, resp.json()
    # 아무것도 바뀌지 않았다
    body = (await _sql(client, admin, "SELECT count(*), min(equipment_name) FROM equipment")).json()
    assert body["rows"][0][0] == 3 and body["rows"][0][1] != "hacked"


async def test_sql_error_message_is_shown(client, admin):
    resp = await _sql(client, admin, "SELECT nope FROM equipment")
    assert resp.status_code == 400 and "nope" in resp.json()["detail"]
    resp = await _sql(client, admin, "SELECT * FROM allowed_users")
    assert "허용되지 않은 동작" in resp.json()["detail"]


async def test_timeout_interrupts(client, session_factory):
    async with session_factory() as session:
        slow = "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n) SELECT count(*) FROM n"
        with pytest.raises(SqlQueryError, match="초를 넘어"):
            await sql_query_service.run_select_sql(session, slow, timeout=0.3)


async def test_sql_is_admin_only(client, store):
    assert (await _sql(client, {}, "SELECT 1")).status_code == 401
    for role in ("user", "general"):
        token, _ = store.issue_session(role)
        resp = await _sql(client, {"Authorization": f"Bearer {token}"}, "SELECT 1")
        assert resp.status_code == 403, role


def test_normalize_sql():
    assert normalize_sql("  select 1 ;; ") == "select 1"
    assert normalize_sql("-- c\nWITH a AS (SELECT 1) SELECT * FROM a").startswith("-- c")
    with pytest.raises(SqlQueryError):
        normalize_sql("x" * 10_001)
    with pytest.raises(SqlQueryError):
        normalize_sql("/* select */ delete from equipment")
