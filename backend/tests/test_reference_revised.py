"""ref_data_revised/ 수정본 = 시스템 계산 (2026-11-19).

수정본은 원본 계산 양식(ref_data/)에 시스템 계산 규칙(감점 소수 계산·소수 첫째 자리·EF2 결정)을 반영한
참고용 파일이다. 같은 입력이면 시스템 계산기와 모든 계산 컬럼이 같아야 한다 — 시스템 계산을 바꾸고
수정본을 안 고치면 이 테스트가 실패한다. 수정본은 import만 하고 __pycache__도 만들지 않는다.
"""
import importlib
import importlib.util
import random
import sys
from datetime import date, timedelta

import pytest

from app.core.config import BACKEND_DIR
from app.equipment_types.registry import get_module
from app.services.reference_data import has_reference, mock_reference

REVISED_DIR = BACKEND_DIR.parent / "ref_data_revised"
REVISED_FILES = {
    "EF1": "schema_eflms.py", "EF2": "schema_eflms_gis.py", "EF3": "schema_eflms_cable.py",
    "EF4": "schema_eflms_subaejeon.py", "EF5": "schema_eflms_ups.py", "EF6": "schema_eflms_vdp.py",
    "EF7": "schema_eflms_battery.py",
}
# 감점 분기별 기준 입력이 있는 유형 테스트(경계값 입력을 함께 대조한다)
BRANCH_TESTS = {
    "EF2": "tests.test_ef2_gis", "EF3": "tests.test_ef3_cable", "EF4": "tests.test_ef4_switchgear",
    "EF5": "tests.test_ef5_ups", "EF6": "tests.test_ef6_vdp", "EF7": "tests.test_ef7_battery",
}


def _load_revised(ef_code):
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location(f"revised_{ef_code}", REVISED_DIR / REVISED_FILES[ef_code])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = prev
    return module


def _revised_calculate(revised, row):
    row = dict(row)
    for col in revised.CALCULATED_COLUMNS:
        row[col["name"]] = col["formula"](row)
    return row


def _rows(ef_code, module):
    random.seed(20261119)
    rows = [module.generate_input_row() for _ in range(300)]
    for years in (0.4, 7.5, 12.7, 19.95, 31.3):
        row = module.generate_input_row()
        row["operation_start_time"] = date.today() - timedelta(days=int(years * 365))
        rows.append(row)
    if ef_code in BRANCH_TESTS:
        t = importlib.import_module(BRANCH_TESTS[ef_code])
        rows += [t._base_row(**overrides) for overrides, _, _ in t.BRANCHES]
    return rows


@pytest.mark.parametrize("ef_code", list(REVISED_FILES))
def test_revised_reference_matches_system(ef_code):
    module = get_module(ef_code)
    revised = _load_revised(ef_code)
    kwargs = {"reference": mock_reference(module)} if has_reference(module) else {}
    names = [c["name"] for c in module.CALCULATED_COLUMNS]
    assert names == [c["name"] for c in revised.CALCULATED_COLUMNS]
    assert [c["name"] for c in module.INPUT_COLUMNS] == [c["name"] for c in revised.INPUT_COLUMNS]
    for row in _rows(ef_code, module):
        ours = module.calculate(row, **kwargs)
        theirs = _revised_calculate(revised, row)
        for name in names:
            assert ours[name] == theirs[name], (ef_code, name, ours[name], theirs[name])


@pytest.mark.parametrize("ef_code", list(REVISED_FILES))
def test_revised_reference_marks_every_deduction_as_float(ef_code):
    revised = _load_revised(ef_code)
    for col in revised.CALCULATED_COLUMNS:
        if col["name"].endswith("_minus") and "dtype" in col:
            assert col["dtype"] == "float", (ef_code, col["name"])


def test_original_reference_is_untouched_by_revised_copy():
    """원본(ref_data/)은 수정본과 별개 — 원본은 여전히 정수 경과연수 감점(-floor)이다."""
    original = (BACKEND_DIR.parent / "ref_data" / "schema_eflms_ups.py").read_text(encoding="utf-8")
    revised = (REVISED_DIR / "schema_eflms_ups.py").read_text(encoding="utf-8")
    assert "math.floor(row[\"operation_year\"])" in original
    assert "math.floor(row[\"operation_year\"])" not in revised
