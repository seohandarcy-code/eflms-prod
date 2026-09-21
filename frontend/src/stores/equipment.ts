import { defineStore } from "pinia";
import { fetchEquipmentDetail, fetchEquipmentList, fetchSummary } from "../api/equipment";
import type { EquipmentDetail, EquipmentSummary, SummaryKPI } from "../types/equipment";

interface State {
  allEquipment: EquipmentSummary[];
  summary: SummaryKPI | null;
  detailCache: Record<number, EquipmentDetail>;
  loading: boolean;
  error: string | null;
  // 다중 선택. 빈 배열 = 전체(필터 없음).
  factoryFilters: string[];
  equipmentTypeFilters: string[];
}

export const useEquipmentStore = defineStore("equipment", {
  state: (): State => ({
    allEquipment: [],
    summary: null,
    detailCache: {},
    loading: false,
    error: null,
    factoryFilters: [],
    equipmentTypeFilters: [],
  }),
  getters: {
    // 사업장·설비유형 다중 선택 필터가 적용된 현재 목록. 서버는 항상 전체를 반환하고,
    // 필터링은 클라이언트에서 처리한다(설비 수가 적어 서버 왕복 없이 즉시 반응 가능).
    equipmentList(state): EquipmentSummary[] {
      let filtered = state.allEquipment;
      if (state.factoryFilters.length > 0) {
        filtered = filtered.filter((item) => state.factoryFilters.includes(item.factory_code));
      }
      if (state.equipmentTypeFilters.length > 0) {
        filtered = filtered.filter((item) => state.equipmentTypeFilters.includes(item.ef_code));
      }
      return [...filtered].sort((a, b) => a.total_score - b.total_score);
    },
    needsInspectionList(): EquipmentSummary[] {
      return this.equipmentList
        .filter((item) => item.status === "review" || item.status === "replace")
        .sort((a, b) => a.total_score - b.total_score);
    },
  },
  actions: {
    async load() {
      this.loading = true;
      this.error = null;
      try {
        const [list, summary] = await Promise.all([fetchEquipmentList(), fetchSummary()]);
        this.allEquipment = list;
        this.summary = summary;
      } catch (err) {
        this.error = err instanceof Error ? err.message : "데이터를 불러오지 못했습니다";
      } finally {
        this.loading = false;
      }
    },
    setFactoryFilters(factoryCodes: string[]) {
      this.factoryFilters = factoryCodes;
    },
    setEquipmentTypeFilters(efCodes: string[]) {
      this.equipmentTypeFilters = efCodes;
    },
    async loadDetail(equipmentId: number): Promise<EquipmentDetail> {
      if (this.detailCache[equipmentId]) {
        return this.detailCache[equipmentId];
      }
      const detail = await fetchEquipmentDetail(equipmentId);
      this.detailCache[equipmentId] = detail;
      return detail;
    },
  },
});
