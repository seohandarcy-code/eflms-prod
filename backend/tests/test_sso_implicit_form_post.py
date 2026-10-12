"""SSO_FLOW_MODE=implicit_form_post(discovery 미지원 자체 브로커) 전용 테스트.

app/auth/oidc.py의 build_broker_authorize_url()/verify_broker_id_token()을
합성 RSA 키쌍으로 검증하고, POST /api/admin/sso/callback 통합 경로까지 확인한다.

주의 — oidc._settings는 모듈 import 시점에 get_settings()가 반환한 Settings
인스턴스를 그대로 들고 있다(app.auth.oidc 상단 참고). admin.py 라우터 핸들러는
매 요청마다 get_settings()를 새로 호출해 monkeypatch.setenv +
get_settings.cache_clear()를 바로 반영하지만, verify_broker_id_token()/
build_broker_authorize_url()은 그 프로세스를 타지 않고 oidc._settings를 직접
참조한다 — 그래서 이 테스트들은 oidc._settings의 속성을 직접
monkeypatch.setattr()로 바꾼다(test_sso_and_access_admin.py 상단에 적힌
SSO_BROKER_CONFIGURED cross-module 바인딩 문제와 같은 계열의 함정).
"""
import json
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

import app.api.routes.admin as admin_routes
import app.auth.oidc as oidc
from app.core.config import get_settings


def _generate_rsa_private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwk_from_public_key(public_key, kid: str) -> dict:
    jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk["kid"] = kid
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return jwk


def _sign_id_token(private_key, kid: str, claims: dict) -> str:
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


def _fake_jwks_response(jwks: dict):
    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return jwks

    return _FakeResponse()


@pytest.fixture
def broker_keypair():
    private_key = _generate_rsa_private_key()
    return private_key, private_key.public_key()


# --- 단위 테스트: build_broker_authorize_url ---


def test_build_broker_authorize_url_uses_client_id_and_redirect_uri(monkeypatch):
    monkeypatch.setattr(oidc._settings, "sso_issuer_url", "https://broker.company.local")
    monkeypatch.setattr(oidc._settings, "sso_client_id", "eflms-service")

    url = oidc.build_broker_authorize_url("https://eflms.company.local/api/admin/sso/callback")

    assert url.startswith("https://broker.company.local/oidc/form-authorize?")
    assert "client_id=eflms-service" in url
    assert "redirect_uri=https%3A%2F%2Feflms.company.local%2Fapi%2Fadmin%2Fsso%2Fcallback" in url


# --- 단위 테스트: verify_broker_id_token ---


def test_verify_broker_id_token_accepts_valid_signature(monkeypatch, broker_keypair):
    private_key, public_key = broker_keypair
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    token = _sign_id_token(private_key, "key-1", {"sub": "alice@company.local", "exp": int(time.time()) + 300})

    monkeypatch.setattr(oidc._settings, "sso_issuer_url", "https://broker.company.local")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _fake_jwks_response({"keys": [jwk]}))

    claims = oidc.verify_broker_id_token(token)
    assert claims["sub"] == "alice@company.local"


def test_verify_broker_id_token_rejects_expired_token(monkeypatch, broker_keypair):
    private_key, public_key = broker_keypair
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    token = _sign_id_token(private_key, "key-1", {"sub": "alice@company.local", "exp": int(time.time()) - 10})

    monkeypatch.setattr(oidc._settings, "sso_issuer_url", "https://broker.company.local")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _fake_jwks_response({"keys": [jwk]}))

    with pytest.raises(jwt.ExpiredSignatureError):
        oidc.verify_broker_id_token(token)


def test_verify_broker_id_token_rejects_wrong_signature(monkeypatch, broker_keypair):
    _private_key, public_key = broker_keypair
    other_private_key = _generate_rsa_private_key()
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    # JWKS에는 원래 public_key만 올라가 있는데 다른 키로 서명 — 검증 실패해야 함
    token = _sign_id_token(other_private_key, "key-1", {"sub": "alice@company.local", "exp": int(time.time()) + 300})

    monkeypatch.setattr(oidc._settings, "sso_issuer_url", "https://broker.company.local")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _fake_jwks_response({"keys": [jwk]}))

    with pytest.raises(jwt.InvalidTokenError):
        oidc.verify_broker_id_token(token)


def test_verify_broker_id_token_falls_back_to_first_key_without_kid_match(monkeypatch, broker_keypair):
    private_key, public_key = broker_keypair
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    # 토큰 헤더의 kid가 JWKS 어느 키와도 안 맞음 — keys[0]으로 폴백해야 함
    # (kid 없이 단일 키만 내려주는 브로커 대응, app/auth/oidc.py 참고)
    token = _sign_id_token(private_key, "unknown-kid", {"sub": "alice@company.local", "exp": int(time.time()) + 300})

    monkeypatch.setattr(oidc._settings, "sso_issuer_url", "https://broker.company.local")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _fake_jwks_response({"keys": [jwk]}))

    claims = oidc.verify_broker_id_token(token)
    assert claims["sub"] == "alice@company.local"


# --- 통합 테스트: POST /api/admin/sso/callback (implicit_form_post) ---


async def test_sso_callback_post_form_issues_admin_session(client, monkeypatch, broker_keypair):
    private_key, public_key = broker_keypair
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    token = _sign_id_token(
        private_key, "key-1", {"email": "admin@company.local", "name": "Admin", "exp": int(time.time()) + 300}
    )

    monkeypatch.setenv("AUTH_MODE", "sso")
    monkeypatch.setenv("SSO_FLOW_MODE", "implicit_form_post")
    monkeypatch.setenv("SSO_ADMIN_ALLOWLIST", "admin@company.local")
    monkeypatch.setattr(admin_routes, "SSO_BROKER_CONFIGURED", True)
    monkeypatch.setattr(oidc._settings, "sso_issuer_url", "https://broker.company.local")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _fake_jwks_response({"keys": [jwk]}))
    get_settings.cache_clear()
    try:
        resp = await client.post("/api/admin/sso/callback", data={"id_token": token}, follow_redirects=False)
        assert resp.status_code == 307
        location = resp.headers["location"]
        assert "#token=" in location
        assert "role=admin" in location
    finally:
        get_settings.cache_clear()


async def test_sso_callback_post_form_rejects_expired_token(client, monkeypatch, broker_keypair):
    private_key, public_key = broker_keypair
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    token = _sign_id_token(private_key, "key-1", {"email": "admin@company.local", "exp": int(time.time()) - 10})

    monkeypatch.setenv("AUTH_MODE", "sso")
    monkeypatch.setenv("SSO_FLOW_MODE", "implicit_form_post")
    monkeypatch.setattr(admin_routes, "SSO_BROKER_CONFIGURED", True)
    monkeypatch.setattr(oidc._settings, "sso_issuer_url", "https://broker.company.local")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _fake_jwks_response({"keys": [jwk]}))
    get_settings.cache_clear()
    try:
        resp = await client.post("/api/admin/sso/callback", data={"id_token": token}, follow_redirects=False)
        assert resp.status_code == 307
        assert "#error=auth_failed" in resp.headers["location"]
    finally:
        get_settings.cache_clear()


async def test_sso_callback_post_form_rejects_unregistered_account(client, monkeypatch, broker_keypair):
    private_key, public_key = broker_keypair
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    token = _sign_id_token(
        private_key, "key-1", {"email": "unknown@company.local", "exp": int(time.time()) + 300}
    )

    monkeypatch.setenv("AUTH_MODE", "sso")
    monkeypatch.setenv("SSO_FLOW_MODE", "implicit_form_post")
    monkeypatch.setenv("SSO_ADMIN_ALLOWLIST", "")
    monkeypatch.setattr(admin_routes, "SSO_BROKER_CONFIGURED", True)
    monkeypatch.setattr(oidc._settings, "sso_issuer_url", "https://broker.company.local")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _fake_jwks_response({"keys": [jwk]}))
    get_settings.cache_clear()
    try:
        resp = await client.post("/api/admin/sso/callback", data={"id_token": token}, follow_redirects=False)
        assert resp.status_code == 307
        assert "#error=not_registered" in resp.headers["location"]
    finally:
        get_settings.cache_clear()
