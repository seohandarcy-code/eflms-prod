<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useEquipmentStore } from "../stores/equipment";
import RiskScatterChart from "../components/RiskScatterChart.vue";
import EquipmentCard from "../components/EquipmentCard.vue";
import EquipmentDetailPanel from "../components/EquipmentDetailPanel.vue";
import { getReasonsByAxis } from "../utils/scoreBreakdown";
import type { ReasonsByAxis } from "../utils/scoreBreakdown";

const store = useEquipmentStore();
const selectedId = ref<number | null>(null);
const hoveredId = ref<number | null>(null);
const reasonScrollEl = ref<HTMLDivElement | null>(null);
const factories = ["H1", "H2", "K1", "P1"];

const EMPTY_REASONS: ReasonsByAxis = { pof: [], cof: [], dof: [] };

const detailReasons = computed(() =>
  store.needsInspectionList.map((item) => ({
    item,
    reasons: store.detailCache[item.equipment_id] ? getReasonsByAxis(store.detailCache[item.equipment_id].score_detail) : EMPTY_REASONS,
  })),
);

onMounted(async () => {
  await store.load();
  // 점검필요 순위 리스트의 감점 사유를 보여주기 위해 상세를 미리 불러온다.
  await Promise.all(store.needsInspectionList.map((item) => store.loadDetail(item.equipment_id)));
  // 기본값: 종합점수가 가장 낮은(가장 시급한) 설비를 자동 선택
  if (selectedId.value === null && store.equipmentList.length > 0) {
    selectedId.value = store.equipmentList[0].equipment_id;
  }
});

function selectCard(equipmentId: number) {
  selectedId.value = equipmentId;
}

function onChartHover(equipmentId: number | null) {
  hoveredId.value = equipmentId;
  if (equipmentId === null || !reasonScrollEl.value) return;
  reasonScrollEl.value.querySelector(`[data-equipment-id="${equipmentId}"]`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function formatDateTime(value: string | null): string {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 16);
}
</script>

<template>
  <div class="dashboard">
    <header class="topbar">
      <div class="brand">
        <div class="title">전기설비 수명관리 시스템</div>
        <div class="subtitle">각 설비의 PoF, CoF, DoF 지수를 평가하여 점검 설비 우선 순위를 도출합니다.</div>
      </div>
      <div class="filters">
        <button class="filtbtn" :class="{ active: store.factoryFilter === null }" @click="store.setFactoryFilter(null)">전체 사업장</button>
        <button v-for="f in factories" :key="f" class="filtbtn" :class="{ active: store.factoryFilter === f }" @click="store.setFactoryFilter(f)">
          {{ f }}
        </button>
        <span class="ef-badge">EF1 · 변압기</span>
      </div>
    </header>

    <div class="body">
      <aside class="rail">
        <div class="rail-title">설비유형</div>
        <div class="rail-row muted">EF1 · 변압기</div>
        <div class="rail-hint">EF2~EF22 설비유형 추가 예정</div>
      </aside>

      <main class="main">
        <div v-if="store.loading" class="loading">불러오는 중...</div>
        <div v-else-if="store.error" class="error">{{ store.error }}</div>
        <template v-else>
          <div class="kpi-row">
            <div class="card kpi">
              <div class="kpi-label">전체 설비</div>
              <div class="kpi-value">{{ store.equipmentList.length }}<span class="unit">대</span></div>
              <div class="kpi-sub">EF1 · 변압기 기준{{ store.factoryFilter ? ` · ${store.factoryFilter} 필터 적용` : "" }}</div>
            </div>
            <div class="card kpi">
              <div class="kpi-label">정상 설비</div>
              <div class="kpi-value normal">{{ store.equipmentList.length - store.needsInspectionList.length }}<span class="unit">대</span></div>
              <div class="kpi-sub">PoF·CoF·DoF 모두 기준 충족</div>
            </div>
            <div class="card kpi">
              <div class="kpi-label">점검 필요 설비</div>
              <div class="kpi-value flagged">{{ store.needsInspectionList.length }}<span class="unit">대</span></div>
              <div class="kpi-sub">PoF·CoF·DoF 중 기준 미달</div>
            </div>
            <div class="card kpi">
              <div class="kpi-label">최근 데이터 갱신</div>
              <div class="kpi-value small">{{ formatDateTime(store.summary?.last_updated ?? null) }}</div>
              <div class="kpi-sub">DGA · Furan 정기점검 반영</div>
            </div>
          </div>

          <div class="list-header">
            <div class="list-title">PoF·CoF·DoF 지수 3차원 분포도</div>
          </div>

          <div class="risk-panel">
            <div class="risk-header">
              <div class="risk-count">{{ store.needsInspectionList.length }}<span class="risk-label">건 점검필요</span></div>
              <div class="risk-desc">기준 미달 설비를 빨간색으로 표시</div>
            </div>
            <div class="risk-body">
              <div class="chart-col">
                <RiskScatterChart :equipment-list="store.equipmentList" :selected-id="selectedId" @select="selectCard" @hover="onChartHover" />
              </div>
              <div class="reason-col">
                <div class="reason-title">점검필요 순위 · 종합점수 낮은순</div>
                <div class="reason-hint">항목이 많아지면 이 영역 안에서만 스크롤됩니다</div>
                <div class="reason-scroll" ref="reasonScrollEl">
                  <div
                    v-for="entry in detailReasons"
                    :key="entry.item.equipment_id"
                    class="reason-card"
                    :class="{ active: selectedId === entry.item.equipment_id, hovered: hoveredId === entry.item.equipment_id }"
                    :data-equipment-id="entry.item.equipment_id"
                    @click="selectCard(entry.item.equipment_id)"
                  >
                    <div class="reason-row">
                      <span class="reason-name">{{ entry.item.transformer_name }}</span>
                      <span class="reason-score">종합점수 {{ entry.item.total_score.toFixed(1) }}</span>
                    </div>
                    <div class="reason-meta">{{ entry.item.factory_code }} · {{ entry.item.voltage.toLocaleString() }}V</div>

                    <div class="axis-grid">
                      <div class="axis-col">
                        <div class="axis-head" :class="{ fail: entry.item.pof < 20 }">PoF <b>{{ entry.item.pof }}</b></div>
                        <div v-for="reason in entry.reasons.pof" :key="reason.label" class="axis-reason">
                          {{ reason.label }} <span class="neg">{{ reason.value }}</span>
                        </div>
                        <div v-if="entry.reasons.pof.length === 0" class="axis-empty">감점 없음</div>
                      </div>
                      <div class="axis-col">
                        <div class="axis-head" :class="{ fail: entry.item.cof < 30 }">CoF <b>{{ entry.item.cof }}</b></div>
                        <div v-for="reason in entry.reasons.cof" :key="reason.label" class="axis-reason">
                          {{ reason.label }} <span class="neg">{{ reason.value }}</span>
                        </div>
                        <div v-if="entry.reasons.cof.length === 0" class="axis-empty">감점 없음</div>
                      </div>
                      <div class="axis-col">
                        <div class="axis-head" :class="{ fail: entry.item.dof < 20 }">DoF <b>{{ entry.item.dof }}</b></div>
                        <div v-for="reason in entry.reasons.dof" :key="reason.label" class="axis-reason">
                          {{ reason.label }} <span class="neg">{{ reason.value }}</span>
                        </div>
                        <div v-if="entry.reasons.dof.length === 0" class="axis-empty">감점 없음</div>
                      </div>
                    </div>
                  </div>
                  <div v-if="detailReasons.length === 0" class="muted">점검필요 설비가 없습니다</div>
                </div>
              </div>
            </div>
          </div>

          <div class="list-header">
            <div class="list-title">설비 목록</div>
            <div class="list-hint">전체 {{ store.equipmentList.length }}건 · 정렬: 종합점수 낮은순 · 카드를 클릭하면(또는 위 3D 그래프의 점을 클릭하면) 아래 상세정보가 갱신됩니다</div>
          </div>

          <EquipmentDetailPanel v-if="selectedId !== null" :equipment-id="selectedId" />

          <div class="card-grid">
            <EquipmentCard
              v-for="item in store.equipmentList"
              :key="item.equipment_id"
              :summary="item"
              :active="selectedId === item.equipment_id"
              @select="selectCard"
            />
          </div>
        </template>
      </main>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: #f4f5f7;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  color: #1a2230;
  display: flex;
  flex-direction: column;
}
.topbar {
  height: 96px;
  flex: 0 0 auto;
  background: #fff;
  border-bottom: 1px solid #e2e5ea;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 0 32px 14px;
}
.title {
  font-size: 24px;
  font-weight: 700;
}
.subtitle {
  font-size: 14px;
  color: #8891a0;
  margin-top: 4px;
}
.filters {
  display: flex;
  align-items: center;
  gap: 8px;
}
.filtbtn {
  border: 1px solid #e2e5ea;
  background: #fff;
  color: #4a5361;
  font: 500 13px "IBM Plex Sans", sans-serif;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
}
.filtbtn.active {
  background: #1a2230;
  border-color: #1a2230;
  color: #fff;
}
.ef-badge {
  font-size: 12px;
  color: #8891a0;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  padding: 5px 10px;
  margin-left: 4px;
}
.body {
  display: flex;
  flex: 1;
}
.rail {
  width: 224px;
  flex: 0 0 auto;
  background: #fff;
  border-right: 1px solid #e2e5ea;
  padding: 24px 20px;
}
.rail-title {
  font: 600 13px "IBM Plex Sans";
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #8891a0;
  margin-bottom: 10px;
}
.rail-row {
  font-size: 13px;
  padding: 5px 0;
}
.rail-hint {
  font-size: 11.5px;
  color: #b4bac4;
  margin-top: 2px;
}
.main {
  flex: 1;
  padding: 28px 32px 40px;
  overflow: auto;
}
.loading,
.error {
  padding: 40px;
  text-align: center;
  color: #8891a0;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.card {
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  padding: 16px 18px;
}
.kpi-label {
  font: 600 11px "IBM Plex Sans";
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #8891a0;
}
.kpi-value {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 28px;
  font-weight: 600;
  margin-top: 6px;
}
.kpi-value.small {
  font-size: 20px;
}
.kpi-value.normal {
  color: #3e8e8e;
}
.kpi-value.flagged {
  color: #c4392b;
}
.unit {
  font-size: 14px;
  color: #8891a0;
  font-weight: 500;
}
.kpi-sub {
  font-size: 11.5px;
  color: #8891a0;
  margin-top: 4px;
}
.risk-panel {
  background: #fff;
  border: 1px solid #f0cfc9;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 28px;
}
.risk-header {
  display: flex;
  align-items: baseline;
  gap: 14px;
  padding: 18px 22px;
  background: #fcf1ef;
  border-bottom: 1px solid #f0cfc9;
}
.risk-count {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 30px;
  font-weight: 700;
  color: #c4392b;
}
.risk-label {
  font-size: 14px;
  font-family: "IBM Plex Sans";
  font-weight: 600;
}
.risk-desc {
  font-size: 12px;
  color: #96382f;
}
.risk-body {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(380px, 1.3fr);
  height: 540px;
}
.chart-col {
  padding: 18px 10px 8px 18px;
  border-right: 1px solid #eef0f3;
}
.reason-col {
  padding: 18px 22px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}
.reason-title {
  font: 600 11px "IBM Plex Sans";
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #8891a0;
  margin-bottom: 4px;
}
.reason-hint {
  font-size: 10.5px;
  color: #b4bac4;
  margin-bottom: 10px;
}
.reason-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 6px;
}
.reason-card {
  border: 1px solid #f0cfc9;
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 10px;
  cursor: pointer;
}
.reason-card.active {
  border-color: #c4392b;
  border-width: 2px;
  padding: 11px 13px;
  background: #fff8f7;
}
.reason-card.hovered:not(.active) {
  border-color: #0f8a8a;
  box-shadow: 0 0 0 2px rgba(15, 138, 138, 0.15);
}
.reason-row {
  display: flex;
  justify-content: space-between;
}
.reason-name {
  font-weight: 700;
}
.reason-score {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 700;
  color: #c4392b;
}
.reason-meta {
  font-size: 11px;
  color: #8891a0;
  margin-bottom: 8px;
}
.axis-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0 10px;
}
.axis-col {
  min-width: 0;
  border-left: 1px solid #f0cfc9;
  padding-left: 8px;
}
.axis-col:first-child {
  border-left: none;
  padding-left: 0;
}
.axis-head {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px;
  font-weight: 600;
  color: #4a5361;
  margin-bottom: 4px;
}
.axis-head.fail {
  color: #c4392b;
}
.axis-reason {
  font-size: 10.5px;
  color: #4a5361;
  line-height: 1.5;
  overflow-wrap: break-word;
}
.axis-empty {
  font-size: 10.5px;
  color: #b4bac4;
}
.neg {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  color: #c4392b;
}
.list-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 14px;
}
.list-title {
  font-size: 15px;
  font-weight: 700;
}
.list-hint {
  font-size: 12px;
  color: #8891a0;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 16px;
}
.muted {
  color: #8891a0;
  font-size: 12px;
}
</style>
