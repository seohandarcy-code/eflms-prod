import { describe, expect, it } from "vitest";
import { getReasonsByAxis } from "./scoreBreakdown";
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

describe("getReasonsByAxis", () => {
  it("sorts each axis's reasons by largest deduction first and excludes zero-value fields", () => {
    const detail = makeScoreDetail({ dga_minus: -12, load_minus: -5, temp_minus: 0 });
    const { pof } = getReasonsByAxis(detail);

    expect(pof.map((r) => r.value)).toEqual([-12, -5]);
    expect(pof[0].label).toBe("DGA(유중가스)");
  });

  it("routes fields to the correct axis (pof/cof/dof never mix)", () => {
    const detail = makeScoreDetail({
      dga_minus: -12, // pof
      fire_minus: -8, // cof
      redundancy_minus: -36, // dof
    });
    const { pof, cof, dof } = getReasonsByAxis(detail);

    expect(pof.map((r) => r.label)).toEqual(["DGA(유중가스)"]);
    expect(cof.map((r) => r.label)).toEqual(["화재취약성"]);
    expect(dof.map((r) => r.label)).toEqual(["예비화"]);
  });

  it("returns empty arrays for axes with nothing deducted", () => {
    const { pof, cof, dof } = getReasonsByAxis(makeScoreDetail());
    expect(pof).toEqual([]);
    expect(cof).toEqual([]);
    expect(dof).toEqual([]);
  });

  it("includes every nonzero reason for an axis, not just the top few", () => {
    const detail = makeScoreDetail({
      redundancy_minus: -36,
      ato_minus: -36,
      online_og_minus: -30,
      offline_safety_minus: -25,
    });
    expect(getReasonsByAxis(detail).dof).toHaveLength(4);
  });
});
