from app.auth.state import AdminAuthStore, get_auth_store
from app.core.config import get_settings
from app.main import app


async def test_admin_login_disabled_when_auth_mode_none(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "none")
    get_settings.cache_clear()
    try:
        resp = await client.post("/api/admin/login", json={"password": "0000"})
        assert resp.status_code == 503
    finally:
        get_settings.cache_clear()


async def test_admin_login_and_table_access(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "local")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", "test-pw-1234")
    get_settings.cache_clear()
    test_store = AdminAuthStore()
    app.dependency_overrides[get_auth_store] = lambda: test_store

    try:
        resp = await client.get("/api/admin/tables")
        assert resp.status_code == 401

        resp = await client.post("/api/admin/login", json={"password": "wrong"})
        assert resp.status_code == 401

        resp = await client.post("/api/admin/login", json={"password": "test-pw-1234"})
        assert resp.status_code == 200
        token = resp.json()["token"]

        resp = await client.get("/api/admin/tables", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "equipment" in resp.json()["tables"]

        resp = await client.get("/api/admin/tables/equipment", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["table_name"] == "equipment"
        assert body["total"] == 3
        assert len(body["rows"]) == 3

        resp = await client.get("/api/admin/tables/not_a_real_table", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

        resp = await client.post("/api/admin/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        resp = await client.get("/api/admin/tables", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.pop(get_auth_store, None)
        get_settings.cache_clear()


async def test_admin_login_locks_after_max_attempts(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "local")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", "correct-horse")
    get_settings.cache_clear()
    test_store = AdminAuthStore()
    app.dependency_overrides[get_auth_store] = lambda: test_store

    try:
        for _ in range(5):
            resp = await client.post("/api/admin/login", json={"password": "wrong"})
            assert resp.status_code == 401

        resp = await client.post("/api/admin/login", json={"password": "correct-horse"})
        assert resp.status_code == 429
    finally:
        app.dependency_overrides.pop(get_auth_store, None)
        get_settings.cache_clear()
