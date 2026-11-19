import { defineStore } from "pinia";
import { fetchEquipmentDetail, fetchEquipmentList, fetchEquipmentTypes, fetchSummary } from "../api/equipment";
import type { Axis, BreakdownItem, EquipmentDetail, EquipmentSummary, EquipmentTypeInfo, SummaryKPI } from "../types/equipment";

interface State {
  allEquipment: EquipmentSummary[];
  // 등록된 설비유형과 감점 항목 메타데이터(/api/equipment-types) — 화면 라벨의 단일 원본.
  equipmentTypes: EquipmentTypeInfo[];
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
    equipmentTypes: [],
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
    // 사업장 필터 선택지 — 받아 둔 전체 설비에 실제로 있는 사업장만(이름순). 코드에 고정하지 않아서
    // 실제 데이터(H1만)면 H1만, 다른 사업장 설비가 들어오면 자동으로 나타난다. 설비유형 필터와는 무관하다.
    factoryCodes(state): string[] {
      return [...new Set(state.allEquipment.map((item) => item.factory_code))].sort();
    },
    typeNames(state): Record<string, string> {
      return Object.fromEntries(state.equipmentTypes.map((t) => [t.ef_code, t.ef_name]));
    },
    // 지금 목록(필터 적용 후)에 들어 있는 설비유형 — 분포도 마커 구분/KPI 분해 표시에 쓴다.
    visibleTypeCodes(): string[] {
      return [...new Set(this.equipmentList.map((item) => item.ef_code))].sort();
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
        // 모든 설비유형을 받아 두고 유형·사업장 필터는 클라이언트에서 적용한다(Stage 8-5).
        const [list, summary, types] = await Promise.all([fetchEquipmentList(), fetchSummary(), fetchEquipmentTypes()]);
        this.allEquipment = list;
        this.summary = summary;
        this.equipmentTypes = types;
        // 다시 불러온 데이터에 없는 사업장은 선택에서 뺀다 — "전체"처럼 보이는데 걸러지는 상황 방지
        const present = new Set(list.map((item) => item.factory_code));
        if (this.factoryFilters.some((code) => !present.has(code))) {
          this.factoryFilters = this.factoryFilters.filter((code) => present.has(code));
        }
      } catch (err) {
        this.error = err instanceof Error ? err.message : "데이터를 불러오지 못했습니다";
      } finally {
        this.loading = false;
      }
    },
    async loadTypes() {
      if (this.equipmentTypes.length === 0) {
        this.equipmentTypes = await fetchEquipmentTypes();
      }
    },
    breakdownFor(efCode: string): Record<Axis, BreakdownItem[]> {
      const info = this.equipmentTypes.find((t) => t.ef_code === efCode);
      return info?.breakdown ?? { pof: [], cof: [], dof: [] };
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
