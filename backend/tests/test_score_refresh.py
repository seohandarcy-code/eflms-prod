"""점수 갱신 (Stage 21-1, 2026-11-19).

- 갱신은 기준일만 바꿔 점수 테이블(계산 결과 + score_snapshot)만 다시 쓴다 — 입력 테이블·최근 진단일은 그대로.
- 유형마다 한 트랜잭션(실패한 유형만 이전 점수 유지, 기록은 partial), 같은 날 두 번 돌려도 같다.
- 데이터 작업 잠금: 갱신·실제 반영 임포트·참고표 변경이 겹치지 않는다(검증만은 잠그지 않음), 만료된 잠금은 풀린다.
- 관리자 API(admin만, 진행 중이면 409), 요약 API의 점수 기준일·진단 데이터 반영일, 한국 시간 오늘, 마이그레이션 왕복.
"""
import sqlite3
from datetime import date, datetime, timedelta, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.auth.state import AdminAuthStore, get_auth_store
from app.core import clock
from app.core.config import BACKEND_DIR, get_settings
from app.db import recalculate
from app.db.models import DataJobLock, ScoreRefreshRun, ScoreSnapshot, SwitchgearCondition, UpsCondition
from app.equipment_types import ef4_switchgear, ef5_ups
from app.main import app
from app.services import job_lock
from app.services.import_service import import_file
from app.services.ingest import ingest_row
from app.services.score_refresh_service import refresh_scores

BASE = date(2026, 1, 1)
LATER = date(2031, 1, 1)


async def _seed(session_factory, n=3):
    """EF4·EF5 설비를 BASE 기준으로 넣는다. {equipment_id: (module, input_row)}."""
    seeded = {}
    async with session_factory() as session:
        for module in (ef4_switchgear, ef5_ups):
            for _ in range(n):
                row = module.generate_input_row()
                row["operation_start_time"] = date(2005, 3, 1)
                eq_id = await ingest_row(module.calculate(row, as_of=BASE), session)
                seeded[eq_id] = (module, row)
        await session.commit()
    return seeded


async def _snapshot(session_factory):
    async with session_factory() as session:
        return {r.equipment_id: (r.pof, r.total_score) for r in (await session.execute(select(ScoreSnapshot))).scalars()}


async def _diag_dates(session_factory):
    async with session_factory() as session:
        rows = [*(await session.execute(select(SwitchgearCondition.equipment_id, SwitchgearCondition.measured_at))).all(),
                *(await session.execute(select(UpsCondition.equipment_id, UpsCondition.measured_at))).all()]
        return dict(rows)


async def test_refresh_rewrites_scores_only_with_new_as_of(session_factory):
    seeded = await _seed(session_factory)
    diag_before = await _diag_dates(session_factory)
    assert set(diag_before.values()) == {BASE}

    result = await refresh_scores(session_factory, ["EF4", "EF5"], LATER, trigger="cli")

    assert result.status == "success" and result.equipment_count == 6
    stored = await _snapshot(session_factory)
    for eq_id, (module, row) in seeded.items():
        expected = module.calculate(row, as_of=LATER)
        assert stored[eq_id] == (expected["pof"], expected["total_score"])
    assert await _diag_dates(session_factory) == diag_before  # 최근 진단일은 그대로
    async with session_factory() as session:
        loaded = await ef4_switchgear.load_inputs(session, next(iter(seeded)))
        assert loaded[1] == LATER  # 다음 예측·재계산의 기준일은 갱신된 점수 기준일


async def test_refresh_is_idempotent_and_records_runs(session_factory):
    await _seed(session_factory)
    await refresh_scores(session_factory, ["EF4", "EF5"], LATER, trigger="schedule")
    first = await _snapshot(session_factory)
    await refresh_scores(session_factory, ["EF4", "EF5"], LATER, trigger="admin", requested_by="admin")
    assert await _snapshot(session_factory) == first
    async with session_factory() as session:
        runs = (await session.execute(select(ScoreRefreshRun).order_by(ScoreRefreshRun.run_id))).scalars().all()
        assert [(r.trigger, r.status, r.as_of, r.equipment_count) for r in runs] == [
            ("schedule", "success", LATER, 6), ("admin", "success", LATER, 6),
        ]
        assert all(r.finished_at is not None for r in runs)


async def test_failed_type_keeps_previous_scores_and_marks_partial(session_factory, monkeypatch):
    seeded = await _seed(session_factory)
    before = await _snapshot(session_factory)

    def boom(*args, **kwargs):
        raise RuntimeError("계산 실패 흉내")

    monkeypatch.setattr(ef5_ups, "calculate", boom)
    result = await refresh_scores(session_factory, ["EF4", "EF5"], LATER, trigger="cli")

    assert result.status == "partial"
    assert [(t.ef_code, t.count, bool(t.error)) for t in result.types] == [("EF4", 3, False), ("EF5", 0, True)]
    after = await _snapshot(session_factory)
    for eq_id, (module, _) in seeded.items():
        if module is ef5_ups:
            assert after[eq_id] == before[eq_id]
    async with session_factory() as session:
        run = (await session.execute(select(ScoreRefreshRun))).scalar_one()
        assert run.status == "partial" and "계산 실패 흉내" in run.summary


async def test_lock_blocks_refresh_and_real_import_but_not_check(session_factory, tmp_path):
    await _seed(session_factory, n=1)
    engine = session_factory.kw["bind"]
    token = await job_lock.acquire(engine, "다른 작업")

    busy = await refresh_scores(session_factory, ["EF4"], LATER, trigger="cli")
    assert busy.status == "busy" and "다른 작업" in busy.message

    names = [c["name"] for c in ef4_switchgear.INPUT_COLUMNS]
    row = ef4_switchgear.generate_input_row()
    path = tmp_path / "ef4.dat"
    fmt = lambda v: v.isoformat() if isinstance(v, date) else str(v)  # noqa: E731
    path.write_text("\t".join(names) + "\n" + "\t".join(fmt(row[n]) for n in names) + "\n", encoding="utf-8")
    async with session_factory() as session:
        checked = await import_file(str(path), "EF4", session, dry_run=True)
        assert checked.ok  # 검증만은 잠그지 않는다
        real = await import_file(str(path), "EF4", session)
        assert not real.ok and "진행 중" in real.file_errors[0]

    await job_lock.release(engine, token)
    assert (await refresh_scores(session_factory, ["EF4"], LATER, trigger="cli")).status == "success"
    async with session_factory() as session:
        assert (await session.execute(select(DataJobLock))).first() is None  # 끝나면 잠금이 풀린다


async def test_expired_lock_is_taken_over(session_factory):
    engine = session_factory.kw["bind"]
    await job_lock.acquire(engine, "죽은 작업", now=datetime.now() - timedelta(hours=2))
    assert await job_lock.current_holder(engine) is None
    token = await job_lock.acquire(engine, "새 작업")
    assert (await job_lock.current_holder(engine)).holder == "새 작업"
    await job_lock.release(engine, token)


async def test_recalculate_cli_as_of_option(session_factory, monkeypatch):
    seeded = await _seed(session_factory, n=1)
    monkeypatch.setattr(recalculate, "async_session_factory", session_factory)
    assert recalculate.parse_as_of("today") == clock.today_kst()
    assert recalculate.parse_as_of("2031-01-01") == LATER and recalculate.parse_as_of(None) is None
    assert await recalculate.run("all", LATER, "schedule") is True
    stored = await _snapshot(session_factory)
    for eq_id, (module, row) in seeded.items():
        assert stored[eq_id][0] == module.calculate(row, as_of=LATER)["pof"]


def test_today_kst_rolls_over_at_15_utc():
    assert datetime(2026, 11, 19, 14, 59, tzinfo=timezone.utc).astimezone(clock.KST).date() == date(2026, 11, 19)
    assert datetime(2026, 11, 19, 15, 0, tzinfo=timezone.utc).astimezone(clock.KST).date() == date(2026, 11, 20)
    assert clock.now_kst().utcoffset() == timedelta(hours=9)


# ------------------------------------------------------------------ API
@pytest.fixture
def admin_headers(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "local")
    get_settings.cache_clear()
    store = AdminAuthStore()
    app.dependency_overrides[get_auth_store] = lambda: store
    token, _ = store.issue_session("admin")
    yield {"Authorization": f"Bearer {token}"}, store
    app.dependency_overrides.pop(get_auth_store, None)
    get_settings.cache_clear()


async def test_admin_refresh_api(client, admin_headers, session_factory):
    headers, store = admin_headers
    user_token, _ = store.issue_session("user")
    assert (await client.post("/api/admin/score-refresh", headers={"Authorization": f"Bearer {user_token}"})).status_code == 403

    resp = await client.post("/api/admin/score-refresh", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success" and body["as_of"] == clock.today_kst().isoformat()
    assert body["equipment_count"] == 3  # client 픽스처의 EF1 3대

    status = (await client.get("/api/admin/score-refresh", headers=headers)).json()
    assert status["running"] is None
    assert status["runs"][0]["run_id"] == body["run_id"] and status["runs"][0]["trigger"] == "admin"

    token = await job_lock.acquire(session_factory.kw["bind"], "임포트 EF1")
    try:
        busy = await client.post("/api/admin/score-refresh", headers=headers)
        assert busy.status_code == 409 and "임포트 EF1" in busy.json()["detail"]
        assert (await client.get("/api/admin/score-refresh", headers=headers)).json()["running"]["holder"] == "임포트 EF1"
    finally:
        await job_lock.release(session_factory.kw["bind"], token)


async def test_summary_separates_score_date_and_data_date(client, session_factory):
    await _seed(session_factory, n=2)
    await refresh_scores(session_factory, ["EF4", "EF5"], LATER, trigger="cli")
    summary = (await client.get("/api/summary", params={"ef_code": "EF4"})).json()
    assert summary["score_as_of"] == summary["score_as_of_latest"] == LATER.isoformat()
    assert summary["data_updated_on"] == BASE.isoformat()  # 갱신으로 바뀌지 않는다
    everything = (await client.get("/api/summary")).json()
    assert everything["score_as_of_latest"] == LATER.isoformat()
    assert everything["score_as_of"] == clock.today_kst().isoformat()  # client 픽스처 EF1은 오늘 기준 — 가장 이른 날


# ------------------------------------------------------------------ 마이그레이션
def test_refresh_tables_migration_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "refresh.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    def tables():
        with sqlite3.connect(db_path) as conn:
            return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    try:
        cfg = Config()
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        command.upgrade(cfg, "head")
        assert {"score_refresh_run", "data_job_lock"} <= tables()
        command.downgrade(cfg, "f3b8d1e6a9c4")
        assert not {"score_refresh_run", "data_job_lock"} & tables()
        command.upgrade(cfg, "head")
        assert {"score_refresh_run", "data_job_lock"} <= tables()
    finally:
        get_settings.cache_clear()


# ------------------------------------------------------------------ Stage 21-1c: 요약 API의 마지막 갱신 시각
async def test_summary_reports_last_refresh_time_and_trigger(client, session_factory, monkeypatch):
    from app.services import score_refresh_service

    first = (await client.get("/api/summary")).json()
    assert first["score_refreshed_at"] is None and first["score_refresh_trigger"] is None
    assert first["score_refresh_auto"] is True

    stamp = datetime(2026, 11, 19, 0, 5, 30)  # 한국 시간으로 기록된다(now_kst_naive)
    monkeypatch.setattr(score_refresh_service, "now_kst_naive", lambda: stamp)
    await refresh_scores(session_factory, ["EF1"], clock.today_kst(), trigger="daily", requested_by="server")
    body = (await client.get("/api/summary")).json()
    assert body["score_refreshed_at"] == "2026-11-19T00:05:30" and body["score_refresh_trigger"] == "daily"

    def boom(*args, **kwargs):
        raise RuntimeError("실패 흉내")

    from app.equipment_types import ef1_transformer

    monkeypatch.setattr(ef1_transformer, "calculate", boom)
    monkeypatch.setattr(score_refresh_service, "now_kst_naive", lambda: stamp + timedelta(hours=1))
    failed = await refresh_scores(session_factory, ["EF1"], clock.today_kst(), trigger="admin", requested_by="admin")
    assert failed.status == "failed"
    assert (await client.get("/api/summary")).json()["score_refresh_trigger"] == "daily"  # 전부 실패한 갱신은 반영 안 함


def test_now_kst_naive_is_kst_without_tzinfo():
    value = clock.now_kst_naive()
    assert value.tzinfo is None
    assert abs((clock.now_kst().replace(tzinfo=None) - value).total_seconds()) < 5
