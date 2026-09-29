import urllib.parse
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
