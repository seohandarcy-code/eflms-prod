import { describe, expect, it } from "vitest";
import type { SimulatorColumn, SimulatorResult } from "../api/simulator";
import { blankValues, changedFields, deltaLabel, dtypeLabel, errorsByField, ruleLabel, topDeductions } from "./simulator";

const col = (over: Partial<SimulatorColumn>): SimulatorColumn => ({ name: "x", label: "", dtype: "str", na_allowed: true, ...over });

function result(over: Partial<SimulatorResult> = {}): SimulatorResult {
  return {
    ok: true,
    errors: [],
    as_of: "2026-11-18",
    pof: 40,
    cof: 70,
    dof: 80,
    total_score: 57,
    status: "review",
    breakdown: {
      pof: [
        { field: "a", label: "경과년수", group: null, summed: true, value: -15 },
        { field: "b", label: "fan", group: null, summed: true, value: -27 },
        { field: "c", label: "참고용", group: null, summed: false, value: -50 },
        { field: "d", label: "소음", group: null, summed: true, value: 0 },
        { field: "e", label: "N/A 항목", group: null, summed: true, value: null },
      ],
      dof: [{ field: "f", label: "온라인진단", group: null, summed: true, value: -9 }],
    },
    ...over,
  };
}

describe("simulator utils", () => {
  it("finds fields that differ from the start values", () => {
    expect(changedFields({ a: "1", b: " 2 ", c: "N/A" }, { a: "1", b: "2", c: "3" })).toEqual(["c"]);
  });

  it("blanks values but keeps site and type code", () => {
    const columns = [col({ name: "factory_code", na_allowed: false }), col({ name: "EF_code", na_allowed: false }), col({ name: "load", dtype: "float" }), col({ name: "eqp_id", na_allowed: false })];
    expect(blankValues(columns, { factory_code: "H1", EF_code: "EF6", load: "3" })).toEqual({
      factory_code: "H1",
      EF_code: "EF6",
      load: "N/A",
      eqp_id: "",
    });
  });

  it("describes template columns", () => {
    expect(dtypeLabel("float")).toBe("숫자");
    expect(ruleLabel(col({ choices: ["정상", "이상"] }))).toBe("정상 / 이상 · N/A 가능");
    expect(ruleLabel(col({ dtype: "int", min: 0, na_allowed: false, required: true }))).toBe("0 이상 · 필수 · N/A 불가");
  });

  it("formats deltas", () => {
    expect(deltaLabel(49.6, 61.4)).toBe("−11.8");
    expect(deltaLabel(74, 74)).toBe("변화 없음");
    expect(deltaLabel(80, 76.5)).toBe("+3.5");
    expect(deltaLabel(null, 3)).toBe("");
  });

  it("lists the biggest summed deductions only", () => {
    expect(topDeductions(result(), 2)).toEqual([
      { axis: "POF", label: "fan", value: -27 },
      { axis: "POF", label: "경과년수", value: -15 },
    ]);
    expect(topDeductions(result()).map((d) => d.label)).toEqual(["fan", "경과년수", "온라인진단"]);
  });

  it("maps errors by field (first reason wins)", () => {
    const r = result({
      ok: false,
      errors: [
        { column: "load", raw_value: "abc", reason: "숫자가 아님" },
        { column: "load", raw_value: "abc", reason: "두 번째" },
      ],
    });
    expect(errorsByField(r)).toEqual({ load: "숫자가 아님" });
    expect(errorsByField(null)).toEqual({});
  });
});
