import { defineStore } from "pinia";
import { fetchEquipmentDetail, fetchEquipmentList, fetchSummary } from "../api/equipment";
import type { EquipmentDetail, EquipmentSummary, SummaryKPI } from "../types/equipment";

interface State {
  equipmentList: EquipmentSummary[];
  summary: SummaryKPI | null;
  detailCache: Record<number, EquipmentDetail>;
  loading: boolean;
  error: string | null;
  factoryFilter: string | null;
}

export const useEquipmentStore = defineStore("equipment", {
  state: (): State => ({
    equipmentList: [],
    summary: null,
    detailCache: {},
    loading: false,
    error: null,
    factoryFilter: null,
  }),
  getters: {
    needsInspectionList(state): EquipmentSummary[] {
      return state.equipmentList.filter((item) => item.needs_inspection).sort((a, b) => a.total_score - b.total_score);
    },
  },
  actions: {
    async load() {
      this.loading = true;
      this.error = null;
      try {
        const [list, summary] = await Promise.all([
          fetchEquipmentList(this.factoryFilter ?? undefined),
          fetchSummary(),
        ]);
        this.equipmentList = list.sort((a, b) => a.total_score - b.total_score);
        this.summary = summary;
      } catch (err) {
        this.error = err instanceof Error ? err.message : "데이터를 불러오지 못했습니다";
      } finally {
        this.loading = false;
      }
    },
    async setFactoryFilter(factoryCode: string | null) {
      this.factoryFilter = factoryCode;
      await this.load();
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
