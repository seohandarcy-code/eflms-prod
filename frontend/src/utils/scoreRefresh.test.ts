import { describe, expect, it } from "vitest";
import { formatStamp, scoreDateText } from "./scoreRefresh";

describe("scoreRefresh", () => {
  it("점수 기준일은 같으면 한 날짜, 다르면 범위", () => {
    expect(scoreDateText("2026-11-19", "2026-11-19")).toBe("2026-11-19");
    expect(scoreDateText("2026-11-16", "2026-11-19")).toBe("2026-11-16 ~ 2026-11-19");
    expect(scoreDateText(null, null)).toBe("-");
  });

  it("시각은 분까지", () => {
    expect(formatStamp("2026-11-19T01:30:12.5")).toBe("2026-11-19 01:30");
    expect(formatStamp(null)).toBe("-");
  });
});
