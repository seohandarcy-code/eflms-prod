import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import type { EquipmentSummary } from "../types/equipment";

vi.mock("../api/equipment", () => ({
  fetchEquipmentList: vi.fn(),
  fetchSummary: vi.fn().mockResolvedValue(null),
  fetchEquipmentTypes: vi.fn().mockResolvedValue([]),
  fetchEquipmentDetail: vi.fn(),
}));

import { fetchEquipmentList } from "../api/equipment";
import { useEquipmentStore } from "./equipment";

const item = (id: number, factory: string, ef = "EF1") => ({ equipment_id: id, factory_code: factory, ef_code: ef, total_score: 50 }) as EquipmentSummary;

describe("equipment store — 사업장 필터 선택지", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetchEquipmentList).mockReset();
  });

  it("받아 둔 설비에 있는 사업장만 중복 없이 이름순으로", () => {
    const store = useEquipmentStore();
    store.allEquipment = [item(1, "K1"), item(2, "H1"), item(3, "H1", "EF7"), item(4, "H2")];
    expect(store.factoryCodes).toEqual(["H1", "H2", "K1"]);
  });

  it("H1만 있으면 선택지도 H1 하나, 설비유형 필터와는 무관", () => {
    const store = useEquipmentStore();
    store.allEquipment = [item(1, "H1"), item(2, "H1", "EF7")];
    store.setEquipmentTypeFilters(["EF7"]);
    expect(store.factoryCodes).toEqual(["H1"]);
  });

  it("다시 불러온 데이터에 없는 사업장은 선택에서 빠진다", async () => {
    const store = useEquipmentStore();
    store.setFactoryFilters(["H1", "P1"]);
    vi.mocked(fetchEquipmentList).mockResolvedValue([item(1, "H1"), item(2, "H2")]);
    await store.load();
    expect(store.factoryFilters).toEqual(["H1"]);
    expect(store.factoryCodes).toEqual(["H1", "H2"]);
  });
});
