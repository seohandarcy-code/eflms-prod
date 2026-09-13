from sqlalchemy import select

from app.db.models import Equipment, EquipmentExtraAttribute
from app.equipment_types.ef1_transformer import INPUT_COLUMNS, generate_input_row
from app.services.import_service import import_file

HEADER = "\t".join(col["name"] for col in INPUT_COLUMNS)


def _format(value) -> str:
    from datetime import date

    return value.isoformat() if isinstance(value, date) else str(value)


def _data_line(row: dict) -> str:
    return "\t".join(_format(row[col["name"]]) for col in INPUT_COLUMNS)


async def test_import_valid_file(session_factory, tmp_path):
    rows = [generate_input_row() for _ in range(3)]
    path = tmp_path / "valid.dat"
    path.write_text(HEADER + "\n" + "\n".join(_data_line(r) for r in rows) + "\n", encoding="utf-8")

    async with session_factory() as session:
        result = await import_file(str(path), "EF1", session)

        assert result.ok
        assert result.total_rows == 3
        assert result.imported_rows == 3
        assert (await session.execute(select(Equipment))).scalars().all().__len__() == 3


async def test_import_rejects_whole_file_on_row_error(session_factory, tmp_path):
    rows = [generate_input_row() for _ in range(3)]
    voltage_idx = [col["name"] for col in INPUT_COLUMNS].index("voltage")
    lines = [HEADER]
    for i, row in enumerate(rows):
        cells = _data_line(row).split("\t")
        if i == 1:
            cells[voltage_idx] = "확인필요"  # 숫자가 아닌 값으로 오류 유발
        lines.append("\t".join(cells))
    path = tmp_path / "with_error.dat"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    async with session_factory() as session:
        result = await import_file(str(path), "EF1", session)

        assert not result.ok
        assert result.imported_rows == 0
        assert len(result.row_errors) == 1
        assert result.row_errors[0].column == "voltage"
        # 아무것도 반영되지 않아야 함
        assert (await session.execute(select(Equipment))).scalars().all() == []


async def test_import_captures_unknown_columns(session_factory, tmp_path):
    rows = [generate_input_row() for _ in range(2)]
    header = HEADER + "\t점검자\t비고"
    lines = [header]
    for i, row in enumerate(rows):
        lines.append(_data_line(row) + f"\t홍길동{i + 1}\t정기점검")
    path = tmp_path / "with_extra.dat"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    async with session_factory() as session:
        result = await import_file(str(path), "EF1", session)

        assert result.ok
        assert sorted(result.unknown_columns) == ["비고", "점검자"]
        extras = (await session.execute(select(EquipmentExtraAttribute))).scalars().all()
        assert len(extras) == 4  # 2행 x 2개 미등록 컬럼
        assert {e.column_name for e in extras} == {"점검자", "비고"}


async def test_import_handles_cp949_encoding(session_factory, tmp_path):
    row = generate_input_row()
    text = HEADER + "\n" + _data_line(row) + "\n"
    path = tmp_path / "cp949.dat"
    path.write_bytes(text.encode("cp949"))

    async with session_factory() as session:
        result = await import_file(str(path), "EF1", session)

        assert result.ok
        assert result.imported_rows == 1
