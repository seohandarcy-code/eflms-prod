import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import EquipmentListTable from "./EquipmentListTable.vue";
import type { EquipmentSummary } from "../types/equipment";

const items: EquipmentSummary[] = [
  {
    equipment_id: 1,
    factory_code: "H1",
    ef_code: "EF1",
    transformer_name: "TR1",
    voltage: 22900,
    pof: 90,
    cof: 90,
    dof: 90,
    total_score: 90,
    status: "normal",
    last_diag_date: "2026-01-01",
  },
  {
    equipment_id: 2,
    factory_code: "K1",
    ef_code: "EF1",
    transformer_name: "BANK3",
    voltage: 154000,
    pof: 22,
    cof: 36,
    dof: 14,
    total_score: 24.6,
    status: "replace",
    last_diag_date: "2026-01-01",
  },
];

describe("EquipmentListTable", () => {
  it("renders a row per item with its status label", () => {
    const wrapper = mount(EquipmentListTable, { props: { items, activeId: null } });
    expect(wrapper.text()).toContain("TR1");
    expect(wrapper.text()).toContain("BANK3");
    expect(wrapper.text()).toContain("정상");
    expect(wrapper.text()).toContain("즉시교체");
  });

  it("emits select with the equipment id when a row is clicked", async () => {
    const wrapper = mount(EquipmentListTable, { props: { items, activeId: null } });
    await wrapper.findAll("tbody tr")[1].trigger("click");
    expect(wrapper.emitted("select")?.[0]).toEqual([2]);
  });
});
