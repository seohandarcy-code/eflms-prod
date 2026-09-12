async def test_healthz(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_summary_counts_seeded_rows(client):
    resp = await client.get("/api/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_equipment"] == 3
    assert 0 <= data["needs_inspection_count"] <= 3


async def test_equipment_list_is_sorted_by_total_score(client):
    resp = await client.get("/api/equipment")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    scores = [item["total_score"] for item in items]
    assert scores == sorted(scores)


async def test_equipment_detail_matches_list_entry(client):
    items = (await client.get("/api/equipment")).json()
    first_id = items[0]["equipment_id"]

    detail = (await client.get(f"/api/equipment/{first_id}")).json()
    assert detail["equipment_id"] == first_id
    assert detail["score"]["total_score"] == items[0]["total_score"]
    assert "score_detail" in detail
    assert "dga" in detail and "design" in detail


async def test_equipment_detail_404_for_unknown_id(client):
    resp = await client.get("/api/equipment/999999")
    assert resp.status_code == 404
