"""설비유형별 mock 데이터 시드 스크립트.

    python -m app.db.seed --rows 30                 # 등록된 모든 유형에 각 30건 추가
    python -m app.db.seed --ef-code EF1 --rows 30 --reset   # EF1만 지우고 30건 새로 생성

`--reset`은 지정한 유형만 지운다 — 다른 유형의 데이터(예: 이미 넣은 실데이터)는 그대로 남는다
(Stage 8-2, app/services/dataset_service.py).
"""
import argparse
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.equipment_types.registry import UnknownEquipmentTypeError, get_module, resolve_codes
from app.services.dataset_service import reset_type
from app.services.ingest import ingest_row


async def seed_type(session: AsyncSession, ef_code: str, rows: int, reset: bool) -> None:
    """한 유형을 (선택적으로 리셋 후) mock rows건 적재한다. commit하지 않는다."""
    module = get_module(ef_code)
    if reset:
        await reset_type(session, ef_code)
    for _ in range(rows):
        await ingest_row(module.calculate(module.generate_input_row()), session)


async def main(ef_code: str, rows: int, do_reset: bool) -> None:
    codes = resolve_codes(ef_code)
    async with async_session_factory() as session:
        # 유형별로 커밋 — 한 유형이 실패해도 앞서 끝난 유형은 남고, 실패한 유형은 통째로 rollback.
        for code in codes:
            await seed_type(session, code, rows, do_reset)
            await session.commit()
            print(f"[완료] {code} mock 데이터 {rows}건 시드 적재" + (" (기존 데이터 리셋 후)" if do_reset else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="설비유형별 mock 데이터 시드")
    parser.add_argument("--ef-code", default="all", help="설비유형 코드(예: EF1) 또는 all(기본값)")
    parser.add_argument("--rows", type=int, default=30, help="유형별 생성 건수")
    parser.add_argument("--reset", action="store_true", help="지정한 유형의 기존 데이터를 먼저 삭제")
    args = parser.parse_args()
    try:
        resolve_codes(args.ef_code)
    except UnknownEquipmentTypeError as exc:
        parser.error(str(exc))
    asyncio.run(main(args.ef_code, args.rows, args.reset))
