"""사내 입력파일(.dat, 탭구분) 임포트 서비스.

파일을 읽어 검증하고, 문제가 없을 때만 기존 mock 시드와 동일한 경로
(설비유형 모듈의 `calculate` -> `ingest.ingest_row`)로 DB에 반영한다.
컬럼 정의와 계산기는 `--ef-code`로 레지스트리에서 고른다(Stage 8-2).

부분 반영 금지: 검증에 실패한 행이 하나라도 있으면 아무것도 반영하지 않고, 검증을 통과한 뒤
반영 도중(계산/DB) 실패해도 파일 전체를 rollback한다 — 파일 하나가 트랜잭션 하나다.
`replace=True`면 같은 트랜잭션 안에서 그 유형의 기존 데이터를 지우고 파일 내용으로 교체한다
(다른 유형은 그대로). `dry_run=True`면 검증과 계산까지만 하고 DB에는 쓰지 않는다(`--check`).

실제 파일에서 흔한 표기 차이(UTF-8 BOM, 값을 감싼 따옴표, `154000.0` 같은 정수의 실수 표기,
`YYYY.MM.DD`/`YYYY/MM/DD`/`YYYYMMDD` 날짜)는 받아주고, 값 자체가 틀린 것(소수 정수, NaN,
빈 숫자/날짜, 칸 수 불일치, 파일 안 중복 설비)은 행 오류로 막는다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EquipmentExtraAttribute
from app.equipment_types.registry import UnknownEquipmentTypeError, get_module
from app.services.dataset_service import count_type, reset_type
from app.services.ingest import ingest_row


def _match_column(columns_by_name: dict[str, dict], header: str) -> dict | None:
    """파일 헤더를 name(영문)으로만 매칭한다(앞뒤 공백·따옴표는 _parse_lines에서 이미 제거).

    INPUT_COLUMNS의 label(한글)은 항목 설명용 메타데이터일 뿐 — 실제 사내
    입력파일은 영문 헤더로만 오는 것으로 확인되어 매칭 기준에서 제외했다.
    """
    return columns_by_name.get(header.strip())


DATE_FORMATS = ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d")


def _parse_date(raw: str):
    # YYYYMMDD는 8자리 숫자일 때만 — strptime은 "2020611" 같은 자릿수 모자란 값도 억지로 해석한다.
    if len(raw) == 8 and raw.isdigit():
        return datetime.strptime(raw, "%Y%m%d").date()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(raw)


def _cast_value(raw: str, dtype: str):
    raw = raw.strip()
    if dtype == "int":
        try:
            return int(raw)
        except ValueError:
            # 엑셀 저장 시 흔한 "154000.0"은 받되, "154000.5"처럼 정수가 아닌 값은 거부한다.
            number = float(raw)
            if not number.is_integer():
                raise
            return int(number)
    if dtype == "float":
        number = float(raw)
        if not math.isfinite(number):  # float()은 "nan"/"inf"도 받아들인다
            raise ValueError(raw)
        return number
    if dtype == "date":
        return _parse_date(raw)
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
    row_number: int  # 파일의 실제 줄 번호(1행은 헤더)
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
    ignored_columns: list[str] = field(default_factory=list)  # 유형이 IGNORED_COLUMNS로 선언한, 건너뛴 컬럼
    dry_run: bool = False
    existing_rows: int = 0  # dry_run일 때 현재 그 유형의 설비 수(--replace면 지워질 수)

    @property
    def ok(self) -> bool:
        return not self.file_errors and not self.row_errors


def _read_text(path: str) -> str:
    """UTF-8(BOM 있어도 됨)을 우선 시도하고, 실패하면 CP949(EUC-KR)로 폴백한다."""
    with open(path, "rb") as f:
        raw = f.read()
    try:
        # utf-8-sig: 엑셀/메모장이 붙이는 BOM을 떼어낸다 — 안 떼면 첫 헤더가 "\ufefffactory_code"가 돼
        # 파일 전체가 "필수 컬럼 없음"으로 거부된다.
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp949")


def _unquote(cell: str) -> str:
    cell = cell.strip()
    if len(cell) >= 2 and cell[0] == cell[-1] == '"':
        return cell[1:-1].replace('""', '"')
    return cell


def _parse_lines(text: str) -> tuple[list[str], list[tuple[int, list[str]]]]:
    """헤더와 (파일 줄 번호, 칸 목록)을 돌려준다. 빈 줄은 건너뛰되 줄 번호는 실제 파일 기준."""
    numbered = [(n, line) for n, line in enumerate(text.splitlines(), start=1) if line.strip() != ""]
    if not numbered:
        return [], []
    header = [_unquote(c) for c in numbered[0][1].split("\t")]
    rows = [(n, [_unquote(c) for c in line.split("\t")]) for n, line in numbered[1:]]
    return header, rows


async def import_file(
    path: str, ef_code: str, session: AsyncSession, replace: bool = False, dry_run: bool = False
) -> ImportResult:
    result = ImportResult(file_path=path, ef_code=ef_code, replace=replace, dry_run=dry_run)

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
    # 유형이 "원본엔 있지만 쓰지 않는다"고 선언한 컬럼 — 미등록 컬럼(extra 보관)과 달리 아예 버린다.
    ignored = set(getattr(module, "IGNORED_COLUMNS", ()))
    skip = [col is None and h in ignored for h, col in zip(header, matched_cols)]
    for h, col, is_skipped in zip(header, matched_cols, skip):
        if is_skipped:
            result.ignored_columns.append(h)
        elif col is None and h.strip():
            result.unknown_columns.append(h.strip())

    # 필수 입력 컬럼(스키마 전체)이 파일에 하나도 없으면 행 단위가 아니라 파일 단위 오류
    matched_names = {col["name"] for col in matched_cols if col is not None}
    missing_columns = [col["name"] for col in input_columns if col["name"] not in matched_names]
    if missing_columns:
        result.file_errors.append(f"필수 컬럼 없음: {', '.join(missing_columns)}")
        return result

    result.total_rows = len(raw_rows)

    # 1) 전체 행 검증 먼저 — 하나라도 오류가 있으면 DB에 아무것도 반영하지 않는다.
    parsed_rows: list[tuple[int, dict]] = []
    extras_per_row: list[dict[str, str]] = []
    first_row_of: dict[tuple, int] = {}  # (factory_code, 설비명) -> 처음 나온 줄 번호
    for i, raw_row in raw_rows:
        # 칸 수가 헤더와 다르면 값이 한 칸씩 밀렸거나 끝 칸이 잘린 것 — 그대로 두면 엉뚱한 컬럼에
        # 값이 들어가거나 계산 중 KeyError로 실패하므로 행 오류로 먼저 막는다.
        if len(raw_row) != len(header):
            result.row_errors.append(
                RowError(
                    row_number=i,
                    column="(행 전체)",
                    raw_value=f"{len(raw_row)}칸",
                    reason=f"칸 수 불일치(헤더 {len(header)}칸)",
                )
            )
            continue
        row: dict = {"EF_code": ef_code}
        extras: dict[str, str] = {}
        for h, col, raw_value, is_skipped in zip(header, matched_cols, raw_row, skip):
            if is_skipped:
                continue
            if col is None:
                if raw_value.strip():
                    extras[h.strip()] = raw_value.strip()
                continue
            try:
                value = _cast_value(raw_value, col["dtype"])
            except (ValueError, TypeError):
                if raw_value.strip() == "":
                    reason = f"빈 값({col['dtype']} 필요)"
                elif col["dtype"] == "date":
                    reason = "date 형식이 아님(YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD, YYYYMMDD)"
                else:
                    reason = f"{col['dtype']} 형식이 아님"
                result.row_errors.append(RowError(row_number=i, column=col["name"], raw_value=raw_value, reason=reason))
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
        # 같은 설비(공장 + 설비명)가 파일에 두 번 나오면 뒤 행이 앞 행을 조용히 덮어쓴다 — 거부한다.
        key = (row.get("factory_code"), row.get(module.NAME_FIELD))
        if key in first_row_of:
            result.row_errors.append(
                RowError(
                    row_number=i,
                    column=module.NAME_FIELD,
                    raw_value=f"{key[0]} / {key[1]}",
                    reason=f"{first_row_of[key]}행과 같은 설비(factory_code + {module.NAME_FIELD}) 중복",
                )
            )
        else:
            first_row_of[key] = i
        parsed_rows.append((i, row))
        extras_per_row.append(extras)

    if result.row_errors:
        return result

    # 2) 계산 — DB에 쓰기 전에 전부 계산해 둔다. 실패하면 몇 번째 행인지 행 오류로 알려준다.
    full_rows: list[dict] = []
    for i, row in parsed_rows:
        try:
            full_rows.append(module.calculate(row))
        except Exception as exc:
            result.row_errors.append(
                RowError(row_number=i, column="(계산)", raw_value="", reason=f"{type(exc).__name__}: {exc}")
            )
    if result.row_errors:
        return result

    if dry_run:
        result.existing_rows = await count_type(session, ef_code)
        return result

    # 3) 저장 — 기존 시드와 동일한 경로. 파일 전체를 한 트랜잭션으로.
    try:
        if replace:
            result.replaced_rows = await reset_type(session, ef_code)
        for full_row, extras in zip(full_rows, extras_per_row):
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
