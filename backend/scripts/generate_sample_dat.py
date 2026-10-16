"""테스트/시연용 샘플 .dat 파일 3종을 backend/sample_data/<ef_code 소문자>/에 생성한다.

    .venv/Scripts/python scripts/generate_sample_dat.py --ef-code EF1

실제 사내 파일이 아니라 각 설비유형 모듈의 mock 스키마(INPUT_COLUMNS) 기준으로 만든
연습용 파일이다. 실제 파일로 바꾸는 방법은 backend/CLAUDE.md 참고.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

# `python scripts/generate_sample_dat.py`로 직접 실행해도 app 패키지를 찾도록 backend/를 경로에 넣는다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.equipment_types.base import EquipmentTypeModule  # noqa: E402
from app.equipment_types.registry import get_module, resolve_codes  # noqa: E402

SAMPLE_ROOT = Path(__file__).resolve().parent.parent / "sample_data"


def _format_value(value) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _header_row(module: EquipmentTypeModule) -> list[str]:
    # 실제 사내 입력파일은 영문 헤더로만 오므로, 샘플도 name(영문)만 사용한다.
    return [col["name"] for col in module.INPUT_COLUMNS]


def _data_row(module: EquipmentTypeModule) -> list[str]:
    row = module.generate_input_row()
    return [_format_value(row[col["name"]]) for col in module.INPUT_COLUMNS]


def write_valid(module: EquipmentTypeModule, path: Path, rows: int = 100) -> None:
    lines = ["\t".join(_header_row(module))]
    for _ in range(rows):
        lines.append("\t".join(_data_row(module)))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_with_errors(module: EquipmentTypeModule, path: Path, rows: int = 100) -> None:
    header = _header_row(module)
    lines = ["\t".join(header)]
    voltage_idx = header.index("voltage")
    for i in range(rows):
        cells = _data_row(module)
        if i == 2:  # 3번째 행의 전압 값을 숫자가 아닌 값으로 깨뜨린다
            cells[voltage_idx] = "확인필요"
        lines.append("\t".join(cells))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_with_extra_columns(module: EquipmentTypeModule, path: Path, rows: int = 100) -> None:
    lines = ["\t".join([*_header_row(module), "점검자", "비고"])]
    for i in range(rows):
        lines.append("\t".join([*_data_row(module), f"홍길동{i + 1}", "정기점검"]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="설비유형별 샘플 .dat 3종 생성")
    parser.add_argument("--ef-code", default="all", help="설비유형 코드(예: EF1) 또는 all(기본값)")
    args = parser.parse_args()
    for code in resolve_codes(args.ef_code):
        module = get_module(code)
        sample_dir = SAMPLE_ROOT / code.lower()
        sample_dir.mkdir(parents=True, exist_ok=True)
        write_valid(module, sample_dir / "sample_valid.dat")
        write_with_errors(module, sample_dir / "sample_with_errors.dat")
        write_with_extra_columns(module, sample_dir / "sample_with_extra_columns.dat")
        print(f"[완료] {sample_dir}에 샘플 3종 생성")


if __name__ == "__main__":
    main()
