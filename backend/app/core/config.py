import urllib.parse
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


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
    auth_mode: str = "none"
    auto_seed_if_empty: bool = False
    admin_bootstrap_password: str = ""

    # AUTH_MODE=sso 전용 — Stage 6, docs/ARCHITECTURE.md "인증" 참고.
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
    return Settings()
