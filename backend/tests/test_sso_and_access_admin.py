from app.auth.state import AdminAuthStore, get_auth_store
from app.core.config import get_settings
from app.main import app


async def test_sso_login_disabled_without_issuer_url(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "sso")
    get_settings.cache_clear()
    try:
        resp = await client.get("/api/admin/sso/login")
        assert resp.status_code == 503
    finally:
        get_settings.cache_clear()


async def test_sso_callback_disabled_without_issuer_url(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "sso")
    get_settings.cache_clear()
    try:
        resp = await client.get("/api/admin/sso/callback")
        assert resp.status_code == 503
    finally:
        get_settings.cache_clear()


async def test_non_admin_session_can_browse_but_not_manage_access(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "local")
    get_settings.cache_clear()
    test_store = AdminAuthStore()
    app.dependency_overrides[get_auth_store] = lambda: test_store

    try:
        viewer_token, _ = test_store.issue_session(is_admin=False)
        headers = {"Authorization": f"Bearer {viewer_token}"}

        # require_session만 필요한 테이블 조회는 통과
        resp = await client.get("/api/admin/tables", headers=headers)
        assert resp.status_code == 200

        # require_admin이 필요한 접근권한 관리는 403
        resp = await client.get("/api/admin/access-users", headers=headers)
        assert resp.status_code == 403

        admin_token, _ = test_store.issue_session(is_admin=True)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        resp = await client.get("/api/admin/access-users", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_auth_store, None)
        get_settings.cache_clear()


async def test_access_users_crud(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "local")
    get_settings.cache_clear()
    test_store = AdminAuthStore()
    app.dependency_overrides[get_auth_store] = lambda: test_store

    try:
        admin_token, _ = test_store.issue_session(is_admin=True)
        headers = {"Authorization": f"Bearer {admin_token}"}

        resp = await client.post(
            "/api/admin/access-users",
            json={"sso_id": "alice@company.com", "name": "Alice", "team": "Ops", "is_admin": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["sso_id"] == "alice@company.com"

        resp = await client.patch(
            "/api/admin/access-users/alice@company.com",
            json={"team": "Platform"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["team"] == "Platform"

        resp = await client.delete("/api/admin/access-users/alice@company.com", headers=headers)
        assert resp.status_code == 200

        resp = await client.delete("/api/admin/access-users/alice@company.com", headers=headers)
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_auth_store, None)
        get_settings.cache_clear()
