"""Stage 16-2/16-3/16-6 — 관리자 웹 데이터 입력(붙여넣기)·양식·내보내기 API."""
from pathlib import Path

import pytest

from app.auth.state import AdminAuthStore, get_auth_store
from app.core.config import get_settings
from app.db import seed
from app.equipment_types.registry import registered_codes
from app.main import app
from app.services.data_admin_service import _format_cell
from app.services.import_service import _parse_lines

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

    # 같은 내용을 다시 검증하면 전부 "변경 없음"(값이 같아 반영 안 함, Stage 21-4), 교체로 검증하면 전부 추가
    body = (await _upload(client, headers, content, "EF2")).json()
    assert {a["action"] for a in body["row_actions"]} == {"변경 없음"} and body["unchanged_rows"] == total
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
    assert {a["action"] for a in body["row_actions"]} == {"변경 없음"}  # 목업 1~20년과 같은 값(Stage 21-4)
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
    label_row, header = (line.split("\t") for line in resp.content.decode("utf-8-sig").splitlines()[:2])
    for col in first["unknown_columns"]:
        assert col in header
        assert label_row[header.index(col)] == col  # 한글명이 없는 칸은 영문명 그대로(Stage 22-9)

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


async def test_export_first_row_is_korean_labels(client, admin_headers, session_factory):
    """내려받기 1행은 한글 항목명, 2행은 영문 헤더(Stage 22-9) — 설비 데이터와 참고표 모두."""
    from app.equipment_types import ef3_cable, ef7_battery

    headers, _ = admin_headers
    await _seed(session_factory, ["EF3", "EF7"], rows=2)
    cases = [
        ({"ef_code": "EF3"}, ef3_cable.INPUT_COLUMNS),
        ({"ef_code": "EF7", "table": "temp_decay_coef"}, ef7_battery.REFERENCE_TABLES["temp_decay_coef"]["columns"]),
    ]
    for params, columns in cases:
        dat = (await client.get("/api/admin/data/export", params=params, headers=headers)).content.decode("utf-8-sig")
        label_row, header = (line.split("\t") for line in dat.splitlines()[:2])
        assert header == [c["name"] for c in columns], params
        assert label_row == [c.get("label") or c["name"] for c in columns], params
    assert label_row == ["사용 년차", "온도감소계수"]


def test_parse_lines_skips_label_row_only_when_header_follows():
    known = ["year", "gamma_y"]
    # 한글 항목명 행은 건너뛰고, 줄 번호는 실제 파일 기준
    header, rows = _parse_lines("사용 년차\t온도감소계수\n\nyear\tgamma_y\n1\t0.5\n", known)
    assert header == ["year", "gamma_y"] and rows == [(4, ["1", "0.5"])]
    # 한글명이 없어 영문명이 섞인 항목명 행도 건너뛴다(EF1 dga_h2·EF4~7 eqp_id 등)
    header, rows = _parse_lines("year\t온도감소계수\nyear\tgamma_y\n1\t0.5\n", known)
    assert header == ["year", "gamma_y"] and rows == [(3, ["1", "0.5"])]
    # 영문 헤더만 있는 기존 파일은 그대로
    header, rows = _parse_lines("year\tgamma_y\n1\t0.5\n", known)
    assert header == ["year", "gamma_y"] and rows == [(2, ["1", "0.5"])]
    # 둘째 줄도 헤더가 아니면 첫 줄을 헤더로 둔다(→ 필수 컬럼 없음으로 거부됨)
    header, _ = _parse_lines("연차\t계수\n1\t0.5\n", known)
    assert header == ["연차", "계수"]
    # known_names를 안 주면 예전처럼 첫 줄이 헤더
    header, _ = _parse_lines("사용 년차\t온도감소계수\nyear\tgamma_y\n")
    assert header == ["사용 년차", "온도감소계수"]


async def test_upload_and_paste_accept_korean_label_row(client, admin_headers):
    """엑셀에서 한글 항목명 행까지 복사해 붙여넣어도 받는다 — 오류 줄 번호는 실제 줄."""
    headers, _ = admin_headers
    text = (SAMPLES / "ef7" / "reference_temp_decay_coef.dat").read_text(encoding="utf-8-sig")
    body = (await _upload(client, headers, "사용 년차\t온도감소계수\n" + text, "EF7", table="temp_decay_coef")).json()
    assert body["ok"], body["row_errors"][:3]
    assert body["total_rows"] == 20 and len(body["row_actions"]) == 20
    assert body["row_actions"][0]["row_number"] == 3

    bad = text.strip().split("\n")
    bad[1] = "1\t-1"
    body = (await _upload(client, headers, "사용 년차\t온도감소계수\n" + "\n".join(bad), "EF7", table="temp_decay_coef")).json()
    assert not body["ok"] and body["row_errors"][0]["row_number"] == 3

    sample = (SAMPLES / "ef1" / "sample_valid.dat").read_text(encoding="utf-8-sig")
    body = (await _upload(client, headers, "한글\t항목명\n" + sample, "EF1")).json()
    assert body["ok"], (body["file_errors"], body["row_errors"][:3])
    assert body["row_actions"] and body["row_actions"][0]["row_number"] == 3


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
    assert "allow_blank" not in cols["con_rank"]  # 선언한 칸만(EF3 포설·종단, Stage 22-8)
    ef3 = (await client.get("/api/admin/data/template", params={"ef_code": "EF3"}, headers=headers)).json()
    blank = {c["name"] for c in ef3["columns"] if c.get("allow_blank")}
    assert blank == {"laying_type", "laying_type2", "end_joint", "end_joint2"}

    ref = (await client.get("/api/admin/data/template", params={"ef_code": "EF7", "table": "temp_decay_coef"}, headers=headers)).json()
    assert ref["header"] == "year\tgamma_y" and ref["key"] == ["year"]
    assert {c["name"]: c for c in ref["columns"]}["gamma_y"]["gt"] == 0

    assert (await client.get("/api/admin/data/template", params={"ef_code": "EF99"}, headers=headers)).status_code == 404
    resp = await client.get("/api/admin/data/template", params={"ef_code": "EF1", "table": "x"}, headers=headers)
    assert resp.status_code == 404


# --- 행 편집 (Stage 18) ---


def _tsv(header, rows):
    return "\n".join("\t".join(r) for r in [header, *rows]) + "\n"


async def test_rows_match_export_for_every_type_and_reference(client, admin_headers, session_factory):
    """행 편집 표는 내려받기 dat와 같은 내용이다(같은 함수) — 칸 설명·판정 칸도 양식과 같다."""
    headers, _ = admin_headers
    await _seed(session_factory, [c for c in registered_codes() if c != "EF1"], rows=4)

    targets = [(code, "") for code in registered_codes()] + [("EF7", "discharge_history"), ("EF7", "temp_decay_coef")]
    for code, table in targets:
        params = {"ef_code": code, "table": table}
        body = (await client.get("/api/admin/data/rows", params=params, headers=headers)).json()
        dat = (await client.get("/api/admin/data/export", params=params, headers=headers)).content.decode("utf-8-sig")
        lines = [line.split("\t") for line in dat.splitlines()]
        assert body["header"] == lines[1], (code, table)  # 1행은 한글 항목명(Stage 22-9)
        assert body["rows"] == lines[2:], (code, table)
        tpl = (await client.get("/api/admin/data/template", params=params, headers=headers)).json()
        assert body["key"] == tpl["key"] and body["columns"] == tpl["columns"]
        assert body["extra_columns"] == []


async def test_rows_api_errors_and_permission(client, admin_headers):
    headers, store = admin_headers
    assert (await client.get("/api/admin/data/rows", params={"ef_code": "EF99"}, headers=headers)).status_code == 404
    resp = await client.get("/api/admin/data/rows", params={"ef_code": "EF7", "table": "nope"}, headers=headers)
    assert resp.status_code == 404
    user_token, _ = store.issue_session("user")
    resp = await client.get("/api/admin/data/rows", params={"ef_code": "EF1"}, headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403


async def test_editing_one_row_updates_only_that_equipment(client, admin_headers, session_factory):
    """고친 행만 보내면(추가·갱신) 그 설비만 바뀌고 나머지 설비 점수와 건수는 그대로다."""
    headers, _ = admin_headers
    await _seed(session_factory, ["EF2"], rows=6)
    body = (await client.get("/api/admin/data/rows", params={"ef_code": "EF2"}, headers=headers)).json()
    header, rows = body["header"], body["rows"]
    key_idx = [header.index(k) for k in body["key"]]
    # 행마다 값이 다른 칸을 골라, 0번 행 값을 다른 행의 (유효한) 값으로 바꾼다
    ci = next(i for i in range(len(header)) if i not in key_idx and rows[0][i] != rows[1][i])
    edited = list(rows[0])
    edited[ci] = rows[1][ci]
    before = await _scores(client, "EF2")
    target = (rows[0][key_idx[0]], rows[0][key_idx[1]])

    check = (await _upload(client, headers, _tsv(header, [edited]), "EF2")).json()
    assert check["ok"], check["row_errors"][:3]
    assert check["row_actions"] == [{"row_number": 2, "action": "갱신"}]
    applied = (await _upload(client, headers, _tsv(header, [edited]), "EF2", check=False)).json()
    assert applied["ok"] and applied["imported_rows"] == 1

    after_rows = (await client.get("/api/admin/data/rows", params={"ef_code": "EF2"}, headers=headers)).json()["rows"]
    assert len(after_rows) == len(rows)
    changed = next(r for r in after_rows if (r[key_idx[0]], r[key_idx[1]]) == target)
    assert changed[ci] == edited[ci]
    after = await _scores(client, "EF2")
    assert [s for s in after if s[:2] != target] == [s for s in before if s[:2] != target]


async def test_duplicated_row_with_new_name_is_added(client, admin_headers):
    headers, _ = admin_headers
    body = (await client.get("/api/admin/data/rows", params={"ef_code": "EF1"}, headers=headers)).json()
    header = body["header"]
    new_row = list(body["rows"][0])
    new_row[header.index(body["key"][1])] = "TR_NEW_ROW"

    check = (await _upload(client, headers, _tsv(header, [new_row]), "EF1")).json()
    assert check["ok"] and check["row_actions"] == [{"row_number": 2, "action": "추가"}]
    applied = (await _upload(client, headers, _tsv(header, [new_row]), "EF1", check=False)).json()
    assert applied["ok"]
    rows = (await client.get("/api/admin/data/rows", params={"ef_code": "EF1"}, headers=headers)).json()["rows"]
    assert len(rows) == len(body["rows"]) + 1


async def test_editing_reference_row_updates_by_key(client, admin_headers, session_factory):
    headers, _ = admin_headers
    await _seed(session_factory, ["EF7"], rows=3)
    params = {"ef_code": "EF7", "table": "temp_decay_coef"}
    body = (await client.get("/api/admin/data/rows", params=params, headers=headers)).json()
    header, rows = body["header"], body["rows"]
    key_idx = [header.index(k) for k in body["key"]]
    ci = next(i for i in range(len(header)) if i not in key_idx and rows[0][i] != rows[1][i])
    edited = list(rows[0])
    edited[ci] = rows[1][ci]

    check = (await _upload(client, headers, _tsv(header, [edited]), "EF7", table="temp_decay_coef")).json()
    assert check["ok"], check["row_errors"][:3]
    assert check["row_actions"][0]["action"] == "갱신"
    applied = (await _upload(client, headers, _tsv(header, [edited]), "EF7", table="temp_decay_coef", check=False)).json()
    assert applied["ok"] and applied["updated_rows"] == 1 and applied["table_rows_after"] == len(rows)
    after = (await client.get("/api/admin/data/rows", params=params, headers=headers)).json()["rows"]
    assert edited in after and rows[0] not in after
