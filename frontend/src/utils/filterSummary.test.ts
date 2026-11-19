import { describe, expect, it } from "vitest";
import { summarizeRow } from "./filterSummary";

describe("summarizeRow", () => {
  it("비었으면 전체", () => {
    expect(summarizeRow([], 3)).toEqual({ all: true, shown: [], rest: 0 });
  });
  it("max까지만 보여 주고 나머지는 개수로", () => {
    expect(summarizeRow(["a", "b", "c", "d", "e", "f"], 3)).toEqual({ all: false, shown: ["a", "b", "c"], rest: 3 });
    expect(summarizeRow(["a", "b"], 3)).toEqual({ all: false, shown: ["a", "b"], rest: 0 });
  });
});
