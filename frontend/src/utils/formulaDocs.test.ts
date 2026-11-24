import { describe, expect, it } from "vitest";
import type { FormulaMapItem, FormulaStepsItem } from "../types/equipment";
import { axisTex, formatMinus, mapRows, stepRows } from "./formulaDocs";

const base = { group: null, summed: true, inputs: [], note: null };

describe("formulaDocs", () => {
  it("formats deductions with a real minus sign", () => {
    expect(formatMinus(-36)).toBe("−36");
    expect(formatMinus(-1.7)).toBe("−1.7");
    expect(formatMinus(0)).toBe("0");
  });

  it("turns bands into readable ranges from the top", () => {
    const item: FormulaStepsItem = {
      ...base, field: "load_minus", label: "부하율", kind: "steps", var: "load_percent", var_label: "부하율",
      unit: "%", bands: [{ value: 100, op: "gt", minus: -36 }, { value: 90, op: "gt", minus: -24 }, { value: 80, op: "gt", minus: -12 }],
      otherwise: 0, tex: null,
    };
    expect(stepRows(item)).toEqual([
      { cond: "100% 초과", minus: -36 },
      { cond: "90% 초과 ~ 100% 이하", minus: -24 },
      { cond: "80% 초과 ~ 90% 이하", minus: -12 },
      { cond: "80% 이하", minus: 0 },
    ]);
  });

  it("words 'at least' bands and mixed comparisons", () => {
    const item: FormulaStepsItem = {
      ...base, field: "moisture_minus", label: "수분시험", kind: "steps", var: "moisture_rslt", var_label: "수분시험결과",
      unit: "", bands: [{ value: 50, op: "gt", minus: -8 }, { value: 40, op: "ge", minus: -4 }], otherwise: 0, tex: null,
    };
    expect(stepRows(item).map((r) => r.cond)).toEqual(["50 초과", "40 이상 ~ 50 이하", "40 미만"]);
    const sec: FormulaStepsItem = {
      ...item, bands: [{ value: 4, op: "ge", minus: 0 }, { value: 3, op: "ge", minus: -2 }], otherwise: -4,
    };
    expect(stepRows(sec)).toEqual([
      { cond: "4 이상", minus: 0 },
      { cond: "3 이상 ~ 4 미만", minus: -2 },
      { cond: "3 미만", minus: -4 },
    ]);
  });

  it("lists grades and the fallback row", () => {
    const item: FormulaMapItem = {
      ...base, field: "pd_minus", label: "부분방전", kind: "map",
      table: [{ value: "이상", minus: -8 }, { value: "요주의", minus: -4 }], default: 0, default_label: "양호",
    };
    expect(mapRows(item)).toEqual([
      { value: "이상", minus: -8 },
      { value: "요주의", minus: -4 },
      { value: "그 밖(양호)", minus: 0 },
    ]);
    expect(mapRows({ ...item, default_label: null }).length).toBe(2);
  });

  it("builds the axis equation", () => {
    expect(axisTex("pof")).toBe("\\text{POF} = 100 + \\sum \\text{감점}");
  });
});
