"""지표설명 상세 페이지 계산식(FORMULA_DOCS, Stage 22-11) — 설명이 실제 계산과 같은지."""
import copy

import pytest

from app.equipment_types import ef1_transformer, ef3_cable, ef7_battery
from app.equipment_types import formula_docs as fd
from app.equipment_types.registry import get_module, registered_codes


@pytest.mark.parametrize("code", registered_codes())
def test_docs_match_calculation(code):
    """등록된 모든 유형이 계산식 설명을 갖추고, 설명이 실제 계산과 같다(새 유형도 FORMULA_DOCS 필수)."""
    module = get_module(code)
    assert getattr(module, "FORMULA_DOCS", None), f"{code}: FORMULA_DOCS 없음 — docs/ARCHITECTURE.md 새 설비유형 추가 절차"
    assert fd.verify(module) == []


def _mutated_problems(module, mutate) -> str:
    original = module.FORMULA_DOCS
    try:
        docs = copy.deepcopy(original)
        mutate({d["field"]: d for d in docs}, docs)
        module.FORMULA_DOCS = docs
        return "\n".join(fd.verify(module))
    finally:
        module.FORMULA_DOCS = original


def test_verify_catches_comparison_default_and_chain_errors():
    """이상/초과 비교, 표에 없는 값의 감점, 중간값(판정)을 거치는 항목의 틀린 설명도 잡는다."""
    def mutate(by_field, docs):
        by_field["load_minus"]["bands"][0]["op"] = "gt"           # 81 '이상'을 '초과'로
        by_field["part_discharge_minus"]["default"] = 0           # 양호 외 값은 −20인데 0이라고
        by_field["acid_measure_minus"]["bands"][1]["value"] = 0.3  # 산가도 값 → 판정 → 감점 기준 틀림
        by_field["rep_time_minus"]["bands"][0]["minus"] = -10     # 1차전압 → 교체비용 → 감점 틀림
    problems = _mutated_problems(ef1_transformer, mutate)
    for field in ("load_minus", "part_discharge_minus", "acid_measure_minus", "rep_time_minus"):
        assert field in problems, problems


def test_verify_uses_mock_reference_for_reference_types():
    """참고표 유형(EF7)은 목업 참고표로 예시를 확인한다 — 예시가 틀리면 잡는다."""
    def mutate(by_field, docs):
        by_field["soh_minus"]["examples"][0]["expect"] = -1.0
    assert "soh_minus" in _mutated_problems(ef7_battery, mutate)


def test_verify_catches_wrong_descriptions():
    """설명이 틀리면(구간 감점·기준·등급·예시·빠진 항목) verify가 알려준다."""
    original = ef3_cable.FORMULA_DOCS
    try:
        docs = copy.deepcopy(original)
        by_field = {d["field"]: d for d in docs}
        by_field["load_minus"]["bands"][0]["minus"] = -30        # 감점 틀림
        by_field["temp_minus"]["bands"][1]["value"] = 85           # 기준 틀림
        by_field["emerge_resp_minus"]["table"][0]["minus"] = -9  # 등급 틀림
        by_field["failure_rate_minus"]["examples"][0]["expect"] = -3.3  # 예시 틀림(옛 298.15 값)
        docs.remove(by_field["tl_minus"])                        # 빠진 항목
        ef3_cable.FORMULA_DOCS = docs
        problems = "\n".join(fd.verify(ef3_cable))
    finally:
        ef3_cable.FORMULA_DOCS = original
    for field in ("load_minus", "temp_minus", "emerge_resp_minus", "failure_rate_minus", "설명 없음: tl_minus"):
        assert field in problems, problems


def test_payload_follows_breakdown_and_resolves_labels():
    body = fd.build_payload(ef3_cable)
    assert [a["axis"] for a in body["axes"]] == ["pof", "cof", "dof"]
    for axis in body["axes"]:
        assert [i["field"] for i in axis["items"]] == [b["field"] for b in ef3_cable.BREAKDOWN[axis["axis"]]]
    items = {i["field"]: i for a in body["axes"] for i in a["items"]}
    load = items["load_minus"]
    assert load["label"] == "부하율" and load["kind"] == "steps"
    assert load["inputs"] == [{"name": "max_load", "label": "최대부하"}, {"name": "cable_mva", "label": "회선별용량"}]
    assert items["failure_rate_minus"]["examples"][0] == {"text": "최고온도 25℃ · 상간온도차 2℃ · 사용 15년 → −1.7", "expect": -1.7}
    assert "inputs" not in items["failure_rate_minus"]["examples"][0]
    assert any("N/A" in rule for rule in body["common_rules"])


def test_payload_shapes_for_other_types():
    """비교 방식(이상/초과)·판정 기준표·숫자 등급(문자로 표시)·감점 항목 이름이 계산 컬럼과 다른 항목."""
    ef1 = {i["field"]: i for a in fd.build_payload(ef1_transformer)["axes"] for i in a["items"]}
    assert ef1["moisture_minus"]["bands"] == [{"value": 50, "op": "gt", "minus": -8}, {"value": 40, "op": "ge", "minus": -4}]
    assert ef1["dga_minus"]["summed"] is False and ef1["dga_minus"]["table"]["columns"][0] == "가스(ppm)"
    assert ef1["first_voltage_minus"]["inputs"] == [{"name": "voltage", "label": "전압"}]
    ef7 = {i["field"]: i for a in fd.build_payload(ef7_battery)["axes"] for i in a["items"]}
    assert ef7["model_gen_minus"]["table"][0] == {"value": "2", "minus": -12}


async def test_formulas_api(client):
    for code in registered_codes():
        resp = await client.get(f"/api/equipment-types/{code}/formulas")
        assert resp.status_code == 200
        body = resp.json()
        module = get_module(code)
        assert body["ef_code"] == code and body["documented"] is True
        assert sum(len(a["items"]) for a in body["axes"]) == sum(len(v) for v in module.BREAKDOWN.values())
    assert (await client.get("/api/equipment-types/EF99/formulas")).status_code == 404
