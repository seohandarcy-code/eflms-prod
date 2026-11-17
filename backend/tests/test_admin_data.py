"""Stage 16-2/16-3/16-6 — 관리자 웹 데이터 입력(붙여넣기)·양식·내보내기 API."""
from pathlib import Path

import pytest

from app.auth.state import AdminAuthStore, get_auth_store
from app.core.config import get_settings
from app.db import seed
from app.equipment_types.registry import registered_codes
from app.main import app
from app.services.data_admin_service import _format_cell

SAMPLES = Path(__file__).resolve().parent.parent / "sample_data"


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


async def _upload(client, headers, content, ef_code: str, *, table="", replace=False, check=True):
    """붙여넣기 — 바이트(파일 내용)면 엑셀에서 복사한 것처럼 텍스트로 바꿔 보낸다."""
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    return await client.post(
        "/api/admin/data/import",
        headers=headers,
        json={"ef_code": ef_code, "table": table, "replace": replace, "check": check, "text": text},
    )


async def _seed(session_factory, codes, rows=8):
    async with session_factory() as session:
        for code in codes:
            await seed.seed_type(session, code, rows=rows, reset=False)
        await session.commit()


async def _scores(client, ef_code):
    items = (await client.get("/api/equipment", params={"ef_code": ef_code})).json()
    return sorted((e["factory_code"], e["equipment_name"], e["total_score"], e["pof"], e["cof"], e["dof"]) for e in items)


# --- 권한 ---


async def test_data_api_requires_admin(client, admin_headers):
    _, store = admin_headers
    assert (await client.get("/api/admin/data/targets")).status_code == 401
    user_token, _ = store.issue_session("user")
    resp = await client.get("/api/admin/data/targets", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403
    resp = await _upload(client, {"Authorization": f"Bearer {user_token}"}, b"x", "EF1")
    assert resp.status_code == 403
    resp = await client.get("/api/admin/data/export", params={"ef_code": "EF1"}, headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403


async def test_targets_list_types_and_reference_tables(client, admin_headers, session_factory):
    headers, _ = admin_headers
    await _seed(session_factory, ["EF7"], rows=4)
    targets = {t["ef_code"]: t for t in (await client.get("/api/admin/data/targets", headers=headers)).json()}
    assert list(targets) == registered_codes()
    assert targets["EF1"]["equipment_count"] == 3  # conftest가 넣은 3건
    assert targets["EF1"]["reference_tables"] == []
    refs = {r["name"]: r for r in targets["EF7"]["reference_tables"]}
    assert refs["discharge_history"]["rows"] == 40
    assert refs["temp_decay_coef"]["label"] and refs["temp_decay_coef"]["rows"] == 20


# --- 설비 데이터 입력 ---


async def test_check_then_apply_equipment_file(client, admin_headers):
    headers, _ = admin_headers
    content = (SAMPLES / "ef2" / "sample_valid.dat").read_bytes()

    resp = await _upload(client, headers, content, "EF2")
    body = resp.json()
    assert resp.status_code == 200 and body["ok"] and body["dry_run"] and body["kind"] == "equipment"
    assert body["file_path"] == "붙여넣기"
    assert [a["action"] for a in body["row_actions"]] == ["추가"] * body["total_rows"]
    total = body["total_rows"]
    assert total > 0
    assert (await client.get("/api/equipment", params={"ef_code": "EF2"})).json() == []  # 검증만 — 반영 안 됨

    body = (await _upload(client, headers, content, "EF2", check=False)).json()
    assert body["ok"] and not body["dry_run"] and body["imported_rows"] == total
    assert body["row_actions"] == []  # 미리보기는 검증 때만
    assert len((await client.get("/api/equipment", params={"ef_code": "EF2"})).json()) == total

    # 같은 내용을 다시 검증하면 전부 갱신, 교체로 검증하면 전부 추가
    body = (await _upload(client, headers, content, "EF2")).json()
    assert {a["action"] for a in body["row_actions"]} == {"갱신"}
    body = (await _upload(client, headers, content, "EF2", replace=True)).json()
    assert {a["action"] for a in body["row_actions"]} == {"추가"}


async def test_error_file_is_rejected_whole(client, admin_headers):
    headers, _ = admin_headers
    content = (SAMPLES / "ef7" / "sample_with_errors.dat").read_bytes()
    body = (await _upload(client, headers, content, "EF7", check=False)).json()
    assert not body["ok"] and body["row_errors"]
    assert body["imported_rows"] == 0 and body["row_actions"] == []
    assert (await client.get("/api/equipment", params={"ef_code": "EF7"})).json() == []
    # 검증만 해도 오류 행·칸을 알려준다(화면이 미리보기에서 빨갛게 표시)
    body = (await _upload(client, headers, content, "EF7")).json()
    assert not body["ok"] and all({"row_number", "column", "raw_value", "reason"} <= e.keys() for e in body["row_errors"])


async def test_replace_check_reports_existing_rows(client, admin_headers):
    headers, _ = admin_headers
    content = (SAMPLES / "ef1" / "sample_valid.dat").read_bytes()
    body = (await _upload(client, headers, content, "EF1", replace=True)).json()
    assert body["ok"] and body["replace"] and body["existing_rows"] == 3


async def test_bad_requests(client, admin_headers):
    headers, _ = admin_headers
    assert (await _upload(client, headers, b"", "EF1")).status_code == 400
    assert (await _upload(client, headers, "  \n\t\n", "EF1")).status_code == 400
    resp = await _upload(client, headers, b"a\tb\n", "EF99")
    assert resp.status_code == 400 and "EF99" in resp.json()["detail"]
    resp = await _upload(client, headers, b"a\tb\n", "EF1", table="discharge_history")
    assert resp.status_code == 400 and "참고표" in resp.json()["detail"]
    big = "x" * (5 * 1024 * 1024 + 1)
    assert (await _upload(client, headers, big, "EF1")).status_code == 413


# --- 참고표 입력 ---


async def test_reference_upload_recalculates_battery_scores(client, admin_headers, session_factory):
    headers, _ = admin_headers
    await _seed(session_factory, ["EF7"], rows=6)
    before = await _scores(client, "EF7")

    content = (SAMPLES / "ef7" / "reference_temp_decay_coef.dat").read_bytes()
    body = (await _upload(client, headers, content, "EF7", table="temp_decay_coef")).json()
    assert body["ok"] and body["kind"] == "reference" and body["dry_run"] and body["table_rows_before"] == 20
    assert {a["action"] for a in body["row_actions"]} == {"갱신"}  # 목업 1~20년과 같은 year
    body = (await _upload(client, headers, "year\tgamma_y\n1\t3.0\n21\t0.5\n", "EF7", table="temp_decay_coef")).json()
    assert [(a["action"], a["key"]) for a in body["row_actions"]] == [("갱신", ["1"]), ("추가", ["21"])]

    # 온도감소계수를 1행만 남기도록 교체 → 6건 재계산, 점수가 바뀐다
    one_row = b"year\tgamma_y\n1\t9.9\n"
    body = (await _upload(client, headers, one_row, "EF7", table="temp_decay_coef", replace=True, check=False)).json()
    assert body["ok"] and body["deleted_rows"] == 20 and body["table_rows_after"] == 1
    assert body["recalculated"] == 6
    assert await _scores(client, "EF7") != before

    bad = (SAMPLES / "ef7" / "reference_discharge_history_with_errors.dat").read_bytes()
    body = (await _upload(client, headers, bad, "EF7", table="discharge_history", check=False)).json()
    assert not body["ok"] and body["row_errors"][0]["row_number"] == 4


# --- 내보내기 ---


def test_format_cell_rules():
    from datetime import date, datetime

    assert _format_cell(None) == "N/A"
    assert _format_cell(float("nan")) == "N/A"
    assert _format_cell(date(2020, 6, 1)) == "2020-06-01"
    assert _format_cell(datetime(2020, 6, 1, 13, 5)) == "2020-06-01"
    assert _format_cell(0.1) == "0.1"
    assert _format_cell(154000) == "154000"
    assert _format_cell("a\tb\nc") == "a b c"


async def test_export_round_trips_every_type(client, admin_headers, session_factory):
    """내보낸 dat를 교체로 다시 넣으면 모든 유형에서 점수가 그대로다(백업·이관용 형식 확인)."""
    headers, _ = admin_headers
    codes = [c for c in registered_codes() if c != "EF1"]
    await _seed(session_factory, codes, rows=8)

    for code in registered_codes():
        before = await _scores(client, code)
        resp = await client.get("/api/admin/data/export", params={"ef_code": code}, headers=headers)
        assert resp.status_code == 200, code
        assert resp.content.startswith("﻿".encode("utf-8"))
        assert resp.headers["x-row-count"] == str(len(before))
        assert f'filename="{code}_equipment_' in resp.headers["content-disposition"]

        body = (await _upload(client, headers, resp.content, code, replace=True, check=False)).json()
        assert body["ok"], (code, body["file_errors"], body["row_errors"][:3])
        assert body["imported_rows"] == len(before) and not body["unknown_columns"]
        assert await _scores(client, code) == before, code


async def test_export_keeps_extra_columns(client, admin_headers):
    headers, _ = admin_headers
    content = (SAMPLES / "ef1" / "sample_with_extra_columns.dat").read_bytes()
    first = (await _upload(client, headers, content, "EF1", replace=True, check=False)).json()
    assert first["ok"] and first["unknown_columns"]

    resp = await client.get("/api/admin/data/export", params={"ef_code": "EF1"}, headers=headers)
    header = resp.content.decode("utf-8-sig").splitlines()[0].split("\t")
    for col in first["unknown_columns"]:
        assert col in header

    again = (await _upload(client, headers, resp.content, "EF1", replace=True, check=True)).json()
    assert again["ok"] and sorted(again["unknown_columns"]) == sorted(first["unknown_columns"])


async def test_export_reference_round_trip(client, admin_headers, session_factory):
    headers, _ = admin_headers
    await _seed(session_factory, ["EF7"], rows=3)
    for table, rows in (("discharge_history", 40), ("temp_decay_coef", 20)):
        resp = await client.get("/api/admin/data/export", params={"ef_code": "EF7", "table": table}, headers=headers)
        assert resp.status_code == 200 and resp.headers["x-row-count"] == str(rows)
        body = (await _upload(client, headers, resp.content, "EF7", table=table, replace=True, check=False)).json()
        assert body["ok"] and body["table_rows_after"] == rows and body["inserted_rows"] == rows

    resp = await client.get("/api/admin/data/export", params={"ef_code": "EF7", "table": "nope"}, headers=headers)
    assert resp.status_code == 404
    resp = await client.get("/api/admin/data/export", params={"ef_code": "EF99"}, headers=headers)
    assert resp.status_code == 404


# --- 붙여넣기 형식·양식 ---


async def test_excel_style_paste_with_crlf_and_quotes(client, admin_headers):
    """엑셀에서 복사하면 줄바꿈이 CRLF이고, 특수문자가 있는 칸은 따옴표로 감싸진다."""
    headers, _ = admin_headers
    text = (SAMPLES / "ef7" / "reference_temp_decay_coef.dat").read_text(encoding="utf-8-sig")
    lines = text.strip().split("\n")
    pasted = "\r\n".join(['"year"\t"gamma_y"', *lines[1:]]) + "\r\n\r\n"
    body = (await _upload(client, headers, pasted, "EF7", table="temp_decay_coef")).json()
    assert body["ok"], body["row_errors"][:3]
    assert body["total_rows"] == 20 and len(body["row_actions"]) == 20


async def test_template_lists_header_and_rules(client, admin_headers):
    headers, _ = admin_headers
    body = (await client.get("/api/admin/data/template", params={"ef_code": "EF7"}, headers=headers)).json()
    from app.equipment_types import ef7_battery

    assert body["header"].split("\t") == [c["name"] for c in ef7_battery.INPUT_COLUMNS]
    assert body["key"] == ["factory_code", "eqp_id"]
    cols = {c["name"]: c for c in body["columns"]}
    assert cols["con_rank"]["choices"] == ["단독", "공용"] and cols["con_rank"]["na_allowed"] is True
    assert cols["factory_code"]["na_allowed"] is False and cols["eqp_id"]["na_allowed"] is False
    assert cols["bat_room_humid"]["min"] == 0 and cols["bat_room_humid"]["max"] == 100
    assert "generator" not in cols["factory_code"]

    ref = (await client.get("/api/admin/data/template", params={"ef_code": "EF7", "table": "temp_decay_coef"}, headers=headers)).json()
    assert ref["header"] == "year\tgamma_y" and ref["key"] == ["year"]
    assert {c["name"]: c for c in ref["columns"]}["gamma_y"]["gt"] == 0

    assert (await client.get("/api/admin/data/template", params={"ef_code": "EF99"}, headers=headers)).status_code == 404
    resp = await client.get("/api/admin/data/template", params={"ef_code": "EF1", "table": "x"}, headers=headers)
    assert resp.status_code == 404
