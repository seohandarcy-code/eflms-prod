import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import Ef7DetailBody from "./Ef7DetailBody.vue";
import type { Ef7TypeDetail } from "../../types/equipment";

describe("Ef7DetailBody", () => {
  it("keeps POF/COF/DOF groups, shows reference-based SOH values and one-decimal deductions", () => {
    const typeDetail = {
      ef_code: "EF7",
      spec: { updated_at: "2026-11-16", line_no: "11L", manufacturer: "삼성SDI", model_name: "AVC2", capa: 500 },
      condition: { measured_at: "2026-11-16", vol_diff: 0.023, temp_diff: 5.3, temp_range_over: 0, bat_room_temp: null, bat_room_humid: 52.5, load: 55 },
      consequence: { con_rank: "공용" },
      design: { model_gen: 2 },
      score_detail: {
        operation_year: 10.9, age_minus: -10, disch_index: 103.085, disch_dec_coef: 0.059686215, temp_dec_coef: null,
        soh_minus: 0, bms_stat: null, temp_diff_minus: -0.7, capa_times_load_minus: -3.3, con_rank_minus: -3, model_gen_minus: -12,
      },
    } as unknown as Ef7TypeDetail;
    const wrapper = mount(Ef7DetailBody, { props: { typeDetail } });
    expect(wrapper.findAll(".raw-title").map((t) => t.text())).toEqual(["POF 구성", "COF 구성", "DOF 구성"]);
    expect(wrapper.findAll(".raw-subtitle").map((t) => t.text())).toEqual(["설비정보", "SOH·BMS", "셀·배터리실"]);
    const text = wrapper.text();
    expect(text).toContain("방전인덱스합계103.085");
    expect(text).toContain("방전감소계수0.0597");
    expect(text).toContain("온도감소계수N/A");
    expect(text).toContain("배터리실온도N/A");
    expect(text).toContain("셀간온도편차 감점-0.7");
    expect(text).toContain("경과년수 감점-10.0");
    expect(text).toContain("사고영향성 감점-3.3");
    expect(text).toContain("모델세대 감점-12.0");
  });
});
