import { describe, expect, it } from "vitest";
import { getEvidence, getReasonsByAxis } from "./scoreBreakdown";
import type { Axis, BreakdownItem, EquipmentDetail, ScoreDetail } from "../types/equipment";

// 백엔드 /api/equipment-types의 breakdown 모양(일부만). 라벨은 메타데이터가 단일 원본이다.
const item = (field: string, label: string, group: string | null = null): BreakdownItem => ({ field, label, group, summed: true });
const EF1_BREAKDOWN: Record<Axis, BreakdownItem[]> = {
  pof: [item("age_minus", "경과연수"), { ...item("dga_minus", "DGA(유중가스)"), summed: false }, item("load_minus", "부하율"), item("temp_minus", "운전온도")],
  cof: [item("fire_minus", "화재취약성")],
  dof: [item("redundancy_minus", "예비화"), item("ato_minus", "계통자동전환"), item("online_og_minus", "온라인 유중가스"), item("offline_safety_minus", "안전공사 정밀점검")],
};
const EF2_BREAKDOWN: Record<Axis, BreakdownItem[]> = {
  pof: [item("cb_stat_minus", "차단기 고장확률", "기계적"), item("sf6_minus", "SF6 가스", "화학적")],
  cof: [item("in_vol_minus", "인입전압")],
  dof: [item("ato_minus", "ATO 구성")],
};

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
    const { pof } = getReasonsByAxis(detail, EF1_BREAKDOWN);

    expect(pof.map((r) => r.value)).toEqual([-12, -5]);
    expect(pof[0].label).toBe("DGA(유중가스)");
  });

  it("routes fields to the correct axis (pof/cof/dof never mix)", () => {
    const detail = makeScoreDetail({
      dga_minus: -12, // pof
      fire_minus: -8, // cof
      redundancy_minus: -36, // dof
    });
    const { pof, cof, dof } = getReasonsByAxis(detail, EF1_BREAKDOWN);

    expect(pof.map((r) => r.label)).toEqual(["DGA(유중가스)"]);
    expect(cof.map((r) => r.label)).toEqual(["화재취약성"]);
    expect(dof.map((r) => r.label)).toEqual(["예비화"]);
  });

  it("returns empty arrays for axes with nothing deducted", () => {
    const { pof, cof, dof } = getReasonsByAxis(makeScoreDetail(), EF1_BREAKDOWN);
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
    expect(getReasonsByAxis(detail, EF1_BREAKDOWN).dof).toHaveLength(4);
  });

  it("keeps DGA as a PoF reason even though it is not summed (decision c, 2026-10-17)", () => {
    const { pof } = getReasonsByAxis(makeScoreDetail({ dga_minus: -24 }), EF1_BREAKDOWN);
    expect(pof.map((r) => r.label)).toEqual(["DGA(유중가스)"]);
  });

  it("works for EF2 score details with that type's own metadata", () => {
    const ef2Detail = { cb_stat_minus: -6, sf6_minus: -15, in_vol_minus: -16, ato_minus: 0, age_minus: -20 };
    const { pof, cof, dof } = getReasonsByAxis(ef2Detail, EF2_BREAKDOWN);
    expect(pof.map((r) => [r.label, r.value])).toEqual([["SF6 가스", -15], ["차단기 고장확률", -6]]);
    expect(cof.map((r) => r.value)).toEqual([-16]);
    expect(dof).toEqual([]); // age_minus처럼 메타데이터에 없는 필드는 사유로 안 나온다
  });
});

describe("getEvidence", () => {
  it("describes EF2 SF6 deductions from the GIS detail", () => {
    const detail = {
      type_detail: {
        ef_code: "EF2",
        sf6: { diag_time: "2024-11-01", sf6_so2: 0, sf6_leak: "없음", sf6_h2o: 320, sf6_purity: 96 },
      },
    } as unknown as EquipmentDetail;
    expect(getEvidence("sf6_minus", detail)).toBe("SO2 0 · 누기 없음 · 수분 320 · 순도 96%");
    expect(getEvidence("unknown_minus", detail)).toBe("");
  });

  it("describes EF3 cable deductions from the cable detail", () => {
    const detail = {
      type_detail: {
        ef_code: "EF3",
        spec: { cable_mva: 414, cable_length: 7408, end_joint: "DEBG, EBA" },
        condition: { max_load: 380 },
        score_detail: { load_percent: 91.78743961352657, rep_cost: 100.008 },
      },
    } as unknown as EquipmentDetail;
    expect(getEvidence("load_minus", detail)).toBe("부하율 91.8% (최대부하 380 / 용량 414)");
    expect(getEvidence("end_joint_minus", detail)).toBe("종단접속함 DEBG, EBA");
    expect(getEvidence("rep_cost_minus", detail)).toBe("사고복구교체비용 100.0 (길이 7,408)");
  });
});
