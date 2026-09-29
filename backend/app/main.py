import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import admin, equipment, health
from app.core.config import get_settings
from app.db import seed
from app.db.session import async_session_factory

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_seed_if_empty:
        async with async_session_factory() as session:
            if await seed.is_empty(session):
                await seed.main(rows=30, do_reset=False)
    yield


app = FastAPI(title="EFLMS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SSO 로그인 리다이렉트가 왕복하는 짧은 시간 동안만 쓰이는 OAuth state/nonce 저장용
# (로그인 자체의 세션이 아님 — 그건 AdminAuthStore가 별도 관리). 로컬 dev에서
# SESSION_SECRET_KEY를 비워두면 기동마다 임의 값을 생성해도 문제없다.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key or secrets.token_urlsafe(32),
    https_only=settings.session_cookie_secure,
)

app.include_router(health.router)
app.include_router(equipment.router)
app.include_router(admin.router)
