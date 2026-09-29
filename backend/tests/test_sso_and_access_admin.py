import app.api.routes.admin as admin_routes
from app.auth.state import AdminAuthStore, get_auth_store
from app.core.config import get_settings
from app.main import app

# SSO_BROKER_CONFIGURED/oauth는 app.auth.oidc 모듈이 처음 import될 때 그 시점의
# backend/.env로 한 번 고정된다(요청마다 다시 읽지 않음). 게다가 admin.py가
# `from app.auth.oidc import SSO_BROKER_CONFIGURED`로 값을 복사해와서 자기 모듈
# 네임스페이스에 묶어두므로, oidc.SSO_BROKER_CONFIGURED를 patch해도 admin.py가
# 보는 값은 안 바뀐다 — admin_routes.SSO_BROKER_CONFIGURED를 직접 patch해야
# 로컬 .env 내용과 무관하게 결정적으로 동작한다(a-ims-prod도 같은 이유로 이렇게 처리함).


async def test_sso_login_disabled_without_issuer_url(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "sso")
    monkeypatch.setattr(admin_routes, "SSO_BROKER_CONFIGURED", False)
    get_settings.cache_clear()
    try:
        resp = await client.get("/api/admin/sso/login")
        assert resp.status_code == 503
    finally:
        get_settings.cache_clear()


async def test_local_login_blocked_in_sso_mode_unless_allowed(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "sso")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", "test-pw")
    monkeypatch.setenv("SSO_ALLOW_LOCAL_LOGIN", "false")
    get_settings.cache_clear()
    try:
        resp = await client.post("/api/admin/login", json={"password": "test-pw"})
        assert resp.status_code == 503

        monkeypatch.setenv("SSO_ALLOW_LOCAL_LOGIN", "true")
        get_settings.cache_clear()

        resp = await client.post("/api/admin/login", json={"password": "test-pw"})
        assert resp.status_code == 200
    finally:
        get_settings.cache_clear()


async def test_sso_callback_disabled_without_issuer_url(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "sso")
    monkeypatch.setattr(admin_routes, "SSO_BROKER_CONFIGURED", False)
    get_settings.cache_clear()
    try:
        # 콜백은 브라우저 리다이렉트 도중이라 raw 오류 대신 항상 /admin#error=코드로
        # 돌려보낸다(프론트가 읽을 수 있는 메시지를 보여주기 위함).
        resp = await client.get("/api/admin/sso/callback", follow_redirects=False)
        assert resp.status_code == 307
        assert "#error=sso_not_configured" in resp.headers["location"]
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
