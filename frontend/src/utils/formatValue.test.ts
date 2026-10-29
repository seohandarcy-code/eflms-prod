import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { na } from "./formatValue";
import Ef4DetailBody from "../components/detail/Ef4DetailBody.vue";
import type { Ef4TypeDetail } from "../types/equipment";

describe("na", () => {
  it("shows N/A for null without applying number formats or units", () => {
    expect(na(null)).toBe("N/A");
    expect(na(undefined, { digits: 1, unit: "℃" })).toBe("N/A");
  });

  it("formats present values", () => {
    expect(na(25, { unit: "℃" })).toBe("25℃");
    expect(na(0.624, { scale: 100, digits: 0, unit: "%" })).toBe("62%");
    expect(na(7408, { locale: true })).toBe("7,408");
    expect(na(0, { unit: "%" })).toBe("0%");
    expect(na("양호")).toBe("양호");
  });
});

describe("detail body with N/A (null) values", () => {
  it("renders N/A instead of crashing on null inputs", () => {
    const typeDetail = {
      ef_code: "EF4",
      spec: { eqp_id_name: "hvcb1", eqp_building: null, eqp_disting: "10U", eqp_floor: "1F", install_building: null },
      condition: { measured_at: "2026-10-29", part_thermal_chk: "양호", elec_room_avg_temp: 25, temp_diff_chk: 0, max_temp_chk: null, load_chk: null, ex_box_chk: "양호", noise_chk: "양호", bolt_chk: "양호" },
      consequence: {}, design: { reliability: "O", ato: "적용" }, score_detail: { cb_stat: 1 },
    } as unknown as Ef4TypeDetail;
    const raw = mount(Ef4DetailBody, { props: { typeDetail } }).text();
    expect(raw).toContain("설치건물N/A");
  });
});
