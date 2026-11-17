import { describe, expect, it } from "vitest";
import type { EquipmentSummary } from "../types/equipment";
import { countByType, FACILITY_INFO, facilityAnchor, pofHighlights, sortByFlow } from "./facilityInfo";

const item = (ef_code: string, status: EquipmentSummary["status"]): EquipmentSummary => ({
  equipment_id: 1,
  factory_code: "H1",
  ef_code,
  equipment_name: "x",
  voltage: 0,
  operation_start_time: "2015-03-01",
  pof: 0,
  cof: 0,
  dof: 0,
  total_score: 0,
  status,
  last_diag_date: "2026-01-01",
});

describe("facilityInfo", () => {
  it("has a description and both pictures for every registered type EF1~EF7", () => {
    for (const code of ["EF1", "EF2", "EF3", "EF4", "EF5", "EF6", "EF7"]) {
      const info = FACILITY_INFO[code];
      expect(info, code).toBeDefined();
      expect(info.summary.length).toBeGreaterThan(0);
      expect(info.image).toMatch(/ef\d\.png/);
      expect(info.animated).toMatch(/ef\d\.gif/);
      expect(info.animatedWebp).toMatch(/ef\d\.webp/);
      expect(info.image).toContain(code.toLowerCase());
    }
  });

  it("sorts codes in power-flow order and puts unknown types last", () => {
    expect(sortByFlow(["EF1", "EF9", "EF7", "EF3", "EF8", "EF4"])).toEqual(["EF3", "EF1", "EF4", "EF7", "EF8", "EF9"]);
  });

  it("counts units and 점검필요(교체검토+즉시교체) per type", () => {
    const counts = countByType([item("EF1", "normal"), item("EF1", "review"), item("EF1", "replace"), item("EF7", "normal")]);
    expect(counts.EF1).toEqual({ total: 3, needsInspection: 2 });
    expect(counts.EF7).toEqual({ total: 1, needsInspection: 0 });
    expect(counts.EF2).toBeUndefined();
  });

  it("keeps the first POF labels and reports how many are left", () => {
    const items = ["a", "b", "c", "d", "e", "f", "g"].map((label) => ({ field: label, label, group: null, summed: true }));
    expect(pofHighlights(items)).toEqual({ labels: ["a", "b", "c", "d", "e"], rest: 2 });
    expect(pofHighlights(items.slice(0, 2))).toEqual({ labels: ["a", "b"], rest: 0 });
  });

  it("uses the lowercase code as the guide anchor", () => {
    expect(facilityAnchor("EF7")).toBe("ef7");
  });
});
