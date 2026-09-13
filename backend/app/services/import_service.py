"""사내 입력파일(.dat, 탭구분) 임포트 서비스.

파일을 읽어 검증하고, 문제가 없을 때만 기존 mock 시드와 동일한 경로
(`ef1_transformer.calculate` -> `ingest.ingest_row`)로 DB에 반영한다.
검증에 실패한 행이 하나라도 있으면 전체 파일을 반영하지 않는다(부분 반영 금지).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EquipmentExtraAttribute
from app.equipment_types.ef1_transformer import INPUT_COLUMNS, calculate
from app.services.ingest import ingest_row

_COLUMNS_BY_NAME = {col["name"]: col for col in INPUT_COLUMNS}
_COLUMNS_BY_LABEL = {col["label"]: col for col in INPUT_COLUMNS if col.get("label")}


def _match_column(header: str) -> dict | None:
    key = header.strip()
    return _COLUMNS_BY_NAME.get(key) or _COLUMNS_BY_LABEL.get(key)


def _cast_value(raw: str, dtype: str):
    raw = raw.strip()
    if dtype == "int":
        return int(raw)
    if dtype == "float":
        return float(raw)
    if dtype == "date":
        return datetime.strptime(raw, "%Y-%m-%d").date()
    return raw


def _infer_type(raw: str) -> str:
    """미등록 컬럼 값의 타입을 int -> float -> date -> string 순으로 추론한다."""
    for caster, name in ((int, "int"), (float, "float")):
        try:
            caster(raw)
            return name
        except ValueError:
            continue
    try:
        datetime.strptime(raw, "%Y-%m-%d")
        return "date"
    except ValueError:
        return "string"


@dataclass
class RowError:
    row_number: int  # 1행은 헤더이므로 첫 데이터 행부터 2
    column: str
    raw_value: str
    reason: str


@dataclass
class ImportResult:
    file_path: str
    ef_code: str
    total_rows: int = 0
    imported_rows: int = 0
    file_errors: list[str] = field(default_factory=list)
    row_errors: list[RowError] = field(default_factory=list)
    unknown_columns: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.file_errors and not self.row_errors


def _read_text(path: str) -> str:
    """UTF-8을 우선 시도하고, 실패하면 CP949(EUC-KR)로 폴백한다."""
    with open(path, "rb") as f:
        raw = f.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp949")


def _parse_lines(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [line for line in text.splitlines() if line.strip() != ""]
    if not lines:
        return [], []
    header = lines[0].split("\t")
    rows = [line.split("\t") for line in lines[1:]]
    return header, rows


async def import_file(path: str, ef_code: str, session: AsyncSession) -> ImportResult:
    result = ImportResult(file_path=path, ef_code=ef_code)

    text = _read_text(path)
    header, raw_rows = _parse_lines(text)
    if not header:
        result.file_errors.append("파일이 비어 있음")
        return result

    matched_cols = [_match_column(h) for h in header]
    for h, col in zip(header, matched_cols):
        if col is None and h.strip():
            result.unknown_columns.append(h.strip())

    # 필수 입력 컬럼(스키마 전체)이 파일에 하나도 없으면 행 단위가 아니라 파일 단위 오류
    matched_names = {col["name"] for col in matched_cols if col is not None}
    missing_columns = [col["name"] for col in INPUT_COLUMNS if col["name"] not in matched_names]
    if missing_columns:
        result.file_errors.append(f"필수 컬럼 없음: {', '.join(missing_columns)}")
        return result

    result.total_rows = len(raw_rows)

    # 1) 전체 행 검증 먼저 — 하나라도 오류가 있으면 DB에 아무것도 반영하지 않는다.
    parsed_rows: list[dict] = []
    extras_per_row: list[dict[str, str]] = []
    for i, raw_row in enumerate(raw_rows, start=2):
        row: dict = {"EF_code": ef_code}
        extras: dict[str, str] = {}
        for h, col, raw_value in zip(header, matched_cols, raw_row):
            if col is None:
                if raw_value.strip():
                    extras[h.strip()] = raw_value.strip()
                continue
            try:
                row[col["name"]] = _cast_value(raw_value, col["dtype"])
            except (ValueError, TypeError):
                result.row_errors.append(
                    RowError(row_number=i, column=col["name"], raw_value=raw_value, reason=f"{col['dtype']} 형식이 아님")
                )
        parsed_rows.append(row)
        extras_per_row.append(extras)

    if result.row_errors:
        return result

    # 2) 검증 통과 — 기존 시드와 동일한 경로로 계산 + 저장
    for row, extras in zip(parsed_rows, extras_per_row):
        full_row = calculate(row)
        eq_id = await ingest_row(full_row, session)
        for column_name, value in extras.items():
            session.add(
                EquipmentExtraAttribute(
                    equipment_id=eq_id,
                    column_name=column_name,
                    value=value,
                    inferred_type=_infer_type(value),
                    source_file=path,
                )
            )
        result.imported_rows += 1

    if any(extras_per_row):
        await session.commit()

    return result
