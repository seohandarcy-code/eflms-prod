import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import EquipmentCard from "./EquipmentCard.vue";
import type { EquipmentSummary } from "../types/equipment";

const summary: EquipmentSummary = {
  equipment_id: 1,
  factory_code: "H1",
  ef_code: "EF1",
  equipment_name: "TR1",
  voltage: 22900,
  operation_start_time: "2015-03-01",
  pof: 90,
  cof: 90,
  dof: 90,
  total_score: 90,
  status: "normal",
  last_diag_date: "2026-01-01",
};

describe("EquipmentCard", () => {
  it("renders the transformer name and status", () => {
    const wrapper = mount(EquipmentCard, { props: { summary } });
    expect(wrapper.text()).toContain("TR1");
    expect(wrapper.text()).toContain("정상");
  });

  it("shows a 교체검토 chip when the equipment is in review status", () => {
    const wrapper = mount(EquipmentCard, {
      props: { summary: { ...summary, status: "review" } },
    });
    expect(wrapper.text()).toContain("교체검토");
  });

  it("shows a 즉시교체 chip when the equipment must be replaced immediately", () => {
    const wrapper = mount(EquipmentCard, {
      props: { summary: { ...summary, status: "replace" } },
    });
    expect(wrapper.text()).toContain("즉시교체");
  });

  it("shows the equipment type badge when a type name is given", () => {
    const wrapper = mount(EquipmentCard, { props: { summary: { ...summary, ef_code: "EF2" }, typeName: "GIS" } });
    expect(wrapper.find(".type-badge").text()).toBe("GIS");
  });

  it("shows the operation month instead of voltage (Stage 10-0)", () => {
    const wrapper = mount(EquipmentCard, { props: { summary } });
    expect(wrapper.find(".meta").text()).toContain("H1 · 가동 2015-03");
    expect(wrapper.text()).not.toContain("22,900V");
  });

  it("emits select with the equipment id when clicked", async () => {
    const wrapper = mount(EquipmentCard, { props: { summary } });
    await wrapper.trigger("click");
    expect(wrapper.emitted("select")?.[0]).toEqual([1]);
  });
});
