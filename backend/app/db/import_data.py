"""사내 입력파일 CLI 임포트 진입점. 웹 서버 프로세스와 분리해서 수동/배치 실행한다.

    .venv/Scripts/python -m app.db.import_data --file sample_data/ef1/sample_valid.dat --ef-code EF1
    .venv/Scripts/python -m app.db.import_data --file <실데이터.dat> --ef-code EF1 --replace
    .venv/Scripts/python -m app.db.import_data --file <실데이터.dat> --ef-code EF1 --check   # DB 미반영 점검

--replace: 같은 트랜잭션 안에서 해당 유형의 기존 데이터(mock 포함)를 지우고 파일 내용으로
교체한다. 다른 설비유형 데이터는 그대로. 빼면 추가/갱신(upsert)만 한다.
--check: 검증 + 계산까지만 하고 DB에는 아무것도 쓰지 않는다 — 새 PC에서 실파일을 먼저 확인하는 용도.
"""
import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict
from datetime import datetime, timezone

from app.db.session import async_session_factory
from app.services.import_service import import_file

logger = logging.getLogger("eflms.import")
logging.basicConfig(level=logging.INFO, format="%(message)s")


async def run(path: str, ef_code: str, replace: bool, check: bool = False) -> bool:
    async with async_session_factory() as session:
        result = await import_file(path, ef_code, session, replace=replace, dry_run=check)

    logger.info(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "file": result.file_path,
                "ef_code": result.ef_code,
                "total_rows": result.total_rows,
                "imported_rows": result.imported_rows,
                "replace": result.replace,
                "dry_run": result.dry_run,
                "replaced_rows": result.replaced_rows,
                "ok": result.ok,
                "file_errors": result.file_errors,
                "row_errors": [asdict(e) for e in result.row_errors],
                "unknown_columns": result.unknown_columns,
                "ignored_columns": result.ignored_columns,
                "na_values": result.na_values,
            },
            ensure_ascii=False,
            default=str,
        )
    )

    if result.ok and result.dry_run:
        print(f"[점검 통과] {result.total_rows}건 검증·계산 성공 - DB에는 반영하지 않음(--check)")
        if result.replace:
            print(f"  --check 없이 실행하면 기존 {result.ef_code} 설비 {result.existing_rows}건을 지우고 교체함(다른 유형은 그대로)")
        else:
            print(f"  현재 {result.ef_code} 설비 {result.existing_rows}건 - --replace 없이 실행하면 같은 설비는 갱신, 새 설비는 추가")
        if result.unknown_columns:
            print(f"  미등록 컬럼 {len(result.unknown_columns)}개(equipment_extra_attribute에 보관 예정): {', '.join(result.unknown_columns)}")
    elif result.ok:
        print(f"[완료] {result.imported_rows}/{result.total_rows}건 임포트 성공")
        if result.replace:
            print(f"  --replace: 기존 {result.ef_code} 설비 {result.replaced_rows}건을 지우고 교체함(다른 유형은 그대로)")
        if result.unknown_columns:
            print(f"  미등록 컬럼 {len(result.unknown_columns)}개 발견(equipment_extra_attribute에 보관됨): {', '.join(result.unknown_columns)}")
    else:
        print("[실패] 점검 실패" if result.dry_run else "[실패] 임포트를 중단함(0건 반영)")
        for fe in result.file_errors:
            print(f"  - {fe}")
        for e in result.row_errors:
            print(f"  - {e.row_number}행 {e.column}: '{e.raw_value}' ({e.reason})")
    if result.ignored_columns:
        print(f"  사용 안 하는 컬럼(무시, 저장 안 함): {', '.join(result.ignored_columns)}")
    if result.ok and result.na_values:
        detail = ", ".join(f"{name} {count}건" for name, count in result.na_values.items())
        print(f"  N/A {sum(result.na_values.values())}칸 → 값 없음(null)으로 저장, 해당 항목 감점 0: {detail}")
    return result.ok


def main() -> None:
    # 콘솔이 CP949이거나 출력을 파일로 돌리면 인코딩 못 하는 문자(파일 원문 값 등)에서 print가 죽는다.
    # 임포트는 이미 commit된 뒤라 "성공했는데 실패 종료"가 되므로, 못 찍는 문자는 \uXXXX 형태로 대신 찍는다.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="EFLMS 사내 입력파일 임포트")
    parser.add_argument("--file", required=True, help="임포트할 .dat 파일 경로")
    parser.add_argument("--ef-code", required=True, help="설비유형 코드 (예: EF1)")
    parser.add_argument("--replace", action="store_true", help="해당 유형의 기존 데이터를 지우고 파일 내용으로 교체")
    parser.add_argument("--check", action="store_true", help="검증·계산만 하고 DB에는 반영하지 않음")
    args = parser.parse_args()
    ok = asyncio.run(run(args.file, args.ef_code, args.replace, args.check))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
