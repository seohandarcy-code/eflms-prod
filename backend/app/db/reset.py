"""설비유형 단위 데이터 리셋 CLI (Stage 8-2).

    python -m app.db.reset --ef-code EF2     # EF2 설비와 딸린 데이터만 삭제
    python -m app.db.reset --ef-code all     # 등록된 모든 유형 삭제

다른 유형의 데이터와 equipment_type(마스터), allowed_users(접근 권한)는 건드리지 않는다.
"""
import argparse
import asyncio

from app.db.session import async_session_factory
from app.equipment_types.registry import UnknownEquipmentTypeError, resolve_codes
from app.services.dataset_service import reset_type


async def main(ef_code: str) -> None:
    codes = resolve_codes(ef_code)
    async with async_session_factory() as session:
        for code in codes:
            removed = await reset_type(session, code)
            await session.commit()
            print(f"[완료] {code} 설비 {removed}건 삭제")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="설비유형 단위 데이터 리셋")
    parser.add_argument("--ef-code", required=True, help="설비유형 코드(예: EF2) 또는 all")
    args = parser.parse_args()
    try:
        resolve_codes(args.ef_code)
    except UnknownEquipmentTypeError as exc:
        parser.error(str(exc))
    asyncio.run(main(args.ef_code))
