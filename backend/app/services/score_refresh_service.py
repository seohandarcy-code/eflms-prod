"""점수 갱신 (2026-11-19, Stage 21-1).

저장된 입력값(load_inputs)으로 계산 기준일만 바꿔 같은 공식으로 다시 계산하고 **점수 테이블만** 다시 쓴다
(ingest.save_scores — 계산 결과 테이블 + score_snapshot). 입력 테이블은 건드리지 않으므로 '최근 진단일'은
마지막 임포트·행 편집 날짜로 남는다. 경과연수·부품 노화처럼 날짜에 따라 바뀌는 감점이 오늘 기준으로 맞춰진다.

- as_of=None이면 설비마다 저장된 기준일 그대로 다시 계산한다(계산 규칙이 바뀐 뒤 재계산 — Stage 20 용도).
- 유형마다 한 트랜잭션: 한 유형이 실패하면 그 유형만 rollback되어 이전 점수가 남고, 나머지는 계속한다.
- 실행 한 번 = score_refresh_run 한 행(상태·유형별 건수·오류). 데이터 작업 잠금(job_lock)을 잡고 돈다.
- 부르는 곳: 명령 `python -m app.db.recalculate`(정기 실행 CronJob 포함), 관리자 API `/api/admin/score-refresh`.
"""
import json
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.clock import now_kst_naive
from app.db.models import Equipment, ScoreRefreshRun
from app.equipment_types.registry import get_module
from app.services import job_lock
from app.services.ingest import save_scores
from app.services.reference_data import calc_options

HISTORY_LIMIT = 20


@dataclass
class TypeRefreshResult:
    ef_code: str
    count: int = 0
    error: str | None = None


@dataclass
class RefreshResult:
    run_id: int | None
    status: str  # success / partial / failed / busy(다른 작업 진행 중) / unavailable(DB 업그레이드 필요)
    as_of: date | None
    types: list[TypeRefreshResult] = field(default_factory=list)
    message: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "success"

    @property
    def equipment_count(self) -> int:
        return sum(t.count for t in self.types)


async def _refresh_type(factory: async_sessionmaker, code: str, as_of: date | None) -> TypeRefreshResult:
    module = get_module(code)
    out = TypeRefreshResult(ef_code=code)
    async with factory() as session:
        try:
            options = await calc_options(session, module)
            ids = (
                await session.execute(select(Equipment.equipment_id).where(Equipment.ef_code == code))
            ).scalars().all()
            for eq_id in ids:
                loaded = await module.load_inputs(session, eq_id)
                if loaded is None:
                    continue
                input_row, stored_as_of = loaded
                calc = module.calculate(input_row, as_of=as_of or stored_as_of, **options)
                await save_scores(calc, eq_id, session)
                out.count += 1
            await session.commit()
        except Exception as exc:  # noqa: BLE001 — 유형별로 실패를 기록하고 다음 유형으로
            await session.rollback()
            out.count = 0
            out.error = f"{type(exc).__name__}: {exc}"
    return out


async def refresh_scores(
    factory: async_sessionmaker,
    ef_codes: list[str],
    as_of: date | None,
    trigger: str,
    requested_by: str | None = None,
) -> RefreshResult:
    """점수를 다시 계산해 저장한다. 다른 데이터 작업이 진행 중이면 status="busy"(실행 기록 없음)."""
    engine = factory.kw["bind"]
    try:
        token = await job_lock.acquire(engine, f"점수 갱신({trigger})")
    except job_lock.DataJobBusyError as exc:
        return RefreshResult(run_id=None, status="busy", as_of=as_of, message=str(exc))
    except job_lock.DataJobUnavailableError as exc:  # 마이그레이션 전 DB
        return RefreshResult(run_id=None, status="unavailable", as_of=as_of, message=str(exc))
    try:
        async with factory() as session:
            run = ScoreRefreshRun(
                started_at=now_kst_naive(), status="running", trigger=trigger, requested_by=requested_by, as_of=as_of
            )
            session.add(run)
            await session.commit()
            run_id = run.run_id

        types = [await _refresh_type(factory, code, as_of) for code in ef_codes]
        failed = [t for t in types if t.error]
        status = "success" if not failed else ("failed" if len(failed) == len(types) else "partial")

        async with factory() as session:
            run = await session.get(ScoreRefreshRun, run_id)
            run.finished_at = now_kst_naive()
            run.status = status
            run.equipment_count = sum(t.count for t in types)
            run.summary = json.dumps(
                [{"ef_code": t.ef_code, "count": t.count, "error": t.error} for t in types], ensure_ascii=False
            )
            await session.commit()
        return RefreshResult(run_id=run_id, status=status, as_of=as_of, types=types)
    finally:
        await job_lock.release(engine, token)


def run_to_dict(run: ScoreRefreshRun) -> dict:
    return {
        "run_id": run.run_id,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "status": run.status,
        "trigger": run.trigger,
        "requested_by": run.requested_by,
        "as_of": run.as_of,
        "equipment_count": run.equipment_count,
        "types": json.loads(run.summary) if run.summary else [],
    }


async def recent_runs(factory: async_sessionmaker, limit: int = HISTORY_LIMIT) -> list[dict]:
    async with factory() as session:
        stmt = select(ScoreRefreshRun).order_by(ScoreRefreshRun.run_id.desc()).limit(limit)
        return [run_to_dict(r) for r in (await session.execute(stmt)).scalars()]
