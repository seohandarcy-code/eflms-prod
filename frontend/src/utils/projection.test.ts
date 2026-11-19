import { describe, expect, it } from "vitest";
import type { ProjectionPoint } from "../types/equipment";
import { projectionView, risingReason, signed } from "./projection";

const point = (years: number, pof: number, changes: ProjectionPoint["pof_changes"] = []): ProjectionPoint => ({
  years_ahead: years,
  as_of: `202${6 + years}-11-19`,
  pof,
  cof: 80,
  dof: 80,
  total_score: 80,
  status: pof > 60 ? "normal" : "review",
  pof_changes: changes,
});

describe("projectionView", () => {
  it("라벨·상승 여부·변화 큰 순 정렬", () => {
    const views = projectionView([
      point(0, 41.5),
      point(1, 40.5, [{ field: "age_minus", label: "경과연수", value: -3.5, delta: -1 }]),
      point(2, 63.5, [
        { field: "age_minus", label: "경과연수", value: -4.5, delta: -1 },
        { field: "furan_minus", label: "Furan", value: 0, delta: 24 },
      ]),
    ]);
    expect(views.map((v) => v.label)).toEqual(["현재", "1년 후", "2년 후"]);
    expect(views.map((v) => v.rising)).toEqual([false, false, true]);
    expect(views[2].changes[0].field).toBe("furan_minus");
    expect(risingReason(views[2])).toBe("Furan 감점이 줄어 POF 상승");
    expect(risingReason(views[1])).toBeNull();
  });

  it("부호 붙은 소수 첫째 자리", () => {
    expect(signed(24)).toBe("+24.0");
    expect(signed(-1)).toBe("-1.0");
  });
});
