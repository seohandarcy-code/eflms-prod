import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import admin, equipment, health
from app.core.config import get_settings
from app.db import seed
from app.db.session import async_session_factory
from app.equipment_types.registry import registered_codes
from app.services.dataset_service import is_type_empty

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 실제로 적용된 인증 설정을 기동 때마다 한 줄로 남긴다 — ConfigMap/.env 값이
    # 파드·프로세스에 정말 반영됐는지 로그만 보고 바로 확인하기 위함(a-ims-prod가
    # SSO_FLOW_MODE 미반영 원인을 찾느라 며칠 쓴 문제, backend/app/auth/SSO_MODES.md).
    # 앱 로거엔 INFO 핸들러가 없어서, uvicorn 실행 시 항상 출력되는 uvicorn.error 로거를 쓴다.
    logging.getLogger("uvicorn.error").info("EFLMS auth config: %s", settings.auth_summary())
    if settings.auto_seed_if_empty:
        # 설비유형별로 비어 있는 유형만 채운다 — EF1 실데이터가 있어도 빈 유형은 mock으로 채워짐.
        async with async_session_factory() as session:
            for ef_code in registered_codes():
                if await is_type_empty(session, ef_code):
                    await seed.seed_type(session, ef_code, rows=30, reset=False)
                    await session.commit()
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
