import { describe, expect, it } from "vitest";
import { defaultTableQuery, formatCell, pushHistory, sqlToRun, toCsv } from "./sqlResult";

describe("sqlResult (Stage 16-5)", () => {
  it("테이블 기본 조회문", () => {
    expect(defaultTableQuery("equipment")).toBe("SELECT *\nFROM equipment\nLIMIT 100;");
  });

  it("선택한 부분이 있으면 그것만, 없으면 전체를 실행", () => {
    const text = "SELECT 1;\nSELECT 2;";
    expect(sqlToRun(text, 0, 0)).toBe(text);
    expect(sqlToRun(text, 10, 19)).toBe("SELECT 2;");
    expect(sqlToRun(text, 3, 3)).toBe(text);
    expect(sqlToRun("  \n", 0, 2)).toBe("");
  });

  it("NULL 표시와 CSV(따옴표·쉼표·줄바꿈 처리, BOM)", () => {
    expect(formatCell(null)).toBe("NULL");
    expect(formatCell(0)).toBe("0");
    const csv = toCsv(["a", "b"], [["x,y", 'say "hi"'], [null, "줄\n바꿈"]]);
    expect(csv.startsWith("﻿")).toBe(true);
    expect(csv).toContain('"x,y","say ""hi"""');
    expect(csv).toContain(',"줄\n바꿈"');
  });

  it("최근 실행 목록: 맨 앞, 중복 제거, 최대 개수", () => {
    let h: string[] = [];
    for (let i = 0; i < 12; i++) h = pushHistory(h, `SELECT ${i}`);
    expect(h).toHaveLength(10);
    expect(h[0]).toBe("SELECT 11");
    h = pushHistory(h, " SELECT 5 ");
    expect(h[0]).toBe("SELECT 5");
    expect(h.filter((x) => x === "SELECT 5")).toHaveLength(1);
    expect(pushHistory(h, "   ")).toBe(h);
  });
});
