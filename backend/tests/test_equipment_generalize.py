"""Stage 8-1 — 공통 equipment에서 분리된 EF1 정격용량(transformer_spec)이 적재·조회 경로에서
그대로 이어지는지 확인한다."""

from sqlalchemy import select

from app.db.models import Equipment, TransformerSpec


async def test_ingest_writes_transformer_spec_and_detail_reads_it(client, session_factory):
    async with session_factory() as session:
        equipment = (await session.execute(select(Equipment))).scalars().first()
        spec = await session.get(TransformerSpec, equipment.equipment_id)
    assert spec is not None

    resp = await client.get(f"/api/equipment/{equipment.equipment_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["equipment_name"] == equipment.equipment_name
    # Stage 8-4부터 EF1 정격용량은 type_detail.spec에 있다
    assert body["type_detail"]["spec"]["onan_val"] == spec.onan_val
    assert body["type_detail"]["spec"]["onaf_val"] == spec.onaf_val
    assert "transformer_name" not in body


async def test_equipment_list_uses_equipment_name(client):
    resp = await client.get("/api/equipment")
    items = resp.json()
    assert items and all("equipment_name" in item and "transformer_name" not in item for item in items)
