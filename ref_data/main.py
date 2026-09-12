"""
목업 데이터 생성 실행 스크립트
=================================
schema_config.py 에 정의된 컬럼 구성을 읽어서

  1) 입력 컬럼(INPUT_COLUMNS) 랜덤 생성
  2) 계산 컬럼(CALCULATED_COLUMNS) 순서대로 계산
  3) 화면용 컬럼(DISPLAY_COLUMNS)만 추린 결과 생성
  4) output/mock_data.dat  (전체 원본 데이터, UTF-8 텍스트 JSON)
     output/mock_data.yaml (화면 구성용 데이터, 사람이 읽기 위한 형식)
     로 저장합니다.

실행 방법
---------
    python main.py --rows 100

설치/환경 구성은 README.md 참고.
"""
import argparse
import json
from pathlib import Path
from datetime import date

import yaml

from schema_eflms import (
    INPUT_COLUMNS,
    CALCULATED_COLUMNS,
    DISPLAY_COLUMNS,
    # post_process_inputs,
)

OUTPUT_DIR = Path(__file__).parent / "output"


def generate_row(row_id: int) -> dict:
    row = {"id": row_id}

    # 1) 입력 컬럼 생성
    for col in INPUT_COLUMNS:
        row[col["name"]] = col["generator"]()
    # row = post_process_inputs(row)

    # 2) 계산 컬럼 - 리스트에 적힌 순서대로 계산 (앞선 계산 컬럼 참조 가능)
    for col in CALCULATED_COLUMNS:
        row[col["name"]] = col["formula"](row)

    return row


def to_display_row(row: dict) -> dict:
    """DISPLAY_COLUMNS 에 정의된 컬럼만 골라 화면용 row로 변환"""
    return {"id": row["id"], **{name: row[name] for name in DISPLAY_COLUMNS}}


def _text_safe(value):
    """date 등 JSON/YAML이 기본으로 못 다루는 타입을 문자열로 변환"""
    if isinstance(value, date):
        return value.isoformat()
    return value


def main(n_rows: int) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    full_rows = [generate_row(i + 1) for i in range(n_rows)]
    display_rows = [to_display_row(r) for r in full_rows]

    # ---- .dat 저장 : 전체 컬럼(입력+계산) 원본 데이터, UTF-8 텍스트(JSON) ----
    # (이전 버전은 pickle 바이너리로 저장해서 다른 프로그램/에디터로 열면
    #  인코딩이 깨진 것처럼 보이는 문제가 있었습니다. UTF-8 JSON 텍스트로 바꿔서
    #  메모장/VS Code 등 어떤 텍스트 에디터로 열어도 한글이 그대로 보이도록 했습니다.)
    dat_path = OUTPUT_DIR / "eflms_data.dat"
    full_ready = [
        {k: _text_safe(v) for k, v in row.items()} for row in full_rows
    ]
    with open(dat_path, "w", encoding="utf-8") as f:
        json.dump(full_ready, f, ensure_ascii=False, indent=2)

    # ---- .yaml 저장 : 화면 구성용 컬럼만 담은, 사람이 읽기 위한 형식 ----
    yaml_path = OUTPUT_DIR / "eflms_data.yaml"
    yaml_ready = [
        {k: _text_safe(v) for k, v in row.items()} for row in display_rows
    ]
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_ready, f, allow_unicode=True, sort_keys=False)

    print(f"[완료] {n_rows}건 생성")
    print(f" - 전체 데이터 (.dat, UTF-8 JSON) : {dat_path}")
    print(f" - 화면용 데이터 (.yaml)          : {yaml_path}")
    print(f" - 입력 컬럼 수: {len(INPUT_COLUMNS)} / 계산 컬럼 수: {len(CALCULATED_COLUMNS)} "
          f"/ 화면 컬럼 수: {len(DISPLAY_COLUMNS)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="엑셀 기반 목업 데이터 생성기")
    parser.add_argument("--rows", type=int, default=50, help="생성할 행 개수 (기본 50)")
    args = parser.parse_args()
    main(args.rows)
