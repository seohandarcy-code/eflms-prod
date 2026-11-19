"""참고표 dat 임포트·리셋 + 해당 유형 재계산 (Stage 15-0, 2026-11-16 사용자 결정).

설비 파일처럼 참고표도 넣기(추가·갱신) / 교체(replace) / 검증만(dry_run) / 리셋을 한다.
참고표가 바뀌면 **같은 트랜잭션 안에서** 그 유형의 설비 점수를 전부 다시 계산한다 — 계산 기준일은 저장된 그대로 두고
참고표 변화만 반영한다(모듈의 load_inputs → calculate(as_of=저장 기준일) → ingest_row).

파일 규칙은 설비 임포트와 같다(app/services/import_service.py의 읽기·형식 변환·허용값 검사를 그대로 쓴다):
- 탭 구분, 헤더 = 참고표 컬럼 name. UTF-8(BOM)/CP949, 따옴표, 날짜 4가지 표기.
- 형식 오류가 한 행이라도 있으면 파일 전체를 반영하지 않는다. 반영 중 실패해도 전체 rollback.
- 참고표 값은 모두 필수라 N/A·빈 칸을 받지 않는다. 같은 행(표의 key)이 파일에 두 번 나오면 거부.
- 모르는 컬럼은 저장하지 않고 결과에 표시만 한다(참고표엔 보관할 곳이 없다).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Equipment
from app.equipment_types.na import is_na_token
from app.equipment_types.registry import UnknownEquipmentTypeError, get_module
from app.services.import_service import RowError, _cast_value, _check_allowed, _parse_lines, _read_text
from app.services.ingest import ingest_row
from app.services.reference_data import calc_options, count_rows, empty_reference_warnings, reference_specs, scope_warnings


@dataclass
class ReferenceImportResult:
    file_path: str
    ef_code: str
    table: str
    replace: bool = False
    dry_run: bool = False
    total_rows: int = 0
    inserted_rows: int = 0
    updated_rows: int = 0
    deleted_rows: int = 0  # replace일 때 지운 기존 행 수
    table_rows_before: int = 0
    table_rows_after: int = 0
    recalculated: int = 0  # 다시 계산한 설비 수
    file_errors: list[str] = field(default_factory=list)
    row_errors: list[RowError] = field(default_factory=list)
    unknown_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.file_errors and not self.row_errors


@dataclass
class ReferenceResetResult:
    ef_code: str
    deleted: dict[str, int] = field(default_factory=dict)  # 표 이름 → 지운 행 수
    recalculated: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _resolve(ef_code: str, table: str, allow_all: bool) -> tuple[object, dict[str, dict]]:
    """(모듈, {표 이름: spec}) — 잘못된 유형/표는 ValueError(메시지 그대로 사용자에게 보여준다)."""
    try:
        module = get_module(ef_code)
    except UnknownEquipmentTypeError as exc:
        raise ValueError(str(exc)) from None
    specs = reference_specs(module)
    if not specs:
        raise ValueError(f"{ef_code}에는 참고표가 없음")
    if allow_all and table == "all":
        return module, specs
    if table not in specs:
        choices = ", ".join(specs) + (", all" if allow_all else "")
        raise ValueError(f"{ef_code}에 없는 참고표: {table} (가능: {choices})")
    return module, {table: specs[table]}


async def recalculate_type(session: AsyncSession, module) -> int:
    """유형의 설비 점수를 지금 DB의 참고표로 다시 계산해 저장한다. 다시 계산한 설비 수. commit하지 않는다."""
    await session.flush()
    options = await calc_options(session, module)
    ids = (
        await session.execute(select(Equipment.equipment_id).where(Equipment.ef_code == module.EF_CODE))
    ).scalars().all()
    count = 0
    for eq_id in ids:
        loaded = await module.load_inputs(session, eq_id)
        if loaded is None:
            continue
        input_row, as_of = loaded
        await ingest_row(module.calculate(input_row, as_of=as_of, **options), session)
        count += 1
    return count


async def _warnings(session: AsyncSession, module) -> list[str]:
    """재계산 뒤 경고 — 빈 참고표 + 사업장별 참고표(EF7 방전이력)에 행이 없는 사업장(Stage 19, 막지 않음)."""
    options = await calc_options(session, module)
    sites = (
        await session.execute(select(Equipment.factory_code).where(Equipment.ef_code == module.EF_CODE))
    ).scalars().all()
    return empty_reference_warnings(module, options) + scope_warnings(module, options, list(sites))


def _key_of(spec: dict, row: dict) -> tuple:
    return tuple(row[k] for k in spec["key"])


def _check_row_extra(value, col: dict) -> str | None:
    # _check_allowed에 없는 "초과" 조건(예: 온도감소계수 gamma_y > 0)
    if "gt" in col and value <= col["gt"]:
        return f"{col['gt']} 이하"
    return None


def _parse_file(path: str, spec: dict, result: ReferenceImportResult) -> list[dict]:
    """검증을 통과한 행 dict 목록. 오류는 result에 쌓는다."""
    text = _read_text(path)
    header, raw_rows = _parse_lines(text)
    if not header:
        result.file_errors.append("파일이 비어 있음")
        return []
    columns_by_name = {c["name"]: c for c in spec["columns"]}
    matched = [columns_by_name.get(h.strip()) for h in header]
    result.unknown_columns = [h.strip() for h, col in zip(header, matched) if col is None and h.strip()]
    missing = [name for name in columns_by_name if name not in {c["name"] for c in matched if c}]
    if missing:
        result.file_errors.append(f"필수 컬럼 없음: {', '.join(missing)}")
        return []

    result.total_rows = len(raw_rows)
    rows: list[dict] = []
    first_row_of: dict[tuple, int] = {}
    for i, raw_row in raw_rows:
        if len(raw_row) != len(header):
            result.row_errors.append(
                RowError(row_number=i, column="(행 전체)", raw_value=f"{len(raw_row)}칸", reason=f"칸 수 불일치(헤더 {len(header)}칸)")
            )
            continue
        row: dict = {}
        for col, raw_value in zip(matched, raw_row):
            if col is None:
                continue
            if is_na_token(raw_value):
                result.row_errors.append(RowError(row_number=i, column=col["name"], raw_value=raw_value, reason="N/A 불가(참고표)"))
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
            reason = _check_allowed(value, col) or _check_row_extra(value, col)
            if reason:
                result.row_errors.append(RowError(row_number=i, column=col["name"], raw_value=raw_value, reason=reason))
            row[col["name"]] = value
        if all(k in row for k in spec["key"]):
            key = _key_of(spec, row)
            if key in first_row_of:
                result.row_errors.append(
                    RowError(
                        row_number=i,
                        column=" + ".join(spec["key"]),
                        raw_value=" / ".join(str(k) for k in key),
                        reason=f"{first_row_of[key]}행과 같은 행 중복",
                    )
                )
            else:
                first_row_of[key] = i
        rows.append(row)
    return rows


async def import_reference_file(
    path: str, ef_code: str, table: str, session: AsyncSession, replace: bool = False, dry_run: bool = False
) -> ReferenceImportResult:
    result = ReferenceImportResult(file_path=path, ef_code=ef_code, table=table, replace=replace, dry_run=dry_run)
    try:
        module, specs = _resolve(ef_code, table, allow_all=False)
    except ValueError as exc:
        result.file_errors.append(str(exc))
        return result
    spec = specs[table]
    model = spec["model"]

    rows = _parse_file(path, spec, result)
    if not result.ok:
        return result

    result.table_rows_before = await count_rows(session, model)
    if dry_run:
        if replace and not rows:
            result.warnings.append(f"데이터 행이 없어 --replace면 참고표 '{spec['label']}'이 비게 됨 — 계산에서 0으로 처리")
        return result

    try:
        if replace:
            result.deleted_rows = (await session.execute(delete(model))).rowcount or 0
        for row in rows:
            existing = None
            if not replace:
                cond = and_(*(getattr(model, k) == row[k] for k in spec["key"]))
                existing = (await session.execute(select(model).where(cond))).scalar_one_or_none()
            if existing is None:
                session.add(model(**row))
                result.inserted_rows += 1
            else:
                for name, value in row.items():
                    setattr(existing, name, value)
                result.updated_rows += 1
        result.recalculated = await recalculate_type(session, module)
        result.table_rows_after = await count_rows(session, model)
        result.warnings = await _warnings(session, module)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        result.inserted_rows = result.updated_rows = result.deleted_rows = result.recalculated = 0
        result.file_errors.append(f"반영 중 오류로 전체 rollback(0건 반영): {type(exc).__name__}: {exc}")
    return result


async def reset_reference(session: AsyncSession, ef_code: str, table: str) -> ReferenceResetResult:
    """참고표를 비우고(table='all'이면 전부) 그 유형 설비를 다시 계산한다. 한 트랜잭션."""
    result = ReferenceResetResult(ef_code=ef_code)
    try:
        module, specs = _resolve(ef_code, table, allow_all=True)
    except ValueError as exc:
        result.errors.append(str(exc))
        return result
    try:
        for name, spec in specs.items():
            result.deleted[name] = (await session.execute(delete(spec["model"]))).rowcount or 0
        result.recalculated = await recalculate_type(session, module)
        result.warnings = await _warnings(session, module)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        result.deleted, result.recalculated = {}, 0
        result.errors.append(f"리셋 중 오류로 전체 rollback: {type(exc).__name__}: {exc}")
    return result
