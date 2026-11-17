"""설비유형 참고표 — 계산에 쓰는 별도 표를 읽어 계산기에 넘기는 공통 도우미 (Stage 15-0).

대부분의 설비유형은 입력 한 행만으로 계산하지만, EF7(배터리)처럼 설비에 딸리지 않은 표(방전이력·온도감소계수)를
함께 읽어야 하는 유형이 있다. 그런 유형은 모듈에 `REFERENCE_TABLES`를 선언하고, `calculate(row, reference=...)`로
표 내용을 받는다(2026-11-16 사용자 결정 — 계산에는 DB에 지금 들어 있는 참고표를 쓴다).

계산기를 부르는 곳(임포트·시드·예측 그래프·참고표 재계산)은 `calc_options()`를 펼쳐 넘기기만 한다 — 참고표가 없는
유형(EF1~EF6)은 빈 dict라 호출이 예전과 똑같다.

REFERENCE_TABLES 형식(유형 모듈):
    {"<표 이름>": {
        "label": "방전이력",                 # 화면·CLI 표시용
        "model": <SQLAlchemy 모델>,           # 설비에 딸리지 않는 테이블(equipment_id 없음)
        "columns": [{name, label, dtype, required?/min?/max?/gt?}, ...],  # dat 헤더 = name
        "key": ("factory_code", "disch_date"),  # 같은 행 판정(넣기 = 갱신/추가, 파일 안 중복 거부)
        "mock_rows": [...],                    # 목업(시드)용 — 표가 비어 있을 때만 넣는다
    }}
"""
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def reference_specs(module) -> dict[str, dict[str, Any]]:
    return getattr(module, "REFERENCE_TABLES", None) or {}


def has_reference(module) -> bool:
    return bool(reference_specs(module))


def _column_names(spec: dict) -> list[str]:
    return [c["name"] for c in spec["columns"]]


async def count_rows(session: AsyncSession, model) -> int:
    return await session.scalar(select(func.count()).select_from(model)) or 0


async def load_reference(session: AsyncSession, module) -> dict[str, list[dict]]:
    """유형의 참고표 전부를 {표 이름: [행 dict, ...]}로 읽는다(같은 행 판정 열쇠 순 정렬)."""
    out: dict[str, list[dict]] = {}
    for name, spec in reference_specs(module).items():
        model, names = spec["model"], _column_names(spec)
        stmt = select(model).order_by(*(getattr(model, k) for k in spec["key"]))
        out[name] = [{n: getattr(obj, n) for n in names} for obj in (await session.execute(stmt)).scalars()]
    return out


async def calc_options(session: AsyncSession, module) -> dict[str, Any]:
    """`module.calculate(row, **calc_options(...))`로 펼쳐 넘길 추가 인자 — 참고표가 없는 유형은 빈 dict."""
    if not has_reference(module):
        return {}
    return {"reference": await load_reference(session, module)}


def empty_reference_warnings(module, options: dict[str, Any]) -> list[str]:
    """비어 있는 참고표 경고 — 원본 수식이 합계 방식이라 빈 표는 오류가 아니라 0으로 계산된다."""
    reference = options.get("reference") or {}
    return [
        f"참고표 '{spec['label']}'({name})이 비어 있음 — 계산에서 0으로 처리"
        for name, spec in reference_specs(module).items()
        if not reference.get(name)
    ]


def mock_reference(module) -> dict[str, list[dict]]:
    """목업 참고표(유형 모듈의 mock_rows) — DB 없이 계산할 때(테스트) 쓴다."""
    return {name: [dict(r) for r in spec["mock_rows"]] for name, spec in reference_specs(module).items()}


async def ensure_mock_reference(session: AsyncSession, module) -> list[str]:
    """비어 있는 참고표에만 목업 행을 넣는다(시드용). 채운 표 이름을 돌려준다. commit하지 않는다.

    이미 행이 있는 표(실데이터 포함)는 건드리지 않는다.
    """
    filled = []
    for name, spec in reference_specs(module).items():
        if await count_rows(session, spec["model"]) == 0:
            session.add_all(spec["model"](**row) for row in spec["mock_rows"])
            filled.append(name)
    if filled:
        await session.flush()
    return filled
