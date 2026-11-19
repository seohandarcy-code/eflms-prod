import { describe, expect, it } from "vitest";
import { fieldDiffs, rowKeyLabel } from "./changeHistory";

describe("changeHistory", () => {
  it("갱신은 바뀐 칸만, 내부 칸은 빼고", () => {
    const diffs = fieldDiffs({
      row_key: "H1|eqp14",
      action: "update",
      before: { load_chk: 0.5, noise_chk: "양호", _as_of: "2026-10-01", _extras: {} },
      after: { load_chk: 0.9, noise_chk: "양호", _extras: {} },
    });
    expect(diffs).toEqual([{ name: "load_chk", before: "0.5", after: "0.9" }]);
  });

  it("추가·삭제는 모든 칸, null은 N/A", () => {
    expect(fieldDiffs({ row_key: "k", action: "insert", before: null, after: { a: 1, b: null } })).toEqual([
      { name: "a", before: "", after: "1" },
      { name: "b", before: "", after: "N/A" },
    ]);
    expect(fieldDiffs({ row_key: "k", action: "delete", before: { a: 1 }, after: null })).toEqual([{ name: "a", before: "1", after: "" }]);
    expect(rowKeyLabel("discharge_history|H1|2026-11-01")).toBe("discharge_history · H1 · 2026-11-01");
  });
});
