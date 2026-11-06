import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import Ef5DetailBody from "./Ef5DetailBody.vue";
import type { Ef5TypeDetail } from "../../types/equipment";

describe("Ef5DetailBody", () => {
  it("keeps POF/COF/DOF groups with equipment info first and one-decimal deductions", () => {
    const typeDetail = {
      ef_code: "EF5",
      spec: { updated_at: "2026-11-06", line_no: "M1L", manufacturer: "FUJI", model_name: "7000HX", capa: 2500 },
      condition: { measured_at: "2026-11-06", fan_replace_no: 0, elec_room_max_temp: null, load: 55, mod_cir_curr: 3, mod_vol_diff: 3, noise: 70, thermal_img_chk: "정상", ex_box_chk: "이상" },
      consequence: {}, design: {},
      score_detail: { cap_stat: null, cap_stat_minus: 0, ex_box_chk_minus: -0.3, capa_times_load_minus: -24.8, age_minus: -16 },
    } as unknown as Ef5TypeDetail;
    const wrapper = mount(Ef5DetailBody, { props: { typeDetail } });
    expect(wrapper.findAll(".raw-title").map((t) => t.text())).toEqual(["POF 구성", "COF 구성", "DOF 구성"]);
    expect(wrapper.find(".raw-subtitle").text()).toBe("설비정보");
    const text = wrapper.text();
    expect(text).toContain("외함점검 감점-0.3");
    expect(text).toContain("사고영향성 감점-24.8");
    expect(text).toContain("경과년수 감점-16.0");
    expect(text).toContain("커패시터고장확률상태점수N/A");
    expect(text).toContain("전기실최대온도N/A");
  });
});
