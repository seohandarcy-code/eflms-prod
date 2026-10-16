"""AUTH_MODE/SSO_FLOW_MODE 설정 검증 (Stage 6-8, backend/app/auth/SSO_MODES.md 참고).

Settings(_env_file=None)로 로컬 backend/.env 내용과 무관하게 OS 환경변수만으로
판정한다 — 이 파일이 확인하려는 게 바로 "프로세스 환경변수가 어떻게 해석되는가"다.
"""

import logging

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def _settings() -> Settings:
    return Settings(_env_file=None)


def test_sso_flow_mode_defaults_to_auth_code(monkeypatch):
    monkeypatch.delenv("SSO_FLOW_MODE", raising=False)
    assert _settings().sso_flow_mode == "auth_code"


@pytest.mark.parametrize("raw", ["IMPLICIT_FORM_POST", "  implicit_form_post  ", "Implicit_Form_Post"])
def test_sso_flow_mode_normalizes_case_and_whitespace(monkeypatch, raw):
    monkeypatch.setenv("SSO_FLOW_MODE", raw)
    assert _settings().sso_flow_mode == "implicit_form_post"


def test_auth_mode_normalizes_case_and_whitespace(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", " SSO ")
    assert _settings().auth_mode == "sso"


@pytest.mark.parametrize(
    ("name", "raw"),
    [
        ("SSO_FLOW_MODE", "auth-code"),  # 오타 — 예전엔 조용히 auth_code 분기로 떨어졌다
        ("SSO_FLOW_MODE", ""),  # 셸/ConfigMap에 남은 빈 변수
        ("AUTH_MODE", "oidc"),
        ("AUTH_MODE", ""),
    ],
)
def test_invalid_or_blank_mode_fails_fast(monkeypatch, name, raw):
    monkeypatch.setenv(name, raw)
    with pytest.raises(ValidationError) as exc_info:
        _settings()
    assert name.lower() in str(exc_info.value)


def test_blank_user_id_claim_falls_back_to_email(monkeypatch):
    monkeypatch.setenv("SSO_USER_ID_CLAIM", "  ")
    assert _settings().sso_user_id_claim == "email"


def test_blank_process_env_logs_warning(monkeypatch, caplog):
    monkeypatch.setenv("SSO_USER_ID_CLAIM", "")
    get_settings.cache_clear()
    try:
        with caplog.at_level(logging.WARNING, logger="eflms.config"):
            get_settings()
    finally:
        get_settings.cache_clear()
    assert any("SSO_USER_ID_CLAIM" in rec.getMessage() for rec in caplog.records)


def test_auth_summary_excludes_secrets(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "sso")
    monkeypatch.setenv("SSO_ISSUER_URL", "https://adfs.company.local/adfs")
    monkeypatch.setenv("SSO_CLIENT_ID", "eflms-client")
    monkeypatch.setenv("SSO_CLIENT_SECRET", "super-secret-value")
    summary = _settings().auth_summary()
    assert "sso_flow_mode=auth_code" in summary
    assert "https://adfs.company.local/adfs" in summary
    assert "super-secret-value" not in summary
    assert "eflms-client" not in summary
