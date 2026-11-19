import { describe, expect, it } from "vitest";
import { formatStamp, refreshCaption, refreshTooltip, scoreDateText } from "./scoreRefresh";

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

  it("갱신 캡션은 자동·수동을 구분하고 월-일 시:분", () => {
    expect(refreshCaption("2026-11-19T00:05:30", "daily")).toBe("자동 갱신 11-19 00:05");
    expect(refreshCaption("2026-11-19T00:05:30", "startup")).toBe("자동 갱신 11-19 00:05");
    expect(refreshCaption("2026-11-19T14:20:00", "admin")).toBe("수동 갱신 11-19 14:20");
    expect(refreshCaption(null, "daily")).toBeNull();
    expect(refreshTooltip(false)).toContain("꺼져");
  });
});
