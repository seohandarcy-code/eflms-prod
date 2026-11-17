"""테스트/시연용 샘플 .dat 파일 3종을 backend/sample_data/<ef_code 소문자>/에 생성한다.

    .venv/Scripts/python scripts/generate_sample_dat.py --ef-code EF1

실제 사내 파일이 아니라 각 설비유형 모듈의 mock 스키마(INPUT_COLUMNS) 기준으로 만든
연습용 파일이다. 실제 파일로 바꾸는 방법은 backend/CLAUDE.md 참고.

참고표가 있는 유형(EF7~, Stage 15-0)은 참고표별 `reference_<표 이름>.dat`(목업 참고표 그대로)와
`reference_<첫 표>_with_errors.dat`(3번째 행 숫자 값을 깨뜨림)도 만든다 — `python -m app.db.import_reference`용.
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
    # 3번째 행의 숫자 값 하나를 숫자가 아닌 값으로 깨뜨린다 — 전압이 있으면 전압(EF1~EF3),
    # 없으면(EF4) 첫 번째 정수 컬럼.
    if "voltage" in header:
        broken_idx = header.index("voltage")
    else:
        broken_idx = next(i for i, col in enumerate(module.INPUT_COLUMNS) if col["dtype"] == "int")
    for i in range(rows):
        cells = _data_row(module)
        if i == 2:
            cells[broken_idx] = "확인필요"
        lines.append("\t".join(cells))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_with_extra_columns(module: EquipmentTypeModule, path: Path, rows: int = 100) -> None:
    lines = ["\t".join([*_header_row(module), "점검자", "비고"])]
    for i in range(rows):
        lines.append("\t".join([*_data_row(module), f"홍길동{i + 1}", "정기점검"]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_table(path: Path, rows: list[list[str]]) -> None:
    path.write_text("\n".join("\t".join(r) for r in rows) + "\n", encoding="utf-8")


def write_reference(module: EquipmentTypeModule, sample_dir: Path) -> None:
    specs = getattr(module, "REFERENCE_TABLES", None) or {}
    for i, (name, spec) in enumerate(specs.items()):
        header = [c["name"] for c in spec["columns"]]
        rows = [[_format_value(r[h]) for h in header] for r in spec["mock_rows"]]
        _write_table(sample_dir / f"reference_{name}.dat", [header, *rows])
        if i == 0:
            # 3번째 데이터 행의 첫 숫자 컬럼을 숫자가 아닌 값으로 — 파일 전체 미반영 확인용
            broken = next(j for j, c in enumerate(spec["columns"]) if c["dtype"] in ("int", "float"))
            bad = [list(r) for r in rows]
            bad[2][broken] = "확인필요"
            _write_table(sample_dir / f"reference_{name}_with_errors.dat", [header, *bad])


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
        write_reference(module, sample_dir)
        print(f"[완료] {sample_dir}에 샘플 생성")


if __name__ == "__main__":
    main()
