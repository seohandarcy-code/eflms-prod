"""사내 입력파일 CLI 임포트 진입점. 웹 서버 프로세스와 분리해서 수동/배치 실행한다.

    .venv/Scripts/python -m app.db.import_data --file sample_data/sample_valid.dat --ef-code EF1
"""
import argparse
import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone

from app.db.session import async_session_factory
from app.services.import_service import import_file

logger = logging.getLogger("eflms.import")
logging.basicConfig(level=logging.INFO, format="%(message)s")


async def run(path: str, ef_code: str) -> None:
    async with async_session_factory() as session:
        result = await import_file(path, ef_code, session)

    logger.info(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "file": result.file_path,
                "ef_code": result.ef_code,
                "total_rows": result.total_rows,
                "imported_rows": result.imported_rows,
                "ok": result.ok,
                "file_errors": result.file_errors,
                "row_errors": [asdict(e) for e in result.row_errors],
                "unknown_columns": result.unknown_columns,
            },
            ensure_ascii=False,
            default=str,
        )
    )

    if result.ok:
        print(f"[완료] {result.imported_rows}/{result.total_rows}건 임포트 성공")
        if result.unknown_columns:
            print(f"  미등록 컬럼 {len(result.unknown_columns)}개 발견(equipment_extra_attribute에 보관됨): {', '.join(result.unknown_columns)}")
    else:
        print("[실패] 검증 오류로 임포트를 중단함(0건 반영)")
        for fe in result.file_errors:
            print(f"  - {fe}")
        for e in result.row_errors:
            print(f"  - {e.row_number}행 {e.column}: '{e.raw_value}' ({e.reason})")


def main() -> None:
    parser = argparse.ArgumentParser(description="EFLMS 사내 입력파일 임포트")
    parser.add_argument("--file", required=True, help="임포트할 .dat 파일 경로")
    parser.add_argument("--ef-code", required=True, help="설비유형 코드 (예: EF1)")
    args = parser.parse_args()
    asyncio.run(run(args.file, args.ef_code))


if __name__ == "__main__":
    main()
