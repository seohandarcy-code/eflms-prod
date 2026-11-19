"""DB 스키마 버전 확인 (Stage 21-1b, 2026-11-19).

DB의 alembic_version과 코드의 최신 마이그레이션(head)을 비교한다. 예전 DB(마이그레이션 전)에 지금 코드를
붙이면 새 테이블(data_job_lock·score_refresh_run 등)이 없어 갱신·임포트가 실패하므로, 자동 갱신과 관리자
화면이 먼저 이것으로 확인하고 "alembic upgrade head" 안내를 보여 준다.

alembic_version 테이블이 없는 DB(테스트처럼 create_all로 만든 DB)는 "확인 불가"로 보고 막지 않는다.
"""
from dataclasses import dataclass
from functools import lru_cache

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import BACKEND_DIR

UPGRADE_HINT = "DB가 최신 버전이 아닙니다 — backend에서 `python -m alembic upgrade head` 실행 후 다시 시도해 주세요."


@dataclass
class SchemaStatus:
    current: str | None
    head: str
    known: bool  # alembic_version을 읽었는지

    @property
    def ok(self) -> bool:
        return not self.known or self.current == self.head

    def as_dict(self) -> dict:
        return {"current": self.current, "head": self.head, "ok": self.ok, "known": self.known}


@lru_cache
def code_head() -> str:
    cfg = Config()
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(cfg).get_current_head()


async def schema_status(bind) -> SchemaStatus:
    """bind = AsyncEngine 또는 AsyncSession."""
    head = code_head()
    # 요청 세션의 트랜잭션을 더럽히지 않게 엔진에서 따로 연결을 연다
    engine = bind.bind if isinstance(bind, AsyncSession) else bind
    try:
        async with engine.connect() as conn:
            current = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
    except Exception:  # noqa: BLE001 — 테이블이 없으면 확인 불가(create_all DB)
        return SchemaStatus(current=None, head=head, known=False)
    return SchemaStatus(current=current, head=head, known=True)
