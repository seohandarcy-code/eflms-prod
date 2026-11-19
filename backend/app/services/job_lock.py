"""데이터 작업 잠금 (2026-11-19, Stage 21-1).

점수 갱신·실제 반영 임포트(웹·명령, 관리자 행 편집 포함)·참고표 넣기/리셋이 동시에 돌면, 갱신이 옛 입력으로
계산한 점수가 방금 임포트한 점수를 덮어쓸 수 있다. 그래서 이 작업들은 `data_job_lock`의 "data" 행을 잡고 돈다.

- 잠금은 작업 트랜잭션과 **별도의 짧은 트랜잭션**으로 잡고 푼다(작업이 rollback돼도 잠금 기록은 정리된다).
  같은 DB를 쓰도록 작업 세션의 엔진(session.bind)으로 새 세션을 만든다.
- 비정상 종료로 남은 잠금은 expires_at(기본 30분)이 지나면 다음 작업이 지우고 잡는다.
- 검증만 하는 요청(--check, 화면의 검증)은 잠그지 않는다. 개발용 seed/reset 명령도 잠그지 않는다.
"""
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.models import DataJobLock

LOCK_NAME = "data"
LOCK_TTL = timedelta(minutes=30)


class DataJobBusyError(RuntimeError):
    """다른 데이터 작업이 잠금을 잡고 있다."""

    def __init__(self, holder: str, acquired_at: datetime | None):
        self.holder = holder
        self.acquired_at = acquired_at
        when = f" — {acquired_at:%Y-%m-%d %H:%M} 시작" if acquired_at else ""
        super().__init__(f"다른 데이터 작업({holder})이 진행 중입니다{when}. 잠시 후 다시 시도해 주세요.")


def factory_for(bind: AsyncEngine | AsyncSession) -> async_sessionmaker:
    """작업 세션(또는 엔진)과 같은 DB를 쓰는 새 세션 팩토리."""
    engine = bind.bind if isinstance(bind, AsyncSession) else bind
    return async_sessionmaker(engine, expire_on_commit=False)


async def acquire(bind, holder: str, now: datetime | None = None) -> str:
    """잠금을 잡고 토큰을 돌려준다. 이미 잡혀 있으면(만료 전) DataJobBusyError."""
    now = now or datetime.now()
    token = uuid.uuid4().hex
    async with factory_for(bind)() as session:
        await session.execute(delete(DataJobLock).where(DataJobLock.name == LOCK_NAME, DataJobLock.expires_at < now))
        session.add(DataJobLock(name=LOCK_NAME, holder=holder, token=token, acquired_at=now, expires_at=now + LOCK_TTL))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            current = await session.get(DataJobLock, LOCK_NAME)
            raise DataJobBusyError(current.holder if current else "알 수 없음", current.acquired_at if current else None)
    return token


async def release(bind, token: str) -> None:
    async with factory_for(bind)() as session:
        await session.execute(delete(DataJobLock).where(DataJobLock.name == LOCK_NAME, DataJobLock.token == token))
        await session.commit()


@asynccontextmanager
async def data_job(bind, holder: str):
    """`async with data_job(session, "임포트 EF4"):` — 블록 동안 잠금을 잡는다."""
    token = await acquire(bind, holder)
    try:
        yield
    finally:
        await release(bind, token)


async def current_holder(bind) -> DataJobLock | None:
    async with factory_for(bind)() as session:
        lock = (await session.execute(select(DataJobLock).where(DataJobLock.name == LOCK_NAME))).scalar_one_or_none()
        if lock is not None and lock.expires_at < datetime.now():
            return None
        return lock
