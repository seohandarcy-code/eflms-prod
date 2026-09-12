import { describe, expect, it } from "vitest";
import { getTopReasons, projectScorePoint } from "./scoreBreakdown";
import type { ScoreDetail } from "../types/equipment";

function makeScoreDetail(overrides: Partial<ScoreDetail> = {}): ScoreDetail {
  return {
    today: "2026-09-12",
    operation_year: 5,
    age_minus: 0,
    dga_tcg: 0,
    dga_diag: "정상",
    dga_minus: 0,
    load_minus: 0,
    temp_minus: 0,
    dielec_str_te_avg: 45,
    dielec_str_te_diag: "적합",
    dielec_str_te_minus: 0,
    acid_measure_desc: "적합",
    acid_measure_minus: 0,
    moisture_desc: "정상",
    moisture_minus: 0,
    furan_total: 0,
    furan_total_per_year: 0,
    furan_desc: "정상",
    furan_minus: 0,
    part_discharge_minus: 0,
    oltc_96t_minus: 0,
    oltc_diag: "정상",
    oltc_minus: 0,
    thermal_img_minus: 0,
    noise_minus: 0,
    first_voltage: 22900,
    first_voltage_minus: 0,
    capa_times_load: 10,
    productivity_minus: 0,
    fire_minus: 0,
    fire_spread_minus: 0,
    emerge_response_minus: 0,
    rep_cost: 1,
    rep_cost_minus: 0,
    rep_time: 3,
    rep_time_minus: 0,
    redundancy_minus: 0,
    ato_minus: 0,
    online_og_minus: 0,
    offline_safety_minus: 0,
    sec_minus: 0,
    alarm_minus: 0,
    winding_minus: 0,
    prod_life_minus: 0,
    connect_part_minus: 0,
    temp_inc_limit_minus: 0,
    test_reliability_minus: 0,
    bushing_minus: 0,
    oltc2_minus: 0,
    ...overrides,
  };
}

describe("getTopReasons", () => {
  it("returns the largest deductions first and excludes zero-value fields", () => {
    const detail = makeScoreDetail({ redundancy_minus: -36, fire_minus: -8, dga_minus: -12 });
    const reasons = getTopReasons(detail, 3);

    expect(reasons.map((r) => r.value)).toEqual([-36, -12, -8]);
    expect(reasons[0].label).toBe("예비화");
    expect(reasons.every((r) => r.value < 0)).toBe(true);
  });

  it("returns an empty list when nothing was deducted", () => {
    expect(getTopReasons(makeScoreDetail(), 3)).toEqual([]);
  });

  it("respects the limit parameter", () => {
    const detail = makeScoreDetail({
      redundancy_minus: -36,
      ato_minus: -36,
      online_og_minus: -30,
      fire_minus: -8,
    });
    expect(getTopReasons(detail, 2)).toHaveLength(2);
  });
});

describe("projectScorePoint", () => {
  it("places (0, 0, 0) at the isometric origin", () => {
    expect(projectScorePoint(0, 0, 0)).toEqual({ x: 280, y: 190 });
  });

  it("moves up (smaller y) as dof increases", () => {
    const low = projectScorePoint(50, 50, 0);
    const high = projectScorePoint(50, 50, 100);
    expect(high.y).toBeLessThan(low.y);
  });

  it("clamps out-of-range values instead of projecting off-scale", () => {
    const clamped = projectScorePoint(-40, 150, 20);
    const atBounds = projectScorePoint(0, 100, 20);
    expect(clamped).toEqual(atBounds);
  });
});
