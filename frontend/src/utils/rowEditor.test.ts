import { describe, expect, it } from "vitest";
import {
  buildEditText,
  cleanCell,
  displayOrder,
  isCellChanged,
  isRowChanged,
  makeNewRow,
  pendingRows,
  rowsFromServer,
} from "./rowEditor";

describe("rowEditor", () => {
  it("tracks changed cells and rows against the loaded values", () => {
    const [a, b] = rowsFromServer([
      ["H1", "TR1", "10"],
      ["H1", "TR2", "20"],
    ]);
    a.cells[2] = "11";
    expect(isCellChanged(a, 2)).toBe(true);
    expect(isCellChanged(a, 1)).toBe(false);
    expect(isRowChanged(a)).toBe(true);
    expect(isRowChanged(b)).toBe(false);
    a.cells[2] = "10";
    expect(isRowChanged(a)).toBe(false);
  });

  it("sends changed rows and non-blank new rows only", () => {
    const rows = rowsFromServer([
      ["H1", "TR1", "10"],
      ["H1", "TR2", "20"],
    ]);
    rows[1].cells[2] = "21";
    const blank = makeNewRow(10, 3);
    const copy = makeNewRow(11, 3, rows[0].cells);
    copy.cells[1] = "TR9";
    expect(copy.original).toBeNull();
    expect(pendingRows([...rows, blank, copy]).map((r) => r.id)).toEqual([2, 11]);
  });

  it("builds tab text with header on line 1 and maps lines back to rows", () => {
    const rows = rowsFromServer([["H1", "TR\t1", "a\nb"]]);
    const extra = makeNewRow(7, 3, ["K1", "TR2", "5"]);
    const { text, lineToId } = buildEditText(["factory_code", "name", "v"], [rows[0], extra]);
    expect(text).toBe("factory_code\tname\tv\nH1\tTR 1\ta b\nK1\tTR2\t5\n");
    expect([...lineToId]).toEqual([
      [2, 1],
      [3, 7],
    ]);
    expect(cleanCell("x\r\ny")).toBe("x  y");
  });

  it("puts key columns first for the sticky area", () => {
    expect(displayOrder(["a", "factory_code", "b", "name"], ["factory_code", "name"])).toEqual([1, 3, 0, 2]);
  });
});
