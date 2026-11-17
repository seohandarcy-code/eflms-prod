"""참고표 리셋 CLI (Stage 15-0).

    .venv/Scripts/python -m app.db.reset_reference --ef-code EF7 --table discharge_history
    .venv/Scripts/python -m app.db.reset_reference --ef-code EF7 --table all

참고표를 비우고 그 유형의 설비 점수를 같은 트랜잭션 안에서 다시 계산한다(빈 표는 원본 수식대로 0으로 계산).
설비 데이터는 지우지 않는다 — 설비 리셋은 app.db.reset. 목업 참고표를 다시 넣으려면 리셋 후
`python -m app.db.seed --ef-code EF7 --rows 0`(비어 있는 참고표에만 목업을 넣는다).
"""
import argparse
import asyncio
import sys

from app.db.session import async_session_factory
from app.services.reference_service import reset_reference


async def run(ef_code: str, table: str) -> bool:
    async with async_session_factory() as session:
        result = await reset_reference(session, ef_code, table)
    if not result.ok:
        print("[실패] 참고표 리셋을 중단함")
        for e in result.errors:
            print(f"  - {e}")
        return False
    for name, count in result.deleted.items():
        print(f"[완료] {ef_code} 참고표 {name} {count}행 삭제")
    print(f"  {ef_code} 설비 {result.recalculated}건 점수 재계산")
    for w in result.warnings:
        print(f"  [경고] {w}")
    return True


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="EFLMS 참고표 리셋")
    parser.add_argument("--ef-code", required=True, help="설비유형 코드 (예: EF7)")
    parser.add_argument("--table", required=True, help="참고표 이름 또는 all")
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(run(args.ef_code, args.table)) else 1)


if __name__ == "__main__":
    main()
