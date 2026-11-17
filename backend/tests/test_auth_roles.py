"""Stage 16-1 — 역할(admin/user/general), 대시보드 로그인(sso 모드), SSO 콜백 정리 테스트."""
import urllib.parse

from fastapi.responses import RedirectResponse

import app.api.routes.admin as admin_routes
from app.api.routes.admin import _safe_next
from app.auth.state import AdminAuthStore, get_auth_store
from app.core.config import get_settings
from app.main import app


def _use_store(monkeypatch, mode: str) -> AdminAuthStore:
    monkeypatch.setenv("AUTH_MODE", mode)
    get_settings.cache_clear()
    store = AdminAuthStore()
    app.dependency_overrides[get_auth_store] = lambda: store
    return store


def _cleanup():
    app.dependency_overrides.pop(get_auth_store, None)
    get_settings.cache_clear()


def _fake_oauth(monkeypatch, claims: dict):
    class _FakeSsoClient:
        async def authorize_redirect(self, request, redirect_uri, **kwargs):
            return RedirectResponse("https://idp.example/authorize")

        async def authorize_access_token(self, request):
            return {"userinfo": claims}

    class _FakeOAuth:
        sso = _FakeSsoClient()

    monkeypatch.setenv("SSO_FLOW_MODE", "auth_code")
    monkeypatch.setattr(admin_routes, "SSO_BROKER_CONFIGURED", True)
    monkeypatch.setattr(admin_routes, "oauth", _FakeOAuth())


def _fragment(location: str) -> dict[str, str]:
    return dict(urllib.parse.parse_qsl(location.split("#", 1)[1]))


# --- 대시보드 로그인 (require_viewer) ---


async def test_dashboard_is_public_in_none_and_local_modes(client, monkeypatch):
    for mode in ("none", "local"):
        _use_store(monkeypatch, mode)
        try:
            assert (await client.get("/api/equipment-types")).status_code == 200
            assert (await client.get("/api/summary")).status_code == 200
        finally:
            _cleanup()


async def test_dashboard_requires_session_in_sso_mode(client, monkeypatch):
    store = _use_store(monkeypatch, "sso")
    try:
        for path in ("/api/equipment-types", "/api/equipment", "/api/summary", "/api/equipment/1"):
            assert (await client.get(path)).status_code == 401, path
        assert (await client.get("/api/summary", headers={"Authorization": "Bearer nope"})).status_code == 401

        for role in ("general", "user", "admin"):
            token, _ = store.issue_session(role)
            resp = await client.get("/api/equipment", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200, role
    finally:
        _cleanup()


async def test_auth_config_reports_dashboard_login(client, monkeypatch):
    for mode, expected in (("none", False), ("local", False), ("sso", True)):
        monkeypatch.setenv("AUTH_MODE", mode)
        get_settings.cache_clear()
        try:
            body = (await client.get("/api/admin/auth-config")).json()
            assert body["dashboard_login_required"] is expected
        finally:
            get_settings.cache_clear()


# --- 역할별 관리자 기능 ---


async def test_general_session_cannot_use_admin_screens(client, monkeypatch):
    store = _use_store(monkeypatch, "sso")
    try:
        token, _ = store.issue_session("general")
        headers = {"Authorization": f"Bearer {token}"}
        assert (await client.get("/api/admin/tables", headers=headers)).status_code == 403
        assert (await client.get("/api/admin/access-users", headers=headers)).status_code == 403

        user_token, _ = store.issue_session("user")
        user_headers = {"Authorization": f"Bearer {user_token}"}
        assert (await client.get("/api/admin/tables", headers=user_headers)).status_code == 200
        assert (await client.get("/api/admin/access-users", headers=user_headers)).status_code == 403
    finally:
        _cleanup()


def test_issue_session_rejects_unknown_role():
    store = AdminAuthStore()
    try:
        store.issue_session("root")  # type: ignore[arg-type]
    except ValueError:
        return
    raise AssertionError("알 수 없는 역할이 통과함")


async def test_duplicate_access_user_returns_409(client, monkeypatch):
    store = _use_store(monkeypatch, "local")
    try:
        token, _ = store.issue_session("admin")
        headers = {"Authorization": f"Bearer {token}"}
        body = {"sso_id": "kim@company.com", "name": "김철수", "team": None, "is_admin": False}
        assert (await client.post("/api/admin/access-users", json=body, headers=headers)).status_code == 200
        resp = await client.post("/api/admin/access-users", json=body, headers=headers)
        assert resp.status_code == 409
        assert "이미 등록된 계정" in resp.json()["detail"]
        # 앞뒤 공백만 다른 ID도 같은 계정
        resp = await client.post(
            "/api/admin/access-users", json={**body, "sso_id": " kim@company.com "}, headers=headers
        )
        assert resp.status_code == 409
    finally:
        _cleanup()


# --- SSO 콜백 ---


async def test_callback_unregistered_user_gets_general_session(client, monkeypatch):
    store = _use_store(monkeypatch, "sso")
    _fake_oauth(monkeypatch, {"email": "guest@company.com", "name": "게스트 사용자"})
    monkeypatch.setenv("SSO_ADMIN_ALLOWLIST", "")
    get_settings.cache_clear()
    try:
        resp = await client.get("/api/admin/sso/callback", follow_redirects=False)
        location = resp.headers["location"]
        assert location.startswith("/#token=")  # 기본 복귀 화면은 대시보드
        frag = _fragment(location)
        assert frag["role"] == "general"
        assert frag["name"] == "게스트 사용자"
        assert store.get_role(frag["token"]) == "general"
    finally:
        _cleanup()


async def test_callback_unregistered_user_denied_when_configured(client, monkeypatch):
    _use_store(monkeypatch, "sso")
    _fake_oauth(monkeypatch, {"email": "guest@company.com"})
    monkeypatch.setenv("SSO_ADMIN_ALLOWLIST", "")
    monkeypatch.setenv("SSO_DENY_UNREGISTERED_USERS", "true")
    get_settings.cache_clear()
    try:
        resp = await client.get("/api/admin/sso/callback", follow_redirects=False)
        assert "#error=not_registered" in resp.headers["location"]
    finally:
        _cleanup()


async def test_callback_encodes_name_and_uses_claim_name_for_bootstrap_admin(client, monkeypatch):
    _use_store(monkeypatch, "sso")
    _fake_oauth(monkeypatch, {"email": " boss@company.com ", "name": "홍 길동 & 팀"})
    monkeypatch.setenv("SSO_ADMIN_ALLOWLIST", "boss@company.com")
    get_settings.cache_clear()
    try:
        resp = await client.get("/api/admin/sso/callback", follow_redirects=False)
        location = resp.headers["location"]
        # 이름 안의 & 가 프래그먼트 파라미터를 끊지 않는다
        assert "&name=%ED%99%8D%20%EA%B8%B8%EB%8F%99%20%26%20%ED%8C%80" in location
        frag = _fragment(location)
        assert frag["role"] == "admin"
        assert frag["name"] == "홍 길동 & 팀"
    finally:
        _cleanup()


async def test_login_returns_to_requested_screen(client, monkeypatch):
    _use_store(monkeypatch, "sso")
    _fake_oauth(monkeypatch, {"email": "boss@company.com"})
    monkeypatch.setenv("SSO_ADMIN_ALLOWLIST", "boss@company.com")
    get_settings.cache_clear()
    try:
        resp = await client.get("/api/admin/sso/login", params={"next": "/admin"}, follow_redirects=False)
        assert resp.headers["location"] == "https://idp.example/authorize"
        resp = await client.get("/api/admin/sso/callback", follow_redirects=False)
        assert resp.headers["location"].startswith("/admin#token=")

        # 실패도 시작한 화면으로
        resp = await client.get("/api/admin/sso/login", params={"next": "/guide"}, follow_redirects=False)
        _fake_oauth(monkeypatch, {"email": "stranger@company.com"})
        monkeypatch.setenv("SSO_DENY_UNREGISTERED_USERS", "true")
        get_settings.cache_clear()
        resp = await client.get("/api/admin/sso/callback", follow_redirects=False)
        assert resp.headers["location"].startswith("/guide#error=not_registered")
    finally:
        _cleanup()


async def test_sso_not_configured_returns_to_requested_screen(client, monkeypatch):
    _use_store(monkeypatch, "sso")
    monkeypatch.setattr(admin_routes, "SSO_BROKER_CONFIGURED", False)
    try:
        resp = await client.get("/api/admin/sso/login", params={"next": "/"}, follow_redirects=False)
        assert resp.headers["location"] == "/#error=sso_not_configured"
    finally:
        _cleanup()


def test_safe_next_blocks_external_redirects():
    assert _safe_next("/admin") == "/admin"
    assert _safe_next("/guide?x=1#frag") == "/guide?x=1"
    for bad in (None, "", "admin", "//evil.example", "https://evil.example", "/\\evil.example", 3):
        assert _safe_next(bad) == "/", bad
