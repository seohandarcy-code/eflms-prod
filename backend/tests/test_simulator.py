"""Stage 19 — 점수 시뮬레이터(계산만, DB 쓰기 없음) + 사업장별 참고표(EF7 방전이력) 규칙."""
from datetime import date

from sqlalchemy import delete, func, select

from app.db.models import BatteryDischargeHistory, Equipment, ScoreSnapshot
from app.equipment_types import ef3_cable, ef6_vdp, ef7_battery
from app.services.import_service import import_file
from app.services.ingest import ingest_row
from app.services.reference_data import calc_options, ensure_mock_reference
from app.services.reference_service import import_reference_file
from tests.test_auth_roles import _cleanup, _use_store


async def _seed(session_factory, module, rows):
    async with session_factory() as session:
        if module is ef7_battery:
            await ensure_mock_reference(session, module)
        options = await calc_options(session, module)
        ids = [await ingest_row(module.calculate(r, **options), session) for r in rows]
        await session.commit()
        return ids


def _vdp(eqp_id, factory="H1"):
    row = ef6_vdp.generate_input_row()
    row.update(eqp_id=eqp_id, factory_code=factory)
    return row


def _battery(eqp_id, factory="H1"):
    row = ef7_battery.generate_input_row()
    row.update(eqp_id=eqp_id, factory_code=factory, operation_start_time=date(2016, 1, 1), bat_room_temp=25.0)
    return row


async def _keep_only_h1_discharge(session_factory):
    async with session_factory() as session:
        await session.execute(delete(BatteryDischargeHistory).where(BatteryDischargeHistory.factory_code != "H1"))
        await session.commit()


async def test_form_lists_only_sites_that_have_data(client, session_factory):
    await _seed(session_factory, ef6_vdp, [_vdp("v1"), _vdp("v2")])
    body = (await client.get("/api/simulator/EF6/form")).json()
    assert [s["factory_code"] for s in body["sites"]] == ["H1"]
    assert body["sites"][0]["equipment_count"] == 2
    assert body["excluded_sites"] == []
    assert {e["equipment_name"] for e in body["equipment"]} == {"v1", "v2"}
    names = [c["name"] for c in body["columns"]]
    assert names[0] == "factory_code" and "online_diag" in names
    assert body["header"].split("\t") == names


async def test_existing_equipment_reproduces_stored_score_and_changes(client, session_factory):
    [eq_id] = await _seed(session_factory, ef6_vdp, [_vdp("v1")])
    sample = (await client.get(f"/api/simulator/EF6/sample?equipment_id={eq_id}")).json()
    assert sample["source"] == "equipment" and sample["values"]["eqp_id"] == "v1"
    async with session_factory() as session:
        stored = await session.get(ScoreSnapshot, eq_id)
    assert sample["baseline"]["ok"]
    assert sample["baseline"]["total_score"] == stored.total_score  # 같은 날 저장 → 같은 점수

    values = dict(sample["values"])
    values["online_diag"] = "적용" if values["online_diag"] == "미적용" else "미적용"
    changed = (await client.post("/api/simulator/EF6/calculate", json={"values": values})).json()
    assert changed["ok"] and changed["dof"] != sample["baseline"]["dof"]
    assert changed["status"] in ("normal", "review", "replace")
    assert set(changed["breakdown"]) == {"pof", "cof", "dof"}


async def test_field_errors_and_na(client, session_factory):
    await _seed(session_factory, ef6_vdp, [_vdp("v1")])
    sample = (await client.get("/api/simulator/EF6/sample")).json()
    assert sample["source"] == "example" and sample["values"]["factory_code"] == "H1"

    values = dict(sample["values"], load="abc", thermal_img_chk="좋음", factory_code="Z9", eqp_id="N/A")
    body = (await client.post("/api/simulator/EF6/calculate", json={"values": values})).json()
    assert not body["ok"]
    reasons = {e["column"]: e["reason"] for e in body["errors"]}
    assert set(reasons) == {"load", "thermal_img_chk", "factory_code", "eqp_id"}

    na = dict(sample["values"], noise="N/A")
    body = (await client.post("/api/simulator/EF6/calculate", json={"values": na})).json()
    assert body["ok"]
    noise = next(i for i in body["breakdown"]["pof"] if i["label"] == "소음")
    assert noise["value"] == 0  # N/A면 평가하지 않음(감점 0)


async def test_ef3_blank_laying_and_decimal_load(client, session_factory):
    """Stage 22-8: 포설·종단 빈칸은 받고(다른 쪽 감점), 최대부하는 소수도 받는다 — 데이터 입력과 같은 검사."""
    row = ef3_cable.generate_input_row()
    row["factory_code"] = "H1"
    await _seed(session_factory, ef3_cable, [row])
    sample = (await client.get("/api/simulator/EF3/sample")).json()
    values = dict(sample["values"], laying_type="철탑", laying_type2="", end_joint="", end_joint2="", max_load="154.5")
    body = (await client.post("/api/simulator/EF3/calculate", json={"values": values})).json()
    assert body["ok"], body["errors"]
    cof = {i["label"]: i["value"] for i in body["breakdown"]["cof"]}
    assert cof["포설방법"] == -24 and cof["종단접속함"] == 0
    bad = dict(values, emerge_resp="")
    body = (await client.post("/api/simulator/EF3/calculate", json={"values": bad})).json()
    assert [e["column"] for e in body["errors"]] == ["emerge_resp"]


async def test_simulator_never_writes(client, session_factory):
    [eq_id] = await _seed(session_factory, ef6_vdp, [_vdp("v1")])
    async with session_factory() as session:
        before = (await session.get(ScoreSnapshot, eq_id)).total_score
        count = await session.scalar(select(func.count()).select_from(Equipment))
    sample = (await client.get(f"/api/simulator/EF6/sample?equipment_id={eq_id}")).json()
    values = dict(sample["values"], load="99", noise="95")
    assert (await client.post("/api/simulator/EF6/calculate", json={"values": values})).json()["ok"]
    async with session_factory() as session:
        assert (await session.get(ScoreSnapshot, eq_id)).total_score == before
        assert await session.scalar(select(func.count()).select_from(Equipment)) == count


async def test_unknown_type_and_wrong_equipment_404(client, session_factory):
    [eq_id] = await _seed(session_factory, ef6_vdp, [_vdp("v1")])
    assert (await client.get("/api/simulator/EF99/form")).status_code == 404
    assert (await client.get(f"/api/simulator/EF7/sample?equipment_id={eq_id}")).status_code == 404


async def test_battery_sites_follow_discharge_history(client, session_factory, tmp_path):
    ids = await _seed(session_factory, ef7_battery, [_battery("b1", "H1"), _battery("b2", "H2")])
    await _keep_only_h1_discharge(session_factory)

    body = (await client.get("/api/simulator/EF7/form")).json()
    assert [s["factory_code"] for s in body["sites"]] == ["H1"]
    assert body["excluded_sites"][0]["factory_code"] == "H2"
    assert "방전이력" in body["excluded_sites"][0]["reason"]
    assert [e["equipment_name"] for e in body["equipment"]] == ["b1"]
    assert (await client.get(f"/api/simulator/EF7/sample?equipment_id={ids[1]}")).status_code == 404

    values = (await client.get(f"/api/simulator/EF7/sample?equipment_id={ids[0]}")).json()["values"]
    refused = (await client.post("/api/simulator/EF7/calculate", json={"values": dict(values, factory_code="H2")})).json()
    assert not refused["ok"] and refused["errors"][0]["column"] == "factory_code"

    # 관리자가 H2 방전이력을 넣으면 코드 변경 없이 바로 계산 대상이 된다
    path = tmp_path / "h2.dat"
    path.write_text("disch_date\tfactory_code\tvolt_change\tdisch_index\n2020-01-01\tH2\t10\t4.5\n", encoding="utf-8")
    async with session_factory() as session:
        assert (await import_reference_file(str(path), "EF7", "discharge_history", session)).ok
    body = (await client.get("/api/simulator/EF7/form")).json()
    assert [s["factory_code"] for s in body["sites"]] == ["H1", "H2"] and body["excluded_sites"] == []
    ok = (await client.post("/api/simulator/EF7/calculate", json={"values": dict(values, factory_code="H2")})).json()
    assert ok["ok"]


async def test_import_warns_but_does_not_block_site_without_history(client, session_factory, tmp_path):
    await _seed(session_factory, ef7_battery, [_battery("b1", "H1")])
    await _keep_only_h1_discharge(session_factory)
    header = [c["name"] for c in ef7_battery.INPUT_COLUMNS]
    row = _battery("b9", "H2")
    line = ["N/A" if row.get(h) is None else (row[h].isoformat() if hasattr(row[h], "isoformat") else str(row[h])) for h in header]
    path = tmp_path / "ef7.dat"
    path.write_text("\t".join(header) + "\n" + "\t".join(line) + "\n", encoding="utf-8")
    async with session_factory() as session:
        result = await import_file(str(path), "EF7", session)
    assert not result.row_errors and not result.file_errors
    assert result.imported_rows == 1
    assert any("H2" in w and "방전이력" in w for w in result.reference_warnings)
    assert not any("H1" in w for w in result.reference_warnings)


async def test_simulator_requires_session_in_sso_mode(client, monkeypatch):
    store = _use_store(monkeypatch, "sso")
    try:
        assert (await client.get("/api/simulator/EF1/form")).status_code == 401
        assert (await client.post("/api/simulator/EF1/calculate", json={"values": {}})).status_code == 401
        token, _ = store.issue_session("general")
        resp = await client.get("/api/simulator/EF1/form", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
    finally:
        _cleanup()
