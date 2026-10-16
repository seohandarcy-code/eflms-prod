"""사내 입력파일(.dat, 탭구분) 임포트 서비스.

파일을 읽어 검증하고, 문제가 없을 때만 기존 mock 시드와 동일한 경로
(설비유형 모듈의 `calculate` -> `ingest.ingest_row`)로 DB에 반영한다.
컬럼 정의와 계산기는 `--ef-code`로 레지스트리에서 고른다(Stage 8-2).

부분 반영 금지: 검증에 실패한 행이 하나라도 있으면 아무것도 반영하지 않고, 검증을 통과한 뒤
반영 도중(계산/DB) 실패해도 파일 전체를 rollback한다 — 파일 하나가 트랜잭션 하나다.
`replace=True`면 같은 트랜잭션 안에서 그 유형의 기존 데이터를 지우고 파일 내용으로 교체한다
(다른 유형은 그대로).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EquipmentExtraAttribute
from app.equipment_types.registry import UnknownEquipmentTypeError, get_module
from app.services.dataset_service import reset_type
from app.services.ingest import ingest_row


def _match_column(columns_by_name: dict[str, dict], header: str) -> dict | None:
    """파일 헤더를 name(영문)으로만 매칭한다.

    INPUT_COLUMNS의 label(한글)은 항목 설명용 메타데이터일 뿐 — 실제 사내
    입력파일은 영문 헤더로만 오는 것으로 확인되어 매칭 기준에서 제외했다.
    """
    return columns_by_name.get(header.strip())


def _cast_value(raw: str, dtype: str):
    raw = raw.strip()
    if dtype == "int":
        return int(raw)
    if dtype == "float":
        return float(raw)
    if dtype == "date":
        return datetime.strptime(raw, "%Y-%m-%d").date()
    return raw


def _check_allowed(value, col: dict) -> str | None:
    """컬럼에 선언된 허용값(choices/min/max/required)을 검사해 위반 사유를 돌려준다(없으면 None).

    선언하지 않은 컬럼은 검사하지 않는다 — EF1처럼 허용값을 두지 않은 유형은 동작이 그대로다.
    """
    if col.get("required") and value == "":
        return "빈 값"
    choices = col.get("choices")
    if choices is not None and value not in choices:
        return f"허용값 아님({', '.join(str(c) for c in choices)})"
    if "min" in col and value < col["min"]:
        return f"{col['min']} 미만"
    if "max" in col and value > col["max"]:
        return f"{col['max']} 초과"
    return None


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
    replace: bool = False
    replaced_rows: int = 0  # replace=True일 때 지워진 기존 설비 수
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


async def import_file(path: str, ef_code: str, session: AsyncSession, replace: bool = False) -> ImportResult:
    result = ImportResult(file_path=path, ef_code=ef_code, replace=replace)

    try:
        module = get_module(ef_code)
    except UnknownEquipmentTypeError as exc:
        result.file_errors.append(str(exc))
        return result
    input_columns = module.INPUT_COLUMNS
    columns_by_name = {col["name"]: col for col in input_columns}

    text = _read_text(path)
    header, raw_rows = _parse_lines(text)
    if not header:
        result.file_errors.append("파일이 비어 있음")
        return result

    matched_cols = [_match_column(columns_by_name, h) for h in header]
    for h, col in zip(header, matched_cols):
        if col is None and h.strip():
            result.unknown_columns.append(h.strip())

    # 필수 입력 컬럼(스키마 전체)이 파일에 하나도 없으면 행 단위가 아니라 파일 단위 오류
    matched_names = {col["name"] for col in matched_cols if col is not None}
    missing_columns = [col["name"] for col in input_columns if col["name"] not in matched_names]
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
                value = _cast_value(raw_value, col["dtype"])
            except (ValueError, TypeError):
                result.row_errors.append(
                    RowError(row_number=i, column=col["name"], raw_value=raw_value, reason=f"{col['dtype']} 형식이 아님")
                )
                continue
            reason = _check_allowed(value, col)
            if reason:
                result.row_errors.append(RowError(row_number=i, column=col["name"], raw_value=raw_value, reason=reason))
            row[col["name"]] = value
        # 다른 유형의 파일을 잘못 지정해 넣는 실수 방지 — 행의 EF_code가 --ef-code와 같아야 한다.
        if row.get("EF_code") != ef_code:
            result.row_errors.append(
                RowError(
                    row_number=i,
                    column="EF_code",
                    raw_value=str(row.get("EF_code")),
                    reason=f"--ef-code({ef_code})와 다른 설비유형",
                )
            )
        parsed_rows.append(row)
        extras_per_row.append(extras)

    if result.row_errors:
        return result

    # 2) 검증 통과 — 기존 시드와 동일한 경로로 계산 + 저장. 파일 전체를 한 트랜잭션으로.
    try:
        if replace:
            result.replaced_rows = await reset_type(session, ef_code)
        for row, extras in zip(parsed_rows, extras_per_row):
            full_row = module.calculate(row)
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
        await session.commit()
    except Exception as exc:
        await session.rollback()
        result.replaced_rows = 0
        result.file_errors.append(f"반영 중 오류로 전체 rollback(0건 반영): {type(exc).__name__}: {exc}")
        return result

    result.imported_rows = len(parsed_rows)
    return result
