"""점수 이력(Stage 21-3)·입력 변경 이력과 되돌리기(Stage 21-4), 2026-11-19.

- 점수를 쓸 때마다 설비(유형·사업장·이름)·점수 기준일별 이력 1행(같은 날은 덮어씀), 교체로 equipment_id가 바뀌어도 이어진다.
- 임포트·행 편집·교체·참고표 넣기/리셋이 바뀌기 전후 값과 함께 기록된다. 값이 같은 행은 반영하지 않는다(반영일 그대로).
- 되돌리기: 이전 값·이전 반영일로 복원, 점수는 오늘 기준. 그 뒤 같은 데이터를 바꾼 변경이 있으면 막는다. 되돌리기도 기록된다.
"""
import asyncio
import json
import sqlite3
from datetime import date, timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from app.auth.state import AdminAuthStore, get_auth_store
from app.core.clock import today_kst
from app.core.config import BACKEND_DIR, get_settings
from app.db.models import (
    BatteryDischargeHistory,
    DataChange,
    DataChangeRow,
    Equipment,
    ScoreHistory,
    SwitchgearCondition,
)
from app.equipment_types import ef4_switchgear, ef7_battery
from app.main import app
from app.services import change_service
from app.services.import_service import import_file
from app.services.ingest import ingest_row
from app.services.reference_data import ensure_mock_reference
from app.services.reference_service import import_reference_file, reset_reference
from app.services.score_refresh_service import refresh_scores

OLD = date(2026, 10, 1)


def _fmt(v):
    return "N/A" if v is None else (v.isoformat() if isinstance(v, date) else str(v))


def _write(tmp_path, module, rows, name="data.dat"):
    names = [c["name"] for c in module.INPUT_COLUMNS]
    lines = ["\t".join(names)] + ["\t".join(_fmt(r[n]) for n in names) for r in rows]
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


async def _seed_ef4(session_factory, n=2, as_of=OLD):
    rows = []
    async with session_factory() as session:
        for _ in range(n):
            row = ef4_switchgear.generate_input_row()
            await ingest_row(ef4_switchgear.calculate(row, as_of=as_of), session)
            rows.append(row)
        await session.commit()
    return rows


async def _measured(session_factory, name):
    async with session_factory() as session:
        eq = (await session.execute(select(Equipment).where(Equipment.equipment_name == name))).scalar_one()
        cond = await session.get(SwitchgearCondition, eq.equipment_id)
        return cond.measured_at, cond


async def _changes(session_factory):
    async with session_factory() as session:
        return (await session.execute(select(DataChange).order_by(DataChange.change_id))).scalars().all()


# ------------------------------------------------------------------ 21-3 점수 이력
async def test_score_history_one_row_per_day_and_survives_replace(session_factory, tmp_path):
    rows = await _seed_ef4(session_factory, n=1)
    name = rows[0][ef4_switchgear.NAME_FIELD]
    async with session_factory() as session:
        await ingest_row(ef4_switchgear.calculate(rows[0], as_of=OLD), session)  # 같은 날 다시 계산 → 덮어씀
        await session.commit()
    await refresh_scores(session_factory, ["EF4"], OLD + timedelta(days=400), trigger="cli")
    async with session_factory() as session:
        dates = (await session.execute(select(ScoreHistory.as_of).where(ScoreHistory.equipment_name == name))).scalars().all()
        assert sorted(dates) == [OLD, OLD + timedelta(days=400)]
        result = await import_file(_write(tmp_path, ef4_switchgear, rows), "EF4", session, replace=True)
        assert result.ok
        eq_id = (await session.execute(select(Equipment.equipment_id).where(Equipment.equipment_name == name))).scalar_one()
    from httpx import ASGITransport, AsyncClient
    from app.db.session import get_session

    async def _override():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = _override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            history = (await client.get(f"/api/equipment/{eq_id}/history")).json()
    finally:
        app.dependency_overrides.pop(get_session, None)
    expected = sorted([OLD, OLD + timedelta(days=400), today_kst()])  # 날짜순 — 교체 후에도 같은 설비로 이어진다
    assert [h["as_of"] for h in history] == [d.isoformat() for d in expected]
    assert all(h["status"] in ("normal", "review", "replace") for h in history)


# ------------------------------------------------------------------ 21-4 변경 이력·되돌리기
async def test_unchanged_rows_are_not_applied_and_keep_their_date(session_factory, tmp_path):
    rows = await _seed_ef4(session_factory, n=2)
    name = rows[0][ef4_switchgear.NAME_FIELD]
    async with session_factory() as session:
        checked = await import_file(_write(tmp_path, ef4_switchgear, rows), "EF4", session, dry_run=True)
        assert checked.unchanged_rows == 2
        result = await import_file(_write(tmp_path, ef4_switchgear, rows), "EF4", session)
    assert result.ok and result.unchanged_rows == 2 and result.imported_rows == 0 and result.change_id is None
    assert (await _measured(session_factory, name))[0] == OLD  # 진단 데이터 반영일 그대로
    assert await _changes(session_factory) == []


async def test_edit_is_recorded_and_undo_restores_values_and_date(session_factory, tmp_path):
    rows = await _seed_ef4(session_factory, n=2)
    # 매일 점수 갱신으로 점수 기준일(오늘)과 진단 데이터 반영일(OLD)이 달라진 상태 — 되돌리면 반영일은 OLD로 돌아와야 한다
    await refresh_scores(session_factory, ["EF4"], today_kst(), trigger="daily")
    name = rows[0][ef4_switchgear.NAME_FIELD]
    edited = dict(rows[0], load_chk=0.9)  # 부하율만 바꿈
    async with session_factory() as session:
        result = await import_file(_write(tmp_path, ef4_switchgear, [edited, rows[1]]), "EF4", session,
                                   actor="admin", kind="row_edit", source_name="행 편집")
    assert result.ok and result.imported_rows == 1 and result.unchanged_rows == 1
    measured, cond = await _measured(session_factory, name)
    assert measured == today_kst() and cond.load_chk == 0.9

    async with session_factory() as session:
        detail = await change_service.change_detail(session, result.change_id)
    assert (detail["kind"], detail["actor"], detail["row_count"], detail["unchanged_count"]) == ("row_edit", "admin", 1, 1)
    row = detail["rows"][0]
    assert row["action"] == "update" and row["before"]["load_chk"] == rows[0]["load_chk"] and row["after"]["load_chk"] == 0.9
    assert row["before"]["_as_of"] == today_kst().isoformat() and detail["undo_check"]["possible"]
    assert row["before"]["_dates"]["switchgear_condition"]["measured_at"] == OLD.isoformat()

    async with session_factory() as session:
        undo_id = await change_service.undo_change(session, result.change_id, actor="admin")
        await session.commit()
    measured, cond = await _measured(session_factory, name)
    assert measured == OLD and cond.load_chk == rows[0]["load_chk"]  # 값과 반영일 모두 복원
    changes = await _changes(session_factory)
    assert [(c.change_id, c.kind, c.status) for c in changes] == [(result.change_id, "row_edit", "undone"), (undo_id, "undo", "applied")]
    assert changes[1].undo_of == result.change_id
    async with session_factory() as session:
        assert not (await change_service.undo_blockers(session, changes[0]))["possible"]  # 이미 되돌림
        assert not (await change_service.undo_blockers(session, changes[1]))["possible"]  # 되돌리기는 다시 못 되돌림


async def test_later_change_on_same_equipment_blocks_undo(session_factory, tmp_path):
    rows = await _seed_ef4(session_factory, n=1)
    async with session_factory() as session:
        first = await import_file(_write(tmp_path, ef4_switchgear, [dict(rows[0], load_chk=0.7)]), "EF4", session)
        second = await import_file(_write(tmp_path, ef4_switchgear, [dict(rows[0], load_chk=0.9)]), "EF4", session)
        c1 = await session.get(DataChange, first.change_id)
        blocked = await change_service.undo_blockers(session, c1)
        assert not blocked["possible"] and f"#{second.change_id}" in blocked["reason"]
        with pytest.raises(change_service.UndoError):
            await change_service.undo_change(session, first.change_id, actor="admin")
        await change_service.undo_change(session, second.change_id, actor="admin")
        await session.commit()
        await change_service.undo_change(session, first.change_id, actor="admin")
        await session.commit()
    _, cond = await _measured(session_factory, rows[0][ef4_switchgear.NAME_FIELD])
    assert cond.load_chk == rows[0]["load_chk"]


async def test_replace_is_undone_back_to_previous_equipment(session_factory, tmp_path):
    old_rows = await _seed_ef4(session_factory, n=3)
    new_rows = [ef4_switchgear.generate_input_row() for _ in range(2)]
    async with session_factory() as session:
        result = await import_file(_write(tmp_path, ef4_switchgear, new_rows), "EF4", session, replace=True)
        assert result.ok
        detail = await change_service.change_detail(session, result.change_id)
        assert sorted(r["action"] for r in detail["rows"]) == ["delete"] * 3 + ["insert"] * 2
        await change_service.undo_change(session, result.change_id, actor="admin")
        await session.commit()
        names = sorted((await session.execute(select(Equipment.equipment_name).where(Equipment.ef_code == "EF4"))).scalars())
    assert names == sorted(r[ef4_switchgear.NAME_FIELD] for r in old_rows)
    assert (await _measured(session_factory, old_rows[0][ef4_switchgear.NAME_FIELD]))[0] == OLD


async def test_reference_import_and_reset_are_recorded_and_undoable(session_factory, tmp_path):
    async with session_factory() as session:
        await ensure_mock_reference(session, ef7_battery)
        await session.commit()
        before = (await session.execute(select(func.count()).select_from(BatteryDischargeHistory))).scalar_one()
        spec = ef7_battery.REFERENCE_TABLES["discharge_history"]
        first = (await session.execute(select(BatteryDischargeHistory))).scalars().first()
        cols = [c["name"] for c in spec["columns"]]
        changed = {c: getattr(first, c) for c in cols} | {"disch_index": 9.5}
        added = dict(changed, disch_date=date(2026, 11, 1), disch_index=1.25)
        path = tmp_path / "ref.dat"
        path.write_text("\t".join(cols) + "\n" + "\n".join("\t".join(_fmt(r[c]) for c in cols) for r in (changed, added)) + "\n",
                        encoding="utf-8")
        result = await import_reference_file(str(path), "EF7", "discharge_history", session, actor="admin")
        assert result.ok and (result.updated_rows, result.inserted_rows) == (1, 1) and result.change_id
        await change_service.undo_change(session, result.change_id, actor="admin")
        await session.commit()
        restored = await session.get(BatteryDischargeHistory, first.id) if hasattr(first, "id") else None
        assert (await session.execute(select(func.count()).select_from(BatteryDischargeHistory))).scalar_one() == before
        if restored is not None:
            assert restored.disch_index == getattr(first, "disch_index")

        reset = await reset_reference(session, "EF7", "discharge_history", actor="admin")
        assert reset.ok and reset.change_id
        assert (await session.execute(select(func.count()).select_from(BatteryDischargeHistory))).scalar_one() == 0
        await change_service.undo_change(session, reset.change_id, actor="admin")
        await session.commit()
        assert (await session.execute(select(func.count()).select_from(BatteryDischargeHistory))).scalar_one() == before


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


async def test_admin_change_api_and_row_edit_preview(client, admin_headers, session_factory):
    headers, store = admin_headers
    rows = await _seed_ef4(session_factory, n=1)
    names = [c["name"] for c in ef4_switchgear.INPUT_COLUMNS]
    text = "\t".join(names) + "\n" + "\t".join(_fmt(rows[0][n]) for n in names) + "\n"
    payload = {"ef_code": "EF4", "table": "", "replace": False, "text": text, "source": "row_edit"}

    preview = (await client.post("/api/admin/data/import", headers=headers, json=payload | {"check": True})).json()
    assert preview["ok"] and [a["action"] for a in preview["row_actions"]] == ["변경 없음"]

    edited = text.replace("\t" + _fmt(rows[0]["load_chk"]) + "\t", "\t0.95\t", 1)
    applied = (await client.post("/api/admin/data/import", headers=headers, json=payload | {"text": edited, "check": False})).json()
    assert applied["ok"] and applied["change_id"]

    user_token, _ = store.issue_session("user")
    assert (await client.get("/api/admin/changes", headers={"Authorization": f"Bearer {user_token}"})).status_code == 403
    listed = (await client.get("/api/admin/changes", headers=headers)).json()
    assert listed[0]["change_id"] == applied["change_id"] and listed[0]["kind_label"] == "행 편집"
    detail = (await client.get(f"/api/admin/changes/{applied['change_id']}", headers=headers)).json()
    assert detail["rows"][0]["after"]["load_chk"] == 0.95

    check = (await client.post(f"/api/admin/changes/{applied['change_id']}/undo", headers=headers, json={"check": True})).json()
    assert check["possible"] is True
    done = await client.post(f"/api/admin/changes/{applied['change_id']}/undo", headers=headers, json={"check": False})
    assert done.status_code == 200 and done.json()["undo_change_id"]
    again = await client.post(f"/api/admin/changes/{applied['change_id']}/undo", headers=headers, json={"check": False})
    assert again.status_code == 409 and "이미 되돌린" in again.json()["detail"]
    assert (await client.get("/api/admin/changes/99999", headers=headers)).status_code == 404


# ------------------------------------------------------------------ 마이그레이션
def test_history_migrations_round_trip_and_backfill(tmp_path, monkeypatch):
    db_path = tmp_path / "hist.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    def tables():
        with sqlite3.connect(db_path) as conn:
            return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    try:
        cfg = Config()
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        command.upgrade(cfg, "a6c2e9f4d1b8")
        with sqlite3.connect(db_path) as conn:  # 점수가 저장된 설비 1대(케이블)
            conn.execute("INSERT INTO equipment_type (ef_code, name) VALUES ('EF3', '케이블')")
            conn.execute("INSERT INTO equipment (equipment_id, factory_code, ef_code, equipment_name, voltage, operation_start_time)"
                         " VALUES (1, 'H1', 'EF3', 'cab1', 154000, '2010-01-01')")
            conn.execute("INSERT INTO score_snapshot (equipment_id, pof_minus, pof, cof_minus, cof, dof_minus, dof, total_score)"
                         " VALUES (1, -45, 55, -10, 90, -10, 90, 72.5)")
            cols = [r[1] for r in conn.execute("PRAGMA table_info(cable_score_detail)")]
            values = {c: 0.0 for c in cols} | {"equipment_id": 1, "computed_at": "2026-11-01 00:00:00", "today": "2026-11-01",
                                                "operation_year": 16.8}
            conn.execute(f"INSERT INTO cable_score_detail ({', '.join(values)}) VALUES ({', '.join('?' * len(values))})",
                         list(values.values()))
        command.upgrade(cfg, "head")
        assert {"score_history", "data_change", "data_change_row"} <= tables()
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT ef_code, equipment_name, as_of, pof, status FROM score_history").fetchall() == [
                ("EF3", "cab1", "2026-11-01", 55.0, "normal")  # COF·DOF > 60 → 완화 기준(> 50 정상)
            ]
        command.downgrade(cfg, "a6c2e9f4d1b8")
        assert not {"score_history", "data_change", "data_change_row"} & tables()
        command.upgrade(cfg, "head")
    finally:
        get_settings.cache_clear()
