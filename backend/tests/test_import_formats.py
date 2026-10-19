"""실제 사내 .dat 파일에서 흔한 표기 차이와 파일 오류를 임포트가 어떻게 다루는지 확인.

받아주는 것: UTF-8 BOM, 값을 감싼 따옴표, 정수의 실수 표기(154000.0), 날짜 4가지 표기, 빈 줄.
막는 것(행 오류, 0건 반영): 칸 수 불일치, 파일 안 중복 설비, 소수 정수, NaN, 빈 숫자/날짜.
--check(dry_run): 검증·계산만 하고 DB에는 쓰지 않는다.
"""
from datetime import date

import pytest
from sqlalchemy import func, select

from app.db.models import Equipment
from app.equipment_types import ef1_transformer, ef2_gis
from app.services.import_service import _cast_value, import_file

NAMES = [col["name"] for col in ef1_transformer.INPUT_COLUMNS]
HEADER = "\t".join(NAMES)


def _cells(row: dict) -> list[str]:
    return [v.isoformat() if isinstance(v, date) else str(v) for v in (row[n] for n in NAMES)]


def _rows(n: int) -> list[list[str]]:
    return [_cells(ef1_transformer.generate_input_row()) for _ in range(n)]


def _write(tmp_path, text: str, encoding: str = "utf-8", name: str = "real.dat") -> str:
    path = tmp_path / name
    path.write_bytes(text.encode(encoding))
    return str(path)


def _text(rows: list[list[str]], header: str = HEADER, sep: str = "\n") -> str:
    return sep.join([header] + ["\t".join(r) for r in rows]) + sep


async def _count(session) -> int:
    return await session.scalar(select(func.count()).select_from(Equipment))


# ---- 받아주는 표기 ----

async def test_utf8_bom_is_stripped(session_factory, tmp_path):
    path = _write(tmp_path, "﻿" + _text(_rows(2), sep="\r\n"))
    async with session_factory() as session:
        result = await import_file(path, "EF1", session)
        assert result.ok, (result.file_errors, result.row_errors)
        assert result.unknown_columns == []
        assert await _count(session) == 2


async def test_quoted_header_and_values_are_unquoted(session_factory, tmp_path):
    rows = [[f'"{c}"' for c in r] for r in _rows(2)]
    header = "\t".join(f'"{n}"' for n in NAMES)
    async with session_factory() as session:
        result = await import_file(_write(tmp_path, _text(rows, header=header)), "EF1", session)
        assert result.ok, result.row_errors
        assert await _count(session) == 2


async def test_integral_float_text_accepted_for_int_and_date_variants(session_factory, tmp_path):
    rows = _rows(4)
    v, d = NAMES.index("voltage"), NAMES.index("operation_start_time")
    rows[0][v] = rows[0][v] + ".0"
    rows[1][d] = rows[1][d].replace("-", ".")
    rows[2][d] = rows[2][d].replace("-", "/")
    rows[3][d] = rows[3][d].replace("-", "")
    async with session_factory() as session:
        result = await import_file(_write(tmp_path, _text(rows)), "EF1", session)
        assert result.ok, result.row_errors
        stored = (await session.execute(select(Equipment).order_by(Equipment.equipment_id))).scalars().all()
        assert stored[0].voltage == int(rows[0][v][:-2])
        assert [e.operation_start_time for e in stored[1:]] == [
            date.fromisoformat(rows[i][d].replace(".", "-").replace("/", "-")) if i < 3
            else date.fromisoformat(f"{rows[i][d][:4]}-{rows[i][d][4:6]}-{rows[i][d][6:]}")
            for i in (1, 2, 3)
        ]


async def test_blank_lines_skipped_and_row_numbers_follow_the_file(session_factory, tmp_path):
    rows = _rows(2)
    rows[1][NAMES.index("voltage")] = "확인필요"
    text = HEADER + "\n\n" + "\t".join(rows[0]) + "\n\n" + "\t".join(rows[1]) + "\n"
    async with session_factory() as session:
        result = await import_file(_write(tmp_path, text), "EF1", session)
        assert not result.ok
        assert [(e.row_number, e.column) for e in result.row_errors] == [(5, "voltage")]


@pytest.mark.parametrize(
    "raw, dtype, expected",
    [
        ("154000", "int", 154000),
        ("154000.0", "int", 154000),
        (" 30 ", "int", 30),
        ("0.5", "float", 0.5),
        ("2020-06-01", "date", date(2020, 6, 1)),
        ("2020.06.01", "date", date(2020, 6, 1)),
        ("2020/6/1", "date", date(2020, 6, 1)),
        ("20200601", "date", date(2020, 6, 1)),
    ],
)
def test_cast_value_accepts(raw, dtype, expected):
    assert _cast_value(raw, dtype) == expected


@pytest.mark.parametrize(
    "raw, dtype",
    [
        ("154000.5", "int"),
        ("", "int"),
        ("nan", "float"),
        ("inf", "float"),
        ("", "float"),
        ("2020611", "date"),
        ("2020-13-01", "date"),
        ("01/06/2020", "date"),
        ("", "date"),
    ],
)
def test_cast_value_rejects(raw, dtype):
    with pytest.raises(ValueError):
        _cast_value(raw, dtype)


# ---- 막는 것 ----

async def test_row_with_missing_trailing_cells_is_a_row_error(session_factory, tmp_path):
    rows = _rows(3)
    rows[1] = rows[1][:-2]
    async with session_factory() as session:
        result = await import_file(_write(tmp_path, _text(rows)), "EF1", session)
        assert not result.ok
        assert len(result.row_errors) == 1
        err = result.row_errors[0]
        assert (err.row_number, err.column) == (3, "(행 전체)")
        assert f"헤더 {len(NAMES)}칸" in err.reason and err.raw_value == f"{len(NAMES) - 2}칸"
        assert await _count(session) == 0


async def test_duplicate_equipment_in_file_is_rejected(session_factory, tmp_path):
    rows = _rows(3)
    rows.append(list(rows[0]))
    async with session_factory() as session:
        result = await import_file(_write(tmp_path, _text(rows)), "EF1", session)
        assert not result.ok
        assert [(e.row_number, e.column) for e in result.row_errors] == [(5, "transformer_name")]
        assert "2행" in result.row_errors[0].reason
        assert await _count(session) == 0


async def test_blank_numeric_value_reports_blank(session_factory, tmp_path):
    rows = _rows(1)
    rows[0][NAMES.index("load_percent")] = ""
    async with session_factory() as session:
        result = await import_file(_write(tmp_path, _text(rows)), "EF1", session)
        assert not result.ok
        assert result.row_errors[0].column == "load_percent"
        assert result.row_errors[0].reason.startswith("빈 값")


async def test_ef2_duplicate_uses_its_own_name_field(session_factory, tmp_path):
    names = [col["name"] for col in ef2_gis.INPUT_COLUMNS]
    row = ef2_gis.generate_input_row()
    line = "\t".join(row[n].isoformat() if isinstance(row[n], date) else str(row[n]) for n in names)
    text = "\t".join(names) + "\n" + line + "\n" + line + "\n"
    async with session_factory() as session:
        result = await import_file(_write(tmp_path, text), "EF2", session)
        assert not result.ok
        assert [(e.row_number, e.column) for e in result.row_errors] == [(3, "gis_name")]


# ---- --check (dry_run) ----

async def test_dry_run_validates_and_calculates_but_writes_nothing(session_factory, tmp_path):
    async with session_factory() as session:
        seeded = await import_file(_write(tmp_path, _text(_rows(2)), name="seed.dat"), "EF1", session)
        assert seeded.ok

        result = await import_file(_write(tmp_path, _text(_rows(5))), "EF1", session, replace=True, dry_run=True)
        assert result.ok and result.dry_run
        assert result.total_rows == 5 and result.imported_rows == 0
        assert result.existing_rows == 2 and result.replaced_rows == 0
        assert await _count(session) == 2


async def test_dry_run_reports_the_same_errors(session_factory, tmp_path):
    rows = _rows(2)
    rows[1][NAMES.index("voltage")] = "확인필요"
    async with session_factory() as session:
        result = await import_file(_write(tmp_path, _text(rows)), "EF1", session, dry_run=True)
        assert not result.ok
        assert [(e.row_number, e.column) for e in result.row_errors] == [(3, "voltage")]
