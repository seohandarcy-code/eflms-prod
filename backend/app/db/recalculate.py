"""점수 재계산·갱신 CLI (2026-11-19, Stage 20 / Stage 21-1).

    .venv/Scripts/python -m app.db.recalculate --ef-code all --as-of today --trigger schedule   # 매일 정기 갱신
    .venv/Scripts/python -m app.db.recalculate --ef-code all --as-of 2027-11-19                # 특정 기준일
    .venv/Scripts/python -m app.db.recalculate --ef-code all                                   # 저장된 기준일 그대로

저장된 입력값으로 다시 계산해 **점수 테이블만** 덮어쓴다(입력 테이블·최근 진단일은 그대로). 기준일은
`today`면 한국 시간 오늘(app/core/clock.py), 날짜면 그날, 생략하면 설비마다 저장된 기준일(계산 규칙이 바뀐 뒤
재계산할 때 — 예: 마이그레이션 f3b8d1e6a9c4 다음). 유형마다 한 트랜잭션이고 실패한 유형은 반영되지 않는다.
실행 기록은 score_refresh_run, 다른 데이터 작업이 진행 중이면 실행하지 않고 종료 코드 1.
"""
import argparse
import asyncio
import sys
from datetime import date

from app.core.clock import today_kst
from app.db.session import async_session_factory
from app.equipment_types.registry import resolve_codes
from app.services.score_refresh_service import refresh_scores

TRIGGERS = ("cli", "schedule")  # 서버 자동 갱신은 startup/daily(app/services/score_scheduler.py)


def parse_as_of(value: str | None) -> date | None:
    if value is None:
        return None
    if value.lower() == "today":
        return today_kst()
    return date.fromisoformat(value)


async def run(ef_code: str, as_of: date | None = None, trigger: str = "cli") -> bool:
    result = await refresh_scores(async_session_factory, resolve_codes(ef_code), as_of, trigger, requested_by=trigger)
    if result.status in ("busy", "unavailable"):
        print(f"[중단] {result.message}")
        return False
    basis = f"기준일 {as_of}" if as_of else "저장된 기준일"
    for t in result.types:
        if t.error:
            print(f"[실패] {t.ef_code} 재계산 중단(반영 안 됨): {t.error}")
        else:
            print(f"[완료] {t.ef_code} 설비 {t.count}건 점수 재계산({basis})")
    print(f"실행 기록 #{result.run_id} — {result.status}")
    return result.ok


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="EFLMS 점수 재계산·갱신(저장된 입력값 기준, 점수 테이블만)")
    parser.add_argument("--ef-code", required=True, help="설비유형 코드 (예: EF2) 또는 all")
    parser.add_argument("--as-of", default=None, help="계산 기준일: today(한국 시간 오늘) 또는 YYYY-MM-DD. 생략하면 저장된 기준일")
    parser.add_argument("--trigger", choices=TRIGGERS, default="cli", help="실행 기록에 남길 구분(정기 실행은 schedule)")
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(run(args.ef_code, parse_as_of(args.as_of), args.trigger)) else 1)


if __name__ == "__main__":
    main()
