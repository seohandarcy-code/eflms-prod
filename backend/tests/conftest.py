import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db import models  # noqa: F401  (registers all models on Base.metadata)
from app.db.session import get_session
from app.equipment_types.ef1_transformer import calculate, generate_input_row
from app.main import app
from app.services.ingest import ingest_row


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    # DATABASE_URL이 설정돼 있으면 그 값을 존중한다(예: 로컬 PostgreSQL 대상 검증).
    # 비어있으면 기존과 동일하게 테스트별 임시 SQLite 파일을 새로 만든다.
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        engine = create_async_engine(database_url)
        async with engine.begin() as conn:
            # 테스트마다 깨끗한 상태로 시작하기 위해 스키마를 매번 새로 만든다
            # (SQLite 임시 파일 방식과 동일한 격리 수준을 공유 DB에서도 재현).
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    else:
        db_path = tmp_path / "test.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory

    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory):
    async def _override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session

    async with session_factory() as session:
        for _ in range(3):
            row = calculate(generate_input_row())
            await ingest_row(row, session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
