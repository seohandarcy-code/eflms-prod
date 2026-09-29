from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import equipment, health
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

app.include_router(health.router)
app.include_router(equipment.router)
