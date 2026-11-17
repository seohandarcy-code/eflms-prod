"""관리자 화면의 데이터 입력·내보내기 (Stage 16-2/16-3, 16-6 붙여넣기, 18 행 편집).

명령줄(`import_data`·`import_reference`)과 **같은 서비스**를 그대로 부른다 — 검증·계산·참고표 재계산·
전체 rollback 규칙이 CLI와 웹에서 똑같다. 여기서는 붙여넣은 내용(탭 구분 텍스트)을 임시 파일로 넘기고, 결과를
화면용 dict로 바꾸고(검증 통과 시 행별 추가/갱신 구분 포함), 입력 양식을 알려주고, 지금 DB 내용을 입력파일과
같은 dat 형식으로 꺼내는 일만 한다. 행 편집(Stage 18)은 같은 내용을 표(JSON)로 돌려주고, 저장은 화면이 고친 행만
탭 구분 텍스트로 만들어 붙여넣기와 같은 `import_text`(추가·갱신)로 보낸다 — 저장 경로가 따로 없다.

리셋(유형·참고표 비우기)은 실수 시 피해가 커서 웹에 두지 않는다 — 명령줄로만.
"""
from __future__ import annotations

import math
import os
import tempfile
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Equipment, EquipmentExtraAttribute
from app.equipment_types.registry import UnknownEquipmentTypeError, all_modules, get_module
from app.services.import_service import NOT_NULLABLE_COLUMNS, _parse_lines, import_file
from app.services.reference_data import count_rows, load_reference, reference_specs
from app.services.reference_service import ReferenceImportResult, _key_of, _parse_file, import_reference_file

MAX_TEXT_BYTES = 5 * 1024 * 1024
NA_TOKEN = "N/A"
ACTION_INSERT = "추가"
ACTION_UPDATE = "갱신"
TAB = chr(9)


class DataAdminError(ValueError):
    """잘못된 대상(유형·참고표) 요청 — 라우터가 400/404로 바꾼다."""


async def list_targets(session: AsyncSession) -> list[dict[str, Any]]:
    """입력·내보내기 대상: 설비유형별 설비 수와 참고표(이름·라벨·행 수)."""
    counts = dict(
        (await session.execute(select(Equipment.ef_code, func.count()).group_by(Equipment.ef_code))).all()
    )
    targets = []
    for module in all_modules():
        references = [
            {"name": name, "label": spec["label"], "rows": await count_rows(session, spec["model"])}
            for name, spec in reference_specs(module).items()
        ]
        targets.append(
            {
                "ef_code": module.EF_CODE,
                "ef_name": module.EF_NAME,
                "equipment_count": counts.get(module.EF_CODE, 0),
                "reference_tables": references,
            }
        )
    return targets


def _module_or_error(ef_code: str):
    try:
        return get_module(ef_code)
    except UnknownEquipmentTypeError as exc:
        raise DataAdminError(str(exc)) from None


def _reference_spec_or_error(module, table: str) -> dict:
    specs = reference_specs(module)
    if table not in specs:
        raise DataAdminError(f"{module.EF_CODE}에 없는 참고표: {table}")
    return specs[table]


def template(ef_code: str, table: str | None) -> dict[str, Any]:
    """붙여넣기 양식 — 헤더(영문 컬럼명) 순서와 컬럼별 설명·형식·허용값. 엑셀 첫 행에 헤더를 붙여 쓰면 된다."""
    module = _module_or_error(ef_code)
    if table:
        spec = _reference_spec_or_error(module, table)
        source, na_allowed = spec["columns"], (lambda _name: False)
        key = list(spec["key"])
    else:
        name_field = module.NAME_FIELD
        source = module.INPUT_COLUMNS
        na_allowed = lambda name: name not in NOT_NULLABLE_COLUMNS and name != name_field  # noqa: E731
        key = ["factory_code", name_field]
    columns = []
    for col in source:
        item = {"name": col["name"], "label": col.get("label", ""), "dtype": col.get("dtype", "str")}
        for opt in ("choices", "min", "max", "gt", "required"):
            if opt in col:
                item[opt] = list(col[opt]) if opt == "choices" else col[opt]
        item["na_allowed"] = na_allowed(col["name"])
        columns.append(item)
    names = [c["name"] for c in columns]
    return {"ef_code": ef_code, "table": table or "", "key": key, "columns": columns, "header": TAB.join(names)}


async def _row_actions(session: AsyncSession, module, table: str | None, text: str, replace: bool) -> list[dict]:
    """검증을 통과한 붙여넣기 내용의 행별 구분(추가/갱신) — 미리보기에서 확정 전에 보여준다.

    교체면 기존 데이터를 지우고 넣으므로 전부 추가. 같은 행 판정은 임포트와 같다
    (설비: 사업장 + 설비명, 참고표: 표의 key).
    """
    header, raw_rows = _parse_lines(text)
    if replace:
        return [{"row_number": n, "action": ACTION_INSERT} for n, _ in raw_rows]

    if table:
        spec = reference_specs(module)[table]
        model = spec["model"]
        probe = ReferenceImportResult(file_path="", ef_code=module.EF_CODE, table=table)
        fd, tmp_path = tempfile.mkstemp(prefix="eflms-paste-", suffix=".dat")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            rows = _parse_file(tmp_path, spec, probe)
        finally:
            _remove_quietly(tmp_path)
        actions = []
        for (n, _), row in zip(raw_rows, rows):
            cond = and_(*(getattr(model, k) == row[k] for k in spec["key"]))
            exists = (await session.execute(select(func.count()).select_from(model).where(cond))).scalar_one() > 0
            actions.append({"row_number": n, "action": ACTION_UPDATE if exists else ACTION_INSERT, "key": list(map(str, _key_of(spec, row)))})
        return actions

    names = [h.strip() for h in header]
    fi, ni = names.index("factory_code"), names.index(module.NAME_FIELD)
    existing = set(
        (await session.execute(
            select(Equipment.factory_code, Equipment.equipment_name).where(Equipment.ef_code == module.EF_CODE)
        )).all()
    )
    return [
        {
            "row_number": n,
            "action": ACTION_UPDATE if (cells[fi].strip(), cells[ni].strip()) in existing else ACTION_INSERT,
        }
        for n, cells in raw_rows
    ]


def _remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


async def import_text(
    session: AsyncSession,
    *,
    text: str,
    ef_code: str,
    table: str | None,
    replace: bool,
    check: bool,
) -> dict[str, Any]:
    """붙여넣은 탭 구분 텍스트를 검증(check=True) 또는 반영한다. table이 있으면 참고표, 없으면 설비 데이터.

    결과는 CLI의 JSON 로그와 같은 필드에 `kind`·`ok`를 더한 dict. 검증을 통과하면 `row_actions`(행별 추가/갱신).
    """
    module = _module_or_error(ef_code)
    if table:
        _reference_spec_or_error(module, table)

    fd, tmp_path = tempfile.mkstemp(prefix="eflms-paste-", suffix=".dat")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        if table:
            result = await import_reference_file(tmp_path, ef_code, table, session, replace=replace, dry_run=check)
        else:
            result = await import_file(tmp_path, ef_code, session, replace=replace, dry_run=check)
    finally:
        _remove_quietly(tmp_path)

    body = asdict(result)
    body["file_path"] = "붙여넣기"
    body["kind"] = "reference" if table else "equipment"
    body["ok"] = result.ok
    body["row_actions"] = await _row_actions(session, module, table, text, replace) if (result.ok and check) else []
    return body


# --- 내보내기 ---


def _format_cell(value: Any) -> str:
    """입력파일 규칙에 맞춘 칸 값 — null은 N/A, 날짜는 YYYY-MM-DD, 탭·줄바꿈은 공백(칸이 깨지지 않게)."""
    if value is None:
        return NA_TOKEN
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        if not math.isfinite(value):
            return NA_TOKEN
        return repr(value)
    text = str(value)
    return text.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _to_dat(header: list[str], rows: list[list[str]]) -> str:
    return "\n".join("\t".join(r) for r in [header, *rows]) + "\n"


async def _equipment_table(session: AsyncSession, ef_code: str) -> tuple[list[str], list[list[str]]]:
    """유형의 지금 설비 데이터를 입력파일 칸 규칙대로 — (헤더, 행 목록). 내려받기와 행 편집이 같이 쓴다.

    헤더 = 유형의 입력 컬럼 + 임포트 때 보관한 미등록 컬럼(있으면).
    """
    module = _module_or_error(ef_code)
    input_names = [col["name"] for col in module.INPUT_COLUMNS]
    ids = (
        await session.execute(
            select(Equipment.equipment_id).where(Equipment.ef_code == ef_code).order_by(Equipment.equipment_id)
        )
    ).scalars().all()

    extras: dict[int, dict[str, str | None]] = {}
    extra_names: list[str] = []
    if ids:
        stmt = (
            select(EquipmentExtraAttribute)
            .where(EquipmentExtraAttribute.equipment_id.in_(ids))
            .order_by(EquipmentExtraAttribute.id)
        )
        for attr in (await session.execute(stmt)).scalars():
            extras.setdefault(attr.equipment_id, {})[attr.column_name] = attr.value
            if attr.column_name not in extra_names and attr.column_name not in input_names:
                extra_names.append(attr.column_name)

    rows: list[list[str]] = []
    for eq_id in ids:
        loaded = await module.load_inputs(session, eq_id)
        if loaded is None:
            continue
        input_row, _as_of = loaded
        cells = [_format_cell(input_row.get(name)) for name in input_names]
        own_extras = extras.get(eq_id, {})
        # 미등록 컬럼은 원래 값(문자열) 그대로 — 그 설비에 없던 칸은 빈 값
        cells += [
            "" if (value := own_extras.get(name)) is None else _format_cell(value) for name in extra_names
        ]
        rows.append(cells)
    return input_names + extra_names, rows


async def _reference_table(session: AsyncSession, ef_code: str, table: str) -> tuple[list[str], list[list[str]]]:
    module = _module_or_error(ef_code)
    spec = _reference_spec_or_error(module, table)
    names = [col["name"] for col in spec["columns"]]
    table_rows = (await load_reference(session, module))[table]
    return names, [[_format_cell(row[n]) for n in names] for row in table_rows]


async def export_equipment(session: AsyncSession, ef_code: str) -> tuple[str, int]:
    """유형의 지금 설비 데이터를 입력파일과 같은 dat로 — 그대로 다시 넣을 수 있다(교체·백업용). 반환: (dat 텍스트, 설비 수)."""
    header, rows = await _equipment_table(session, ef_code)
    return _to_dat(header, rows), len(rows)


async def export_reference(session: AsyncSession, ef_code: str, table: str) -> tuple[str, int]:
    """참고표를 `import_reference`에 그대로 넣을 수 있는 dat로. 반환: (dat 텍스트, 행 수)."""
    header, rows = await _reference_table(session, ef_code, table)
    return _to_dat(header, rows), len(rows)


async def list_rows(session: AsyncSession, ef_code: str, table: str | None) -> dict[str, Any]:
    """행 편집(Stage 18)용 지금 데이터 — 내려받기와 같은 칸 값(null=N/A, 날짜 YYYY-MM-DD)을 표로.

    `key`(같은 행 판정 칸)는 화면이 기존 행에서 잠근다 — 바꾸면 이름 변경이 아니라 새 행 추가가 되기 때문.
    `columns`는 붙여넣기 양식과 같은 컬럼 설명, `extra_columns`는 양식에 없는(값만 보관하는) 칸.
    """
    spec = template(ef_code, table)
    if table:
        header, rows = await _reference_table(session, ef_code, table)
    else:
        header, rows = await _equipment_table(session, ef_code)
    known = {c["name"] for c in spec["columns"]}
    return {
        "ef_code": ef_code,
        "table": table or "",
        "key": spec["key"],
        "columns": spec["columns"],
        "header": header,
        "extra_columns": [name for name in header if name not in known],
        "rows": rows,
    }
