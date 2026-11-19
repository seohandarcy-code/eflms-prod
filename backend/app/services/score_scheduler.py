"""서버 자동 점수 갱신 (Stage 21-1b, 2026-11-19).

서버(lifespan)가 켜지면 백그라운드 작업 하나가 돈다 — 시작 직후 한 번, 그 뒤 SCORE_REFRESH_CHECK_MINUTES(기본 10분)마다
`tick()`으로 확인한다:

1. DB가 최신 버전이 아니면(alembic upgrade head 전) 갱신하지 않고 로그에 안내만 남긴다.
2. 점수 기준일이 오늘(한국 시간)보다 이전인 설비가 있으면 오늘 기준으로 갱신한다(score_refresh_service — 점수만,
   진단 데이터 그대로). 실행 기록 trigger는 첫 확인이면 `startup`, 그 뒤는 `daily`.
3. 이미 오늘 기준이면 아무것도 하지 않는다(실행 기록도 없음) — 재시작해도 하루 한 번만 계산한다.

다른 데이터 작업이 진행 중이면 이번엔 건너뛰고 다음 확인 때 다시 본다. 갱신이 실패하면 이전 점수를 유지하고
RETRY_AFTER(1시간) 뒤 다시 시도한다. 서버가 여러 대여도 데이터 작업 잠금 때문에 한 대만 갱신한다.
테스트는 lifespan을 돌리지 않으므로 이 작업이 시작되지 않는다 — tick()을 날짜를 넣어 직접 시험한다.
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.clock import now_kst_naive, today_kst
from app.equipment_types.registry import all_modules, registered_codes
from app.services.schema_check import schema_status
from app.services.score_refresh_service import refresh_scores

log = logging.getLogger("uvicorn.error")  # uvicorn 실행 때 항상 출력되는 로거(main.py의 인증 설정 로그와 같음)

RETRY_AFTER = timedelta(hours=1)


@dataclass
class SchedulerState:
    started: bool = False  # 첫 tick이 끝났는지(첫 실행 기록은 startup)
    retry_at: datetime | None = None  # 실패 후 다음 시도 시각
    last_outcome: str | None = None


async def stale_count(factory: async_sessionmaker, today: date) -> int:
    """점수 기준일(계산 결과 테이블 today)이 오늘보다 이전인 설비 수."""
    total = 0
    async with factory() as session:
        for module in all_modules():
            model = module.SCORE_DETAIL_MODEL
            total += await session.scalar(select(func.count()).select_from(model).where(model.today < today)) or 0
    return total


async def tick(factory: async_sessionmaker, state: SchedulerState, today: date, now: datetime | None = None) -> str:
    """한 번 확인한다. 결과: schema / waiting / fresh / busy / success / partial / failed / unavailable."""
    now = now or now_kst_naive()
    trigger = "daily" if state.started else "startup"
    state.started = True

    status = await schema_status(factory.kw["bind"])
    if not status.ok:
        if state.last_outcome != "schema":  # 같은 안내를 10분마다 반복하지 않는다
            log.warning("EFLMS score refresh: DB 업그레이드 필요(현재 %s / 최신 %s) — 갱신 안 함", status.current, status.head)
        state.last_outcome = "schema"
        return "schema"
    if state.retry_at and now < state.retry_at:
        return "waiting"

    stale = await stale_count(factory, today)
    if stale == 0:
        if trigger == "startup" or state.last_outcome not in (None, "fresh"):
            log.info("EFLMS score refresh: %s — 점수 기준일이 이미 %s라 건너뜀", trigger, today)
        state.last_outcome = "fresh"
        state.retry_at = None
        return "fresh"

    result = await refresh_scores(factory, registered_codes(), today, trigger=trigger, requested_by="server")
    state.last_outcome = result.status
    if result.status == "busy":
        log.info("EFLMS score refresh: %s — %s", trigger, result.message)
    elif result.status in ("success",):
        state.retry_at = None
        log.info("EFLMS score refresh: %s — %d대, 기준일 %s, success", trigger, result.equipment_count, today)
    else:
        state.retry_at = now + RETRY_AFTER
        failed = ", ".join(f"{t.ef_code}({t.error})" for t in result.types if t.error) or result.message
        log.warning("EFLMS score refresh: %s — %s, 1시간 뒤 다시 시도: %s", trigger, result.status, failed)
    return result.status


async def run_forever(factory: async_sessionmaker, interval_minutes: int) -> None:
    """서버가 켜져 있는 동안 도는 작업 — lifespan이 만들고 서버가 꺼질 때 취소한다."""
    state = SchedulerState()
    while True:
        try:
            await tick(factory, state, today_kst())
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — 확인 자체가 실패해도 작업은 계속 돈다
            log.exception("EFLMS score refresh: 확인 중 오류")
            state.retry_at = now_kst_naive() + RETRY_AFTER
        await asyncio.sleep(max(1, interval_minutes) * 60)
