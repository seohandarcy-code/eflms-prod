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
import { START_EQUIPMENT_TYPE_FILTERS, START_FACTORY_FILTERS, useEquipmentStore } from "./equipment";

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

  it("시작 화면은 H1 · 수배전반(EF4)", async () => {
    const store = useEquipmentStore();
    expect(START_FACTORY_FILTERS).toEqual(["H1"]);
    expect(START_EQUIPMENT_TYPE_FILTERS).toEqual(["EF4"]);
    vi.mocked(fetchEquipmentList).mockResolvedValue([item(1, "H1", "EF4"), item(2, "K1", "EF4"), item(3, "H1")]);
    await store.load();
    expect(store.factoryFilters).toEqual(["H1"]);
    expect(store.equipmentTypeFilters).toEqual(["EF4"]);
    expect(store.equipmentList.map((i) => i.equipment_id)).toEqual([1]);
  });

  it("시작 사업장 H1이 데이터에 없으면 전체가 아니라 데이터가 있는 사업장을 모두 체크", async () => {
    const store = useEquipmentStore();
    vi.mocked(fetchEquipmentList).mockResolvedValue([item(1, "P1", "EF4"), item(2, "K1", "EF4")]);
    await store.load();
    expect(store.factoryFilters).toEqual(["K1", "P1"]);
  });

  it("시작한 뒤 다시 불러올 때는 시작 규칙을 다시 적용하지 않는다(사용자가 비운 선택 = 전체 유지)", async () => {
    const store = useEquipmentStore();
    vi.mocked(fetchEquipmentList).mockResolvedValue([item(1, "H1", "EF4")]);
    await store.load();
    store.setFactoryFilters([]);
    await store.load();
    expect(store.factoryFilters).toEqual([]);
    store.setFactoryFilters(["H1"]);
    vi.mocked(fetchEquipmentList).mockResolvedValue([item(2, "K1", "EF4")]);
    await store.load();
    expect(store.factoryFilters).toEqual([]);
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
