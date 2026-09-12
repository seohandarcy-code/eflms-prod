import { beforeEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import EquipmentCard from "./EquipmentCard.vue";
import type { EquipmentSummary } from "../types/equipment";

const summary: EquipmentSummary = {
  equipment_id: 1,
  factory_code: "H1",
  ef_code: "EF1",
  transformer_name: "TR1",
  voltage: 22900,
  pof: 90,
  cof: 90,
  dof: 90,
  total_score: 90,
  needs_inspection: false,
  last_diag_date: "2026-01-01",
};

beforeEach(() => {
  setActivePinia(createPinia());
});

describe("EquipmentCard", () => {
  it("renders the transformer name and status when collapsed", () => {
    const wrapper = mount(EquipmentCard, { props: { summary, expanded: false } });
    expect(wrapper.text()).toContain("TR1");
    expect(wrapper.text()).toContain("정상");
  });

  it("shows a 점검필요 chip when the equipment needs inspection", () => {
    const wrapper = mount(EquipmentCard, {
      props: { summary: { ...summary, needs_inspection: true }, expanded: false },
    });
    expect(wrapper.text()).toContain("점검필요");
  });

  it("emits toggle with the equipment id when clicked", async () => {
    const wrapper = mount(EquipmentCard, { props: { summary, expanded: false } });
    await wrapper.trigger("click");
    expect(wrapper.emitted("toggle")?.[0]).toEqual([1]);
  });
});
