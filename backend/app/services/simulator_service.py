"""점수 시뮬레이터 (Stage 19) — 화면에서 넣은 입력값으로 POF·COF·DOF·종합점수를 계산만 한다(DB에 쓰지 않음).

- 입력 양식은 관리자 데이터 입력 양식(`data_admin_service.template`)을, 값 검사는 데이터 입력과 같은 규칙
  (`import_service`의 형식 변환·허용값·N/A)을 그대로 쓴다 — 붙여넣기로 들어갈 수 있는 값이면 여기서도 계산된다.
- 사업장은 DB에 그 유형의 설비가 있는 사업장만 고를 수 있다(실제 데이터는 지금 H1). 사업장별 참고표(EF7 방전이력,
  `reference_data` "사업장별 참고표")에 행이 없는 사업장은 빼고 계산을 거부한다 — 관리자가 그 사업장 행을 넣으면
  코드 변경 없이 바로 계산 대상이 된다.
- 계산 기준일은 오늘. 시작값의 결과(baseline)도 같은 기준일로 계산해, 화면의 차이는 바꾼 값 때문만 나오게 한다.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import today_kst
from app.db.models import Equipment
from app.equipment_types.na import is_na_token
from app.equipment_types.registry import UnknownEquipmentTypeError, get_module
from app.schemas.simulator import (
    SimulatorEquipment,
    SimulatorExcludedSite,
    SimulatorFieldError,
    SimulatorForm,
    SimulatorItem,
    SimulatorResult,
    SimulatorSample,
    SimulatorSite,
)
from app.services import data_admin_service
from app.services.equipment_service import classify_status
from app.services.import_service import NOT_NULLABLE_COLUMNS, _cast_value, _check_allowed
from app.services.reference_data import calc_options, calculable_sites

NA_TOKEN = "N/A"


class SimulatorError(ValueError):
    """잘못된 요청(모르는 유형, 다른 유형의 설비 등) — 라우터가 404로 바꾼다."""


def _module(ef_code: str):
    try:
        return get_module(ef_code)
    except UnknownEquipmentTypeError as exc:
        raise SimulatorError(f"등록되지 않은 설비유형: {ef_code}") from exc


async def _site_counts(session: AsyncSession, ef_code: str) -> list[tuple[str, int]]:
    stmt = (
        select(Equipment.factory_code, func.count())
        .where(Equipment.ef_code == ef_code)
        .group_by(Equipment.factory_code)
        .order_by(Equipment.factory_code)
    )
    return [(site, count) for site, count in (await session.execute(stmt)).all()]


async def _sites(session: AsyncSession, module, options: dict[str, Any]) -> tuple[list[tuple[str, int]], dict[str, list[str]]]:
    """(계산할 수 있는 (사업장, 설비 수), {제외된 사업장: 빠진 참고표 라벨})."""
    counts = await _site_counts(session, module.EF_CODE)
    ok, excluded = calculable_sites(module, options, [site for site, _ in counts])
    by_site = dict(counts)
    return [(site, by_site[site]) for site in ok], excluded


def _excluded_reason(labels: list[str]) -> str:
    return f"{'·'.join(labels)} 참고표에 이 사업장 데이터가 없음"


async def form(session: AsyncSession, ef_code: str) -> SimulatorForm:
    module = _module(ef_code)
    template = data_admin_service.template(ef_code, None)
    options = await calc_options(session, module)
    sites, excluded = await _sites(session, module, options)
    site_codes = [site for site, _ in sites]
    equipment: list[SimulatorEquipment] = []
    if site_codes:
        stmt = (
            select(Equipment.equipment_id, Equipment.factory_code, Equipment.equipment_name)
            .where(Equipment.ef_code == ef_code, Equipment.factory_code.in_(site_codes))
            .order_by(Equipment.factory_code, Equipment.equipment_name)
        )
        equipment = [
            SimulatorEquipment(equipment_id=i, factory_code=f, equipment_name=n) for i, f, n in (await session.execute(stmt)).all()
        ]
    return SimulatorForm(
        ef_code=module.EF_CODE,
        ef_name=module.EF_NAME,
        name_field=module.NAME_FIELD,
        columns=template["columns"],
        header=template["header"],
        sites=[SimulatorSite(factory_code=site, equipment_count=count) for site, count in sites],
        excluded_sites=[SimulatorExcludedSite(factory_code=site, reason=_excluded_reason(labels)) for site, labels in excluded.items()],
        equipment=equipment,
    )


def _format(value: Any) -> str:
    # 내려받기와 같은 칸 표기(null은 N/A, 날짜는 YYYY-MM-DD) — 그대로 다시 넣으면 같은 값이 된다.
    return data_admin_service._format_cell(value)


async def sample(session: AsyncSession, ef_code: str, equipment_id: int | None) -> SimulatorSample:
    """시작값 — equipment_id가 있으면 그 설비의 저장된 입력값, 없으면 예시값(목업 생성기, 사업장은 고를 수 있는 첫 곳)."""
    module = _module(ef_code)
    options = await calc_options(session, module)
    sites, _ = await _sites(session, module, options)
    site_codes = [site for site, _ in sites]
    if equipment_id is not None:
        equipment = await session.get(Equipment, equipment_id)
        if equipment is None or equipment.ef_code != module.EF_CODE:
            raise SimulatorError(f"{ef_code} 설비가 아님: {equipment_id}")
        if equipment.factory_code not in site_codes:
            raise SimulatorError(f"{equipment.factory_code} 사업장은 시뮬레이터에서 계산할 수 없음")
        loaded = await module.load_inputs(session, equipment_id)
        if loaded is None:
            raise SimulatorError(f"입력값을 불러올 수 없는 설비: {equipment_id}")
        row, source = loaded[0], "equipment"
    else:
        row, source = module.generate_input_row(), "example"
        row["factory_code"] = site_codes[0] if site_codes else ""
    values = {col["name"]: _format(row.get(col["name"])) for col in module.INPUT_COLUMNS}
    values["EF_code"] = module.EF_CODE
    baseline = _calculate(module, options, site_codes, values)
    return SimulatorSample(values=values, source=source, equipment_id=equipment_id, baseline=baseline)


def _parse(module, values: dict[str, str], site_codes: list[str]) -> tuple[dict, list[SimulatorFieldError]]:
    """데이터 입력(import_service)과 같은 규칙으로 칸 값을 바꾼다 — N/A, 형식, 허용값, 필수 칸."""
    row: dict[str, Any] = {}
    errors: list[SimulatorFieldError] = []
    for col in module.INPUT_COLUMNS:
        name = col["name"]
        raw = "" if values.get(name) is None else str(values.get(name))
        if name == "EF_code":
            row[name] = module.EF_CODE
            continue
        if is_na_token(raw):
            if name in NOT_NULLABLE_COLUMNS or name == module.NAME_FIELD:
                errors.append(SimulatorFieldError(column=name, raw_value=raw, reason="N/A 불가(필수 칸)"))
            else:
                row[name] = None
            continue
        try:
            value = _cast_value(raw, col.get("dtype", "str"))
        except (ValueError, TypeError):
            dtype = col.get("dtype", "str")
            if raw.strip() == "":
                reason = "빈 값 — 값을 넣거나 N/A"
            elif dtype == "date":
                reason = "날짜 형식이 아님(YYYY-MM-DD)"
            else:
                reason = {"int": "정수가 아님", "float": "숫자가 아님"}.get(dtype, f"{dtype} 형식이 아님")
            errors.append(SimulatorFieldError(column=name, raw_value=raw, reason=reason))
            continue
        reason = _check_allowed(value, col)
        if reason:
            errors.append(SimulatorFieldError(column=name, raw_value=raw, reason=reason))
        row[name] = value
    site = row.get("factory_code")
    if site is not None and site != "" and site not in site_codes:
        errors.append(
            SimulatorFieldError(column="factory_code", raw_value=str(site), reason="시뮬레이터에서 계산할 수 없는 사업장")
        )
    elif not site and not any(e.column == "factory_code" for e in errors):
        errors.append(SimulatorFieldError(column="factory_code", raw_value="", reason="사업장을 고르세요"))
    return row, errors


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _calculate(module, options: dict[str, Any], site_codes: list[str], values: dict[str, str]) -> SimulatorResult:
    row, errors = _parse(module, values, site_codes)
    if errors:
        return SimulatorResult(ok=False, errors=errors)
    as_of = today_kst()
    try:
        out = module.calculate(row, as_of=as_of, **options)
    except Exception as exc:  # 원본 계산식이 처리하지 못한 값 조합 — 화면에 그대로 알린다
        return SimulatorResult(
            ok=False, errors=[SimulatorFieldError(column="(계산)", raw_value="", reason=f"{type(exc).__name__}: {exc}")]
        )
    breakdown = {
        axis: [SimulatorItem(**item, value=_number(out.get(item["field"]))) for item in items]
        for axis, items in module.BREAKDOWN.items()
    }
    return SimulatorResult(
        ok=True,
        as_of=as_of.isoformat(),
        pof=out["pof"],
        cof=out["cof"],
        dof=out["dof"],
        total_score=out["total_score"],
        status=classify_status(out["pof"], out["cof"], out["dof"]),
        breakdown=breakdown,
    )


async def calculate(session: AsyncSession, ef_code: str, values: dict[str, str]) -> SimulatorResult:
    module = _module(ef_code)
    options = await calc_options(session, module)
    sites, _ = await _sites(session, module, options)
    return _calculate(module, options, [site for site, _ in sites], values)
