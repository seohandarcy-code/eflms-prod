"""점수 재계산 CLI (2026-11-19).

    .venv/Scripts/python -m app.db.recalculate --ef-code all
    .venv/Scripts/python -m app.db.recalculate --ef-code EF2

저장된 입력값과 계산 기준일(load_inputs)로 지금 계산 규칙을 다시 돌려 점수·감점을 덮어쓴다. 입력값은
바뀌지 않는다. 계산 규칙이 바뀐 뒤(예: 2026-11-19 감점 소수 계산 — 마이그레이션 f3b8d1e6a9c4 다음)
기존 설비 점수를 새 규칙으로 맞출 때 쓴다. 유형마다 한 트랜잭션이고, 실패한 유형은 반영되지 않는다.
"""
import argparse
import asyncio
import sys

from app.db.session import async_session_factory
from app.equipment_types.registry import get_module, resolve_codes
from app.services.reference_service import recalculate_type


async def run(ef_code: str) -> bool:
    ok = True
    for code in resolve_codes(ef_code):
        module = get_module(code)
        async with async_session_factory() as session:
            try:
                count = await recalculate_type(session, module)
                await session.commit()
            except Exception as exc:  # noqa: BLE001 — 유형별로 실패를 알리고 다음 유형으로
                await session.rollback()
                print(f"[실패] {code} 재계산 중단(반영 안 됨): {exc}")
                ok = False
                continue
        print(f"[완료] {code} 설비 {count}건 점수 재계산")
    return ok


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="EFLMS 점수 재계산(저장된 입력값·계산 기준일 기준)")
    parser.add_argument("--ef-code", required=True, help="설비유형 코드 (예: EF2) 또는 all")
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(run(args.ef_code)) else 1)


if __name__ == "__main__":
    main()
