"""감점 항목 계산식 설명(FORMULA_DOCS) — 지표설명 상세 페이지(/guide/formulas, Stage 22-11).

각 설비유형 모듈이 감점 항목마다 "어떻게 계산되는지"를 데이터로 선언한다(선택 항목 `FORMULA_DOCS`).
화면은 이것을 표·수식으로 그린다. 설명이 실제 계산과 어긋나지 않도록 `verify()`가 선언된 표의 경계값·
모든 등급·예시를 실제 계산(CALCULATED_COLUMNS)에 넣어 같은 감점이 나오는지 확인한다
(`tests/test_formula_docs.py`). 계산식을 바꾸면 이 설명도 같이 고쳐야 테스트가 통과한다.

항목 형태(kind):
- steps  : 구간표 — 값이 기준을 넘으면(초과 gt / 이상 ge) 감점, 위에서부터 처음 맞는 구간.
           bands = [(기준, 감점[, op]), ...] 큰 기준부터
- map    : 등급표 — 입력값별 감점(표에 없는 값은 default)
- worse  : 1·2 두 칸 중 나쁜(더 작은) 감점 — 같은 등급표를 두 칸에 적용
- expr   : 수식 — LaTeX 식과 변수 설명, 실제 계산으로 확인한 예시(판정 기준표 table을 곁들일 수 있음)

확인 방법: 구간표·등급표는 기본 입력 행에 그 값만 바꿔 넣고 유형의 계산 컬럼을 실제 순서대로 돌린다(na.evaluate —
중간값을 거치는 항목, 예: 산가도 값 → 판정 → 감점도 그대로 확인). 값이 중간 계산값(예: 부하율)이면 그 칸을 그 값으로
고정한다. 감점 항목 이름이 계산 컬럼 이름과 다르면(EF1 first_voltage_minus = 1st_voltage_minus) 모듈의
FORMULA_CALC_NAMES로 잇는다. 참고표가 있는 유형(EF7)은 목업 참고표(mock_rows)로 계산한다.
"""
from __future__ import annotations

import random
from datetime import date
from typing import Any

from app.equipment_types.na import evaluate
from app.equipment_types.rounding import round1

AXIS_LABELS = {"pof": "POF (설비상태)", "cof": "COF (고장영향성)", "dof": "DOF (고장예방력)"}

COMMON_RULES = [
    "각 축 점수 = 100 + 그 축 감점 합계. 감점은 소수 첫째 자리로 반올림한 뒤 더합니다.",
    "입력값이 N/A(값 모름)인 항목은 감점 0으로 계산합니다. 수식에 쓰이는 값 중 하나라도 N/A면 그 항목은 0입니다.",
    "사용년수(경과연수) = (점수 기준일 − 가동년월) ÷ 365, 소수 첫째 자리. 기준일이 지나면 커지므로 날마다 점수가 다시 계산됩니다.",
]


# --- 항목 선언 도우미 ---------------------------------------------------------


def steps(
    field: str,
    var: str,
    bands: list[tuple],
    *,
    var_label: str,
    unit: str = "",
    op: str = "gt",
    inputs: list[str] | None = None,
    otherwise: float = 0,
    tex: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """값(var)이 기준을 넘으면 감점. bands는 큰 기준부터 [(기준, 감점), ...] — op "gt"(초과)/"ge"(이상),
    구간마다 다르면 (기준, 감점, op). 어느 구간에도 안 맞으면 otherwise."""
    out = []
    for band in bands:
        t, m, band_op = (*band, op) if len(band) == 2 else band
        if band_op not in ("gt", "ge"):
            raise ValueError(f"{field}: 모르는 비교 {band_op}")
        out.append({"value": t, "op": band_op, "minus": m})
    return {
        "field": field, "kind": "steps", "var": var, "var_label": var_label, "unit": unit,
        "bands": out, "otherwise": otherwise,
        "inputs": inputs if inputs is not None else [var], "tex": tex, "note": note,
    }


def mapping(
    field: str,
    var: str,
    table: dict[Any, float],
    *,
    default: float = 0,
    default_label: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """입력값(var)별 감점. 표에 없는 값은 default(default_label로 어떤 값인지 설명)."""
    return {
        "field": field, "kind": "map", "var": var, "inputs": [var],
        "table": [{"value": k, "minus": v} for k, v in table.items()],
        "default": default, "default_label": default_label, "note": note,
    }


def worse(field: str, var1: str, var2: str, table: dict[str, float], *, note: str | None = None) -> dict[str, Any]:
    """var1·var2에 같은 등급표를 적용해 나쁜(더 작은) 감점. 표에 없는 값·빈칸은 0으로 비교."""
    return {
        "field": field, "kind": "worse", "inputs": [var1, var2],
        "table": [{"value": k, "minus": v} for k, v in table.items()], "default": 0, "note": note,
    }


def expr(
    field: str,
    tex: list[str],
    *,
    inputs: list[str],
    symbols: list[dict[str, str]] | None = None,
    examples: list[dict[str, Any]] | None = None,
    table: dict[str, list] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """수식 항목. tex = 화면에 차례로 보여줄 LaTeX 식들. symbols = [{sym, label}] 변수 설명.
    table = {"columns": [...], "rows": [[...], ...]} 판정 기준표(화면 표시용 — 맞는지는 examples로 확인).

    examples = [{"text": 화면 문구, "inputs": 입력값 덮어쓰기, "as_of": 기준일, "expect": 감점}] —
    verify()가 유형 calculate()로 다시 계산해 expect와 같은지 본다.
    """
    return {
        "field": field, "kind": "expr", "tex": tex, "inputs": inputs,
        "symbols": symbols or [], "examples": examples or [], "table": table, "note": note,
    }


def example(text: str, expect: float, *, as_of: date | None = None, **inputs: Any) -> dict[str, Any]:
    return {"text": text, "expect": expect, "as_of": as_of, "inputs": inputs}


def signed(value: float) -> str:
    """예시 문구용 감점 표기 — 음수는 유니코드 마이너스(−1.6), 0은 0."""
    if value == 0:
        return "0"
    text = f"{abs(value):g}" if float(value).is_integer() else f"{abs(value):.1f}"
    return f"−{text}" if value < 0 else f"+{text}"


# 예시용 날짜 —가동 2010-01-01, 점수 기준일 2025-01-01이면 사용년수 15.0년
EXAMPLE_START = date(2010, 1, 1)
EXAMPLE_AS_OF = date(2025, 1, 1)


def age_item(field: str = "age_minus") -> dict[str, Any]:
    """경과연수(-사용년수) — 모든 유형 공통 형태."""
    return expr(
        field, [r"\text{감점} = -\,\text{사용년수}"], inputs=["operation_start_time"],
        symbols=[{"sym": "사용년수", "label": "(점수 기준일 − 가동(설치)년월) ÷ 365, 소수 첫째 자리"}],
        examples=[example("사용 15년 → −15.0", -15.0, as_of=EXAMPLE_AS_OF, operation_start_time=EXAMPLE_START)],
    )


def weibull_tex(scale: str, shape: str, factor: str, *, life: str = r"t", temp: bool = False) -> list[str]:
    """와이블 고장확률 감점 식 — R = exp(-(t/η)^β), 감점 = (R − 1) × 100 × 배율. temp면 척도를 전기실 온도로 보정."""
    eta = rf"\eta = {scale} \times 2^{{(25 - T)/10}}" if temp else rf"\eta = {scale}"
    return [
        rf"R = \exp\!\left[-\left(\dfrac{{{life}}}{{\eta}}\right)^{{{shape}}}\right],\quad {eta}",
        rf"\text{{감점}} = (R - 1) \times 100 \times {factor}",
    ]


# --- 화면용 응답 --------------------------------------------------------------


def build_payload(module) -> dict[str, Any]:
    """유형 하나의 계산식 설명 — 축(BREAKDOWN 순서)별 항목에 라벨·입력 컬럼 한글명을 붙인다."""
    docs = {d["field"]: d for d in getattr(module, "FORMULA_DOCS", [])}
    labels = {c["name"]: c.get("label") or c["name"] for c in module.INPUT_COLUMNS}
    axes = []
    for axis, items in module.BREAKDOWN.items():
        out = []
        for item in items:
            doc = docs.get(item["field"])
            if doc is None:
                continue
            entry = {k: v for k, v in doc.items() if k != "examples"}
            if "table" in doc and doc["kind"] in ("map", "worse"):
                entry["table"] = [{**t, "value": str(t["value"])} for t in doc["table"]]
            entry["examples"] = [{"text": e["text"], "expect": e["expect"]} for e in doc.get("examples", [])]
            entry["label"] = item["label"]
            entry["group"] = item.get("group")
            entry["summed"] = item.get("summed", True)
            entry["inputs"] = [{"name": n, "label": labels.get(n, n)} for n in doc["inputs"]]
            out.append(entry)
        axes.append({"axis": axis, "label": AXIS_LABELS[axis], "items": out})
    return {
        "ef_code": module.EF_CODE,
        "ef_name": module.EF_NAME,
        "documented": bool(docs),
        "total_tex": r"\text{종합점수} = 0.5 \times \text{POF} + 0.3 \times \text{COF} + 0.2 \times \text{DOF}",
        "axes": axes,
        "common_rules": COMMON_RULES + list(getattr(module, "FORMULA_NOTES", [])),
    }


# --- 실제 계산과 일치 확인 ------------------------------------------------------


def _calc_name(module, field: str) -> str:
    return getattr(module, "FORMULA_CALC_NAMES", {}).get(field, field)


def _choices(module, name: str) -> list[Any]:
    for col in module.INPUT_COLUMNS:
        if col["name"] == name:
            values = list(col.get("choices", []))
            return values + [""] if col.get("allow_blank") else values
    return []


def steps_value(doc: dict, x: float) -> float:
    for band in doc["bands"]:
        if (x > band["value"]) if band["op"] == "gt" else (x >= band["value"]):
            return band["minus"]
    return doc["otherwise"]


def _base_row(module) -> dict:
    state = random.getstate()
    random.seed(20261124)
    try:
        return module.generate_input_row()
    finally:
        random.setstate(state)


def default_calc_kwargs(module) -> dict:
    """참고표가 있는 유형은 목업 참고표로 계산한다(DB 없이 확인)."""
    tables = getattr(module, "REFERENCE_TABLES", None)
    if not tables:
        return {}
    return {"reference": {name: [dict(r) for r in spec["mock_rows"]] for name, spec in tables.items()}}


def _evaluate_with(module, values: dict, calc_kwargs: dict) -> dict:
    """기본 입력 행에 values를 넣고 계산 컬럼을 실제 순서대로 돌린다. values의 이름이 계산 컬럼이면 그 칸을 고정."""
    calculated = {c["name"] for c in module.CALCULATED_COLUMNS}
    row = {**_base_row(module), **{k: v for k, v in values.items() if k not in calculated}}
    if "reference" in calc_kwargs:
        row["_reference"] = calc_kwargs["reference"]  # 참고표 유형의 calculate()와 같은 방식(EF7)
    columns = [
        {"name": c["name"], "formula": (lambda _row, v=values[c["name"]]: v)} if c["name"] in values else c
        for c in module.CALCULATED_COLUMNS
    ]
    return evaluate(row, columns, None)


_OTHER = "(표에 없는 값)"


def verify(module, calc_kwargs: dict | None = None) -> list[str]:
    """설명과 실제 계산이 다른 곳 목록(비면 일치). 감점 항목이 빠졌거나 남는 것도 알린다."""
    calc_kwargs = default_calc_kwargs(module) if calc_kwargs is None else calc_kwargs
    problems: list[str] = []
    docs = getattr(module, "FORMULA_DOCS", [])
    fields = [item["field"] for items in module.BREAKDOWN.values() for item in items]
    declared = [d["field"] for d in docs]
    for f in fields:
        if f not in declared:
            problems.append(f"설명 없음: {f}")
    for f in declared:
        if f not in fields:
            problems.append(f"BREAKDOWN에 없는 항목: {f}")
        if declared.count(f) > 1:
            problems.append(f"중복: {f}")

    def check(field: str, values: dict, expected: float, what: str) -> None:
        got = _evaluate_with(module, values, calc_kwargs)[_calc_name(module, field)]
        if got != round1(float(expected)):
            problems.append(f"{field} {what}: 설명 {expected} / 계산 {got}")

    for doc in docs:
        field, kind = doc["field"], doc["kind"]
        if kind == "steps":
            points = set()
            for b in doc["bands"]:
                points |= {b["value"], round(b["value"] + 0.01, 6), round(b["value"] - 0.01, 6)}
            points.add(min(b["value"] for b in doc["bands"]) - 1)
            for x in sorted(points):
                check(field, {doc["var"]: x}, steps_value(doc, x), f"{doc['var']}={x}")
        elif kind == "map":
            table = {t["value"]: t["minus"] for t in doc["table"]}
            values = list(table) + [v for v in _choices(module, doc["var"]) if v not in table]
            if all(isinstance(v, str) for v in values):
                values.append(_OTHER)  # 표에 없는 문자열 → default
            for v in values:
                check(field, {doc["var"]: v}, table.get(v, doc["default"]), f"{doc['var']}={v!r}")
        elif kind == "worse":
            table = {t["value"]: t["minus"] for t in doc["table"]}
            a, b = doc["inputs"]
            values = list(dict.fromkeys(list(table) + _choices(module, a)))
            for va in values:
                for vb in values:
                    expected = min(table.get(va, 0), table.get(vb, 0))
                    check(field, {a: va, b: vb}, expected, f"{a}={va!r},{b}={vb!r}")
        elif kind == "expr":
            if not doc["examples"]:
                problems.append(f"{field}: 수식 항목에 확인용 예시 없음")
            for ex in doc["examples"]:
                row = {**_base_row(module), **ex["inputs"]}
                result = module.calculate(row, as_of=ex.get("as_of"), **calc_kwargs)
                got = result[_calc_name(module, field)]
                if got != ex["expect"]:
                    problems.append(f"{field} 예시 '{ex['text']}': 설명 {ex['expect']} / 계산 {got}")
        else:
            problems.append(f"{field}: 모르는 형태 {kind}")
    return problems
