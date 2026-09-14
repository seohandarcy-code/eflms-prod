"""테스트/시연용 샘플 .dat 파일 3종을 backend/sample_data/에 생성한다.

    .venv/Scripts/python scripts/generate_sample_dat.py

실제 사내 파일이 아니라 mock 스키마(ef1_transformer.INPUT_COLUMNS) 기준으로 만든
연습용 파일이다. 실제 파일로 바꾸는 방법은 backend/CLAUDE.md 참고.
"""
from pathlib import Path

from app.equipment_types.ef1_transformer import INPUT_COLUMNS, generate_input_row

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"

# 일부 컬럼은 영문 name 대신 한글 label로 헤더를 써서, 두 표기 모두 매칭되는지 보여준다.
_LABEL_HEADER_COLUMNS = {"factory_code", "transformer_name", "voltage"}


def _format_value(value) -> str:
    from datetime import date

    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _header_row() -> list[str]:
    return [col["label"] if col["name"] in _LABEL_HEADER_COLUMNS else col["name"] for col in INPUT_COLUMNS]


def _data_row(row: dict) -> list[str]:
    return [_format_value(row[col["name"]]) for col in INPUT_COLUMNS]


def write_valid(path: Path, rows: int = 100) -> None:
    header = _header_row()
    lines = ["\t".join(header)]
    for _ in range(rows):
        lines.append("\t".join(_data_row(generate_input_row())))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_with_errors(path: Path, rows: int = 100) -> None:
    header = _header_row()
    lines = ["\t".join(header)]
    voltage_idx = [col["name"] for col in INPUT_COLUMNS].index("voltage")
    for i in range(rows):
        cells = _data_row(generate_input_row())
        if i == 2:  # 3번째 행의 전압 값을 숫자가 아닌 값으로 깨뜨린다
            cells[voltage_idx] = "확인필요"
        lines.append("\t".join(cells))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_with_extra_columns(path: Path, rows: int = 100) -> None:
    header = [*_header_row(), "점검자", "비고"]
    lines = ["\t".join(header)]
    for i in range(rows):
        cells = [*_data_row(generate_input_row()), f"홍길동{i + 1}", "정기점검"]
        lines.append("\t".join(cells))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    SAMPLE_DIR.mkdir(exist_ok=True)
    write_valid(SAMPLE_DIR / "sample_valid.dat")
    write_with_errors(SAMPLE_DIR / "sample_with_errors.dat")
    write_with_extra_columns(SAMPLE_DIR / "sample_with_extra_columns.dat")
    print(f"[완료] {SAMPLE_DIR}에 샘플 3종 생성")


if __name__ == "__main__":
    main()
