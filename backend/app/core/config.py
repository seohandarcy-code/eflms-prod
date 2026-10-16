import logging
import os
import urllib.parse
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger("eflms.config")

# pydantic-settings는 OS 프로세스 환경변수를 .env 파일보다 우선하고, 빈 문자열도
# "값이 있음"으로 취급한다 — 셸/ConfigMap에 같은 이름의 빈 변수가 남아 있으면 .env
# 값이 조용히 무시된다(a-ims-prod가 SSO_FLOW_MODE로 실제 겪은 문제, 2026-10-15).
# 모드·자격 선택값처럼 "명시적인 값을 기대하는" 변수만 감시한다 — DATABASE_URL처럼
# 비어있는 게 정상인 변수까지 넣으면 매 기동마다 경고가 떠서 잡음이 된다.
# backend/app/auth/SSO_MODES.md 참고.
_BLANK_ENV_WATCHLIST = ("AUTH_MODE", "SSO_FLOW_MODE", "SSO_USER_ID_CLAIM", "ADMIN_BOOTSTRAP_PASSWORD")


def _warn_blank_process_env() -> None:
    for name in _BLANK_ENV_WATCHLIST:
        raw = os.environ.get(name)
        if raw is not None and raw.strip() == "":
            logger.warning(
                "%s 환경변수가 프로세스에 빈 문자열로 존재합니다 — backend/.env 값보다 우선하므로 "
                ".env 설정이 무시되고 있을 수 있습니다. PowerShell: Test-Path Env:%s 로 확인, "
                "Remove-Item Env:%s 로 제거 후 재기동하세요.",
                name,
                name,
                name,
            )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = ""
    db_host: str = ""
    db_port: str = "5432"
    db_name: str = "eflms"
    db_user: str = ""
    db_password: str = ""
    cors_origins: str = "http://localhost:5173"
    auth_mode: Literal["none", "local", "sso"] = "none"
    auto_seed_if_empty: bool = False
    admin_bootstrap_password: str = ""

    # AUTH_MODE=sso 전용 — Stage 6, docs/ARCHITECTURE.md "인증" 참고.
    # SSO 연동 방식 선택 기준은 "로컬이냐 운영이냐"가 아니라 "IdP가 OIDC discovery를
    # 지원하느냐"다 — auth_code(기본값)는 discovery 지원 IdP 직접 연결(authlib,
    # authorization code flow) — 브로커 없이 ADFS에 직접 붙는 경우(a-ims-prod가 실서버
    # 연동 성공)와 로컬 Keycloak 검증 둘 다 여기 해당한다. implicit_form_post는
    # discovery 미지원 자체 브로커 경유(/oidc/form-authorize + /oidc/jwks,
    # app/auth/oidc.py의 build_broker_authorize_url()/verify_broker_id_token() 참고)
    # — 이제 기본값이 아니므로 필요하면 명시해야 한다(Stage 6-8, 2026-10-16).
    # 클레임을 받은 이후(allowed_users 대조, role 판정, 세션 발급) 로직은 두 모드가
    # 공유한다. 자세한 내용은 backend/app/auth/SSO_MODES.md.
    sso_flow_mode: Literal["auth_code", "implicit_form_post"] = "auth_code"
    sso_issuer_url: str = ""
    sso_client_id: str = ""
    sso_client_secret: str = ""
    sso_redirect_uri: str = ""
    sso_admin_allowlist: str = ""
    sso_user_id_claim: str = "email"
    sso_allow_local_login: bool = False
    # 사내 CA가 발급한 인증서를 쓰는 SSO 브로커(ADFS 등)에 연결할 때, Python(httpx)이
    # Windows와 달리 그 CA를 기본적으로 신뢰하지 않아 SSL 검증에 실패하는 문제 대응
    # (a-ims-prod가 실제 ADFS 연동 중 겪음). 상대경로면 backend/ 기준으로 해석.
    sso_ca_bundle_path: str = ""
    session_secret_key: str = ""
    session_cookie_secure: bool = False
    frontend_base_url: str = ""

    @field_validator("auth_mode", "sso_flow_mode", mode="before")
    @classmethod
    def _normalize_mode(cls, value: object) -> object:
        # 대소문자/앞뒤 공백 차이는 흡수하되, 빈 값이나 오타는 Literal 검증에서 기동
        # 실패로 이어지게 둔다 — 잘못된 모드로 조용히 다른 분기를 타는 것보다 파드가
        # 아예 안 뜨는 편이 원인 파악이 훨씬 빠르다.
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("sso_user_id_claim", mode="after")
    @classmethod
    def _default_blank_claim(cls, value: str) -> str:
        # 빈 클레임명이면 아무도 allowed_users와 매칭되지 않아 전원 로그인 거부가 된다
        # — 기본값으로 되돌린다(빈 값 자체는 _warn_blank_process_env가 경고로 알림).
        return value.strip() or "email"

    def auth_summary(self) -> str:
        """기동 로그용 인증 설정 요약 — 시크릿(client_secret, 비밀번호 등)은 넣지 않는다."""
        if self.auth_mode != "sso":
            return f"auth_mode={self.auth_mode}"
        return (
            f"auth_mode=sso sso_flow_mode={self.sso_flow_mode} "
            f"issuer={self.sso_issuer_url or '(미설정 — SSO 비활성)'} "
            f"client_id={'설정됨' if self.sso_client_id else '없음'} "
            f"user_id_claim={self.sso_user_id_claim} "
            f"allow_local_login={self.sso_allow_local_login}"
        )

    @model_validator(mode="after")
    def _resolve_database_url(self) -> "Settings":
        """DATABASE_URL 우선 -> DB_HOST 조합(PostgreSQL) -> SQLite 폴백.

        PDEP처럼 host/port/name은 ConfigMap, user/password는 Secret으로 나눠
        주입하는 배포 환경과, DSN 하나로 충분한 로컬 개발을 동시에 지원한다.
        """
        if not self.database_url:
            if self.db_host:
                user = urllib.parse.quote_plus(self.db_user)
                password = urllib.parse.quote_plus(self.db_password)
                self.database_url = (
                    f"postgresql+asyncpg://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"
                )
            else:
                self.database_url = "sqlite+aiosqlite:///./eflms.db"
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sso_admin_allowlist_list(self) -> list[str]:
        return [item.strip() for item in self.sso_admin_allowlist.split(",") if item.strip()]

    @property
    def sso_ca_bundle_resolved_path(self) -> Path | None:
        if not self.sso_ca_bundle_path:
            return None
        path = Path(self.sso_ca_bundle_path)
        return path if path.is_absolute() else BACKEND_DIR / path


@lru_cache
def get_settings() -> Settings:
    _warn_blank_process_env()
    return Settings()
