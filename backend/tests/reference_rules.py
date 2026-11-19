"""원본 대조 테스트 공통 — 원본 계산 툴 공식에 우리 계산 규칙을 얹은 기대값 (2026-11-19).

원본(ref_data/)의 CALCULATED_COLUMNS를 위에서부터 그대로 돌리되,
- 의도적으로 바꾼 공식(`changes`)만 테스트가 명시한 새 공식으로 대신한다 — 공통은 운전년수(엑셀식 반올림)와
  경과연수 감점(-운전년수, 원본은 -floor), 유형별로는 감점을 정수로 만들던 round()/int()를 뺀 공식.
- 감점(`_minus`)과 점수 지표는 계산 직후 float·소수 첫째 자리로 반올림한다(app/equipment_types/na.py와 같은 순서).
그 밖의 공식은 원본 그대로라, 바꾸지 않은 계산이 원본과 같은지는 계속 대조된다.
"""
from app.equipment_types.rounding import SCORE_FIELDS, is_deduction, round1


def operation_year(row):
    return round1((row["today"] - row["operation_start_time"]).days / 365)


COMMON_CHANGES = {
    "operation_year": operation_year,
    "age_minus": lambda row: -row["operation_year"],
}


def reference_formula(ref, name):
    """원본의 공식 하나(바꾼 공식이 원본 값에 무언가를 더하는 경우에 쓴다)."""
    return next(col["formula"] for col in ref.CALCULATED_COLUMNS if col["name"] == name)


def expected_from_reference(ref, row, changes=None):
    formulas = {**COMMON_CHANGES, **(changes or {})}
    row = dict(row)
    for col in ref.CALCULATED_COLUMNS:
        name = col["name"]
        value = formulas.get(name, col["formula"])(row)
        if value is not None and (is_deduction(name) or name in SCORE_FIELDS):
            value = round1(float(value))
        row[name] = value
    return row
