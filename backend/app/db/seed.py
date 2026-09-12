"""EF1 mock 데이터 시드 스크립트.

    python -m app.db.seed --rows 30 --reset
"""
import argparse
import asyncio

from sqlalchemy import delete

from app.db.models import (
    DesignAttribute,
    DgaReading,
    DielectricTest,
    Equipment,
    EquipmentType,
    FuranReading,
    LoadCondition,
    OilTest,
    PeriodicInspection,
    ScoreSnapshot,
    TransformerScoreDetail,
)
from app.db.session import async_session_factory
from app.equipment_types.ef1_transformer import calculate, generate_input_row
from app.services.ingest import ingest_row

# 자식 테이블 -> 부모 테이블 순서로 삭제 (FK 제약 위반 방지)
_RESET_ORDER = [
    TransformerScoreDetail,
    ScoreSnapshot,
    DesignAttribute,
    PeriodicInspection,
    LoadCondition,
    OilTest,
    DielectricTest,
    FuranReading,
    DgaReading,
    Equipment,
    EquipmentType,
]


async def _reset(session) -> None:
    for model in _RESET_ORDER:
        await session.execute(delete(model))
    await session.commit()


async def main(rows: int, do_reset: bool) -> None:
    async with async_session_factory() as session:
        if do_reset:
            await _reset(session)
        for _ in range(rows):
            full_row = calculate(generate_input_row())
            await ingest_row(full_row, session)
    print(f"[완료] EF1 mock 데이터 {rows}건 시드 적재")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EF1(변압기) mock 데이터 시드")
    parser.add_argument("--rows", type=int, default=30)
    parser.add_argument("--reset", action="store_true", help="기존 데이터를 먼저 삭제")
    args = parser.parse_args()
    asyncio.run(main(args.rows, args.reset))
