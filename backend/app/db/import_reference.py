"""참고표 dat 임포트 CLI (Stage 15-0). 설비 임포트(app.db.import_data)와 같은 방식으로 수동/배치 실행한다.

    .venv/Scripts/python -m app.db.import_reference --ef-code EF7 --table discharge_history --file <방전이력.dat>
    .venv/Scripts/python -m app.db.import_reference --ef-code EF7 --table temp_decay_coef --file <온도감소계수.dat> --replace
    .venv/Scripts/python -m app.db.import_reference --ef-code EF7 --table discharge_history --file <파일> --check

기본: 같은 행(표의 key — 방전이력은 사업장+일자, 온도감소계수는 year)은 갱신, 새 행은 추가.
--replace: 같은 트랜잭션 안에서 그 참고표를 비우고 파일 내용으로 교체.
--check: 검증만 하고 DB에는 아무것도 쓰지 않는다.
반영하면 그 유형의 설비 점수를 같은 트랜잭션 안에서 전부 다시 계산한다(app/services/reference_service.py).
"""
import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict
from datetime import datetime, timezone

from app.db.session import async_session_factory
from app.services.reference_service import import_reference_file

logger = logging.getLogger("eflms.import_reference")
logging.basicConfig(level=logging.INFO, format="%(message)s")


async def run(path: str, ef_code: str, table: str, replace: bool, check: bool) -> bool:
    async with async_session_factory() as session:
        result = await import_reference_file(path, ef_code, table, session, replace=replace, dry_run=check)

    logger.info(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **{k: v for k, v in asdict(result).items() if k != "row_errors"},
                "row_errors": [asdict(e) for e in result.row_errors],
                "ok": result.ok,
            },
            ensure_ascii=False,
            default=str,
        )
    )

    name = f"{result.ef_code} 참고표 {result.table}"
    if result.ok and result.dry_run:
        print(f"[점검 통과] {name} {result.total_rows}건 검증 성공 - DB에는 반영하지 않음(--check)")
        if result.replace:
            print(f"  --check 없이 실행하면 기존 {result.table_rows_before}행을 지우고 파일 내용으로 교체함")
        else:
            print(f"  현재 {result.table_rows_before}행 - --replace 없이 실행하면 같은 행은 갱신, 새 행은 추가")
    elif result.ok:
        print(f"[완료] {name} {result.total_rows}건 반영 - 추가 {result.inserted_rows}, 갱신 {result.updated_rows} (현재 {result.table_rows_after}행)")
        if result.replace:
            print(f"  --replace: 기존 {result.deleted_rows}행을 지우고 교체함")
        print(f"  {result.ef_code} 설비 {result.recalculated}건 점수 재계산")
        if result.unchanged_rows:
            print(f"  지금과 값이 같은 {result.unchanged_rows}행은 건드리지 않음")
        if result.change_id:
            print(f"  변경 이력 #{result.change_id} — 관리자 화면 '변경 이력'에서 되돌릴 수 있음")
    else:
        print("[실패] 점검 실패" if result.dry_run else "[실패] 참고표 임포트를 중단함(0건 반영)")
        for fe in result.file_errors:
            print(f"  - {fe}")
        for e in result.row_errors:
            print(f"  - {e.row_number}행 {e.column}: '{e.raw_value}' ({e.reason})")
    if result.unknown_columns:
        print(f"  모르는 컬럼(저장 안 함): {', '.join(result.unknown_columns)}")
    for w in result.warnings:
        print(f"  [경고] {w}")
    return result.ok


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="EFLMS 참고표 임포트")
    parser.add_argument("--ef-code", required=True, help="설비유형 코드 (예: EF7)")
    parser.add_argument("--table", required=True, help="참고표 이름 (예: discharge_history, temp_decay_coef)")
    parser.add_argument("--file", required=True, help="임포트할 .dat 파일 경로")
    parser.add_argument("--replace", action="store_true", help="참고표를 비우고 파일 내용으로 교체")
    parser.add_argument("--check", action="store_true", help="검증만 하고 DB에는 반영하지 않음")
    args = parser.parse_args()
    ok = asyncio.run(run(args.file, args.ef_code, args.table, args.replace, args.check))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
