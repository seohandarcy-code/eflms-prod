"""서버 자동 점수 갱신 (Stage 21-1b, 2026-11-19).

- tick(): DB가 예전이면 건너뜀, 점수가 오늘 기준이면 아무것도 안 함(기록 없음), 이전이면 갱신(첫 확인 startup, 그 뒤 daily),
  다른 작업 중이면 건너뜀, 실패하면 1시간 동안 다시 시도하지 않음.
- 예전 DB(잠금 테이블 없음)에서 임포트는 500 대신 업그레이드 안내, 관리자 API도 안내.
- DB 버전 확인(alembic_version ↔ 코드 head), 반복 작업은 취소하면 깔끔하게 끝난다.
"""
import asyncio
import sqlite3
from datetime import date, datetime, timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.auth.state import AdminAuthStore, get_auth_store
from app.core.config import BACKEND_DIR, get_settings
from app.db.models import ScoreRefreshRun
from app.equipment_types import ef4_switchgear
from app.main import app
from app.services import job_lock, score_scheduler
from app.services.import_service import import_file
from app.services.ingest import ingest_row
from app.services.schema_check import SchemaStatus, code_head, schema_status

D = date(2026, 11, 18)


async def _seed(session_factory, as_of=D, n=2):
    async with session_factory() as session:
        for _ in range(n):
            await ingest_row(ef4_switchgear.calculate(ef4_switchgear.generate_input_row(), as_of=as_of), session)
        await session.commit()


async def _runs(session_factory):
    async with session_factory() as session:
        rows = (await session.execute(select(ScoreRefreshRun).order_by(ScoreRefreshRun.run_id))).scalars().all()
        return [(r.trigger, r.status, r.as_of) for r in rows]


async def test_tick_refreshes_only_when_scores_are_older_than_today(session_factory):
    await _seed(session_factory)
    state = score_scheduler.SchedulerState()

    assert await score_scheduler.tick(session_factory, state, D) == "fresh"  # 시작: 이미 오늘 기준
    assert await _runs(session_factory) == []
    assert await score_scheduler.tick(session_factory, state, D) == "fresh"  # 같은 날 다시 확인
    assert await score_scheduler.tick(session_factory, state, D + timedelta(days=1)) == "success"  # 날짜가 바뀜
    assert await _runs(session_factory) == [("daily", "success", D + timedelta(days=1))]
    assert await score_scheduler.stale_count(session_factory, D + timedelta(days=1)) == 0
    assert await score_scheduler.tick(session_factory, state, D + timedelta(days=1)) == "fresh"
    assert len(await _runs(session_factory)) == 1


async def test_first_tick_on_old_scores_is_recorded_as_startup(session_factory):
    await _seed(session_factory, as_of=D - timedelta(days=60))
    state = score_scheduler.SchedulerState()
    assert await score_scheduler.stale_count(session_factory, D) == 2
    assert await score_scheduler.tick(session_factory, state, D) == "success"
    assert await _runs(session_factory) == [("startup", "success", D)]


async def test_tick_skips_while_another_job_runs(session_factory):
    await _seed(session_factory, as_of=D - timedelta(days=1))
    engine = session_factory.kw["bind"]
    token = await job_lock.acquire(engine, "임포트 EF4")
    state = score_scheduler.SchedulerState()
    assert await score_scheduler.tick(session_factory, state, D) == "busy"
    assert await _runs(session_factory) == []
    await job_lock.release(engine, token)
    assert await score_scheduler.tick(session_factory, state, D) == "success"
    assert await _runs(session_factory) == [("daily", "success", D)]


async def test_failed_refresh_waits_an_hour_before_retrying(session_factory, monkeypatch):
    await _seed(session_factory, as_of=D - timedelta(days=1))

    def boom(*args, **kwargs):
        raise RuntimeError("계산 실패 흉내")

    monkeypatch.setattr(ef4_switchgear, "calculate", boom)
    state = score_scheduler.SchedulerState()
    now = datetime(2026, 11, 18, 9, 0)
    assert await score_scheduler.tick(session_factory, state, D, now=now) == "partial"  # EF4만 실패, 다른 유형은 0대
    assert await score_scheduler.tick(session_factory, state, D, now=now + timedelta(minutes=10)) == "waiting"
    monkeypatch.undo()
    assert await score_scheduler.tick(session_factory, state, D, now=now + timedelta(minutes=61)) == "success"
    assert [r[1] for r in await _runs(session_factory)] == ["partial", "success"]


async def test_tick_does_nothing_on_outdated_schema(session_factory, monkeypatch):
    await _seed(session_factory, as_of=D - timedelta(days=1))

    async def outdated(bind):
        return SchemaStatus(current="9df1f3504cfe", head=code_head(), known=True)

    monkeypatch.setattr(score_scheduler, "schema_status", outdated)
    state = score_scheduler.SchedulerState()
    assert await score_scheduler.tick(session_factory, state, D) == "schema"
    assert await score_scheduler.tick(session_factory, state, D) == "schema"
    assert await _runs(session_factory) == []


async def test_run_forever_stops_cleanly_when_cancelled(session_factory):
    task = asyncio.create_task(score_scheduler.run_forever(session_factory, 10))
    await asyncio.sleep(0.3)  # 첫 확인(빈 DB → fresh)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


# ------------------------------------------------------------------ 예전 DB(마이그레이션 전)
async def test_import_without_lock_table_returns_upgrade_hint(session_factory, tmp_path):
    async with session_factory() as session:
        await session.execute(text("DROP TABLE data_job_lock"))
        await session.commit()
    names = [c["name"] for c in ef4_switchgear.INPUT_COLUMNS]
    row = ef4_switchgear.generate_input_row()
    fmt = lambda v: v.isoformat() if isinstance(v, date) else str(v)  # noqa: E731
    path = tmp_path / "ef4.dat"
    path.write_text("\t".join(names) + "\n" + "\t".join(fmt(row[n]) for n in names) + "\n", encoding="utf-8")
    async with session_factory() as session:
        result = await import_file(str(path), "EF4", session)
    assert not result.ok and "alembic upgrade head" in result.file_errors[0]
    assert await job_lock.current_holder(session_factory.kw["bind"]) is None


@pytest.fixture
def admin_headers(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "local")
    get_settings.cache_clear()
    store = AdminAuthStore()
    app.dependency_overrides[get_auth_store] = lambda: store
    token, _ = store.issue_session("admin")
    yield {"Authorization": f"Bearer {token}"}
    app.dependency_overrides.pop(get_auth_store, None)
    get_settings.cache_clear()


async def test_admin_api_reports_schema_and_auto_settings(client, admin_headers, monkeypatch):
    body = (await client.get("/api/admin/score-refresh", headers=admin_headers)).json()
    assert body["schema"]["ok"] is True and body["schema"]["hint"] is None
    assert body["auto"] == {"enabled": True, "check_minutes": 10}

    from app.api.routes import admin_score_refresh

    async def outdated(bind):
        return SchemaStatus(current="9df1f3504cfe", head=code_head(), known=True)

    monkeypatch.setattr(admin_score_refresh, "schema_status", outdated)
    body = (await client.get("/api/admin/score-refresh", headers=admin_headers)).json()
    assert body["schema"]["ok"] is False and "alembic upgrade head" in body["schema"]["hint"]
    assert body["runs"] == [] and body["running"] is None


# ------------------------------------------------------------------ DB 버전 확인
async def test_schema_status_is_unknown_without_alembic_version(session_factory):
    status = await schema_status(session_factory.kw["bind"])
    assert (status.known, status.ok, status.current) == (False, True, None)  # create_all DB — 확인 불가, 막지 않음


def test_schema_status_compares_alembic_version_with_code_head(tmp_path, monkeypatch):
    db_path = tmp_path / "schema.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()

    def status_now():
        async def check():
            engine = create_async_engine(url)
            try:
                return await schema_status(engine)
            finally:
                await engine.dispose()
        return asyncio.run(check())

    try:
        cfg = Config()
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        command.upgrade(cfg, "head")
        assert status_now().ok and status_now().current == code_head()
        command.downgrade(cfg, "f3b8d1e6a9c4")
        status = status_now()
        assert status.known and not status.ok and status.current == "f3b8d1e6a9c4"
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT version_num FROM alembic_version").fetchone() == ("f3b8d1e6a9c4",)
    finally:
        get_settings.cache_clear()
