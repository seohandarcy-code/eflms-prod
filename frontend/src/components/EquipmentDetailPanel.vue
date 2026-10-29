<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useEquipmentStore } from "../stores/equipment";
import type { EquipmentDetail } from "../types/equipment";
import { formatMonth } from "../utils/formatDate";
import { na } from "../utils/formatValue";
import { statusBg, statusColor, statusLabel } from "../utils/statusStyle";
import PofDistributionChart from "./PofDistributionChart.vue";
import ScoreProjectionChart from "./ScoreProjectionChart.vue";
import Ef1DetailBody from "./detail/Ef1DetailBody.vue";
import Ef2DetailBody from "./detail/Ef2DetailBody.vue";
import Ef3DetailBody from "./detail/Ef3DetailBody.vue";
import Ef4DetailBody from "./detail/Ef4DetailBody.vue";

const props = defineProps<{ equipmentId: number }>();

const store = useEquipmentStore();
const detail = ref<EquipmentDetail | null>(store.detailCache[props.equipmentId] ?? null);
const loading = ref(false);
const showRaw = ref(false);

watch(
  () => props.equipmentId,
  async (id) => {
    detail.value = store.detailCache[id] ?? null;
    if (detail.value) return;
    loading.value = true;
    try {
      const fetched = await store.loadDetail(id);
      // 응답이 도착했을 때 사용자가 이미 다른 설비를 선택했다면(더 빠른 최신 요청이 이미 반영된
      // 상태라면) 뒤늦게 도착한 이 응답으로 화면을 덮어쓰지 않는다.
      if (props.equipmentId === id) {
        detail.value = fetched;
      }
    } finally {
      if (props.equipmentId === id) {
        loading.value = false;
      }
    }
  },
  { immediate: true },
);

function clampWidth(value: number): number {
  return Math.max(0, Math.min(100, value));
}

const color = computed(() => (detail.value ? statusColor(detail.value.status) : "#8891a0"));

// 헤더 부제 — 유형마다 대표 사양이 다르다(EF1 정격용량, EF2 조작방식, EF3 굵기·회선별용량, EF4 설비명·설치위치). 본문은 detail/Ef*DetailBody.vue (Stage 8-5).
const typeSubtitle = computed(() => {
  const typeDetail = detail.value?.type_detail;
  if (typeDetail?.ef_code === "EF1") return `ONAN ${na(typeDetail.spec.onan_val, { unit: "MVA" })}`;
  if (typeDetail?.ef_code === "EF2") return `조작방식 ${na(typeDetail.operation.op_type)}`;
  if (typeDetail?.ef_code === "EF3") return `${na(typeDetail.spec.cable_sq, { unit: "sq" })} × ${na(typeDetail.spec.cable_per_phase)} · ${na(typeDetail.spec.cable_mva, { unit: "MVA" })}`;
  if (typeDetail?.ef_code === "EF4") return `${na(typeDetail.spec.eqp_id_name)} · ${na(typeDetail.spec.eqp_building)} ${na(typeDetail.spec.eqp_floor)} · ${na(typeDetail.spec.eqp_disting)}`;
  return "";
});
// POF 분포는 같은 설비유형끼리 비교한다(유형마다 감점 체계가 달라서).
const sameTypeList = computed(() => store.equipmentList.filter((item) => item.ef_code === detail.value?.ef_code));
</script>

<template>
  <div class="panel" :style="detail ? { borderColor: color } : {}">
    <div v-if="loading || !detail" class="loading">불러오는 중...</div>
    <template v-else>
      <div class="panel-grid">
        <div class="eyebrow">선택된 설비</div>
        <div class="meta">
          {{ detail.factory_code }} · {{ typeSubtitle }} · 가동 {{ formatMonth(detail.operation_start_time) }}
        </div>

        <div class="name-row">
          <span class="name">{{ detail.equipment_name }}</span>
          <span class="type-badge">{{ detail.ef_name }}</span>
          <span class="chip" :style="{ background: statusBg(detail.status), color }">
            {{ statusLabel(detail.status) }}
          </span>
          <span class="total-score-badge">종합점수: {{ detail.score.total_score.toFixed(1) }}</span>
        </div>
        <div class="chart-title chart-title-1">POF 분포 <span class="muted">· 같은 설비유형({{ detail.ef_name }}) 중 이 설비 구간 강조</span></div>
        <div class="chart-title chart-title-2">5개년 POF 예측 <span class="muted">· 연 -1점 단순 가정(실제 예측 아님)</span></div>

        <div class="left-col">
          <div class="score-bars">
            <span>POF</span>
            <div class="bar-track"><div class="bar-fill" :style="{ width: clampWidth(detail.score.pof) + '%', background: color }" /></div>
            <span class="bar-value mono">{{ detail.score.pof }}</span>
            <span>COF</span>
            <div class="bar-track"><div class="bar-fill" :style="{ width: clampWidth(detail.score.cof) + '%', background: color }" /></div>
            <span class="bar-value mono">{{ detail.score.cof }}</span>
            <span>DOF</span>
            <div class="bar-track"><div class="bar-fill" :style="{ width: clampWidth(detail.score.dof) + '%', background: color }" /></div>
            <span class="bar-value mono">{{ detail.score.dof }}</span>
          </div>
        </div>

        <div class="chart-cell chart-cell-1">
          <PofDistributionChart :equipment-list="sameTypeList" :selected-pof="detail.score.pof" :highlight-color="color" />
        </div>
        <div class="chart-cell chart-cell-2">
          <ScoreProjectionChart :current-score="detail.score.pof" :color="color" />
        </div>
      </div>

      <div class="raw-section">
        <button type="button" class="raw-toggle" @click="showRaw = !showRaw">
          {{ showRaw ? "원본 데이터 접기" : "원본 데이터 전체 보기" }}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :style="{ transform: showRaw ? 'rotate(180deg)' : 'none' }">
            <path d="M6 9 L12 15 L18 9" />
          </svg>
        </button>

        <div v-if="showRaw" class="raw-groups">
          <Ef1DetailBody v-if="detail.type_detail.ef_code === 'EF1'" :type-detail="detail.type_detail" />
          <Ef2DetailBody v-else-if="detail.type_detail.ef_code === 'EF2'" :type-detail="detail.type_detail" />
          <Ef3DetailBody v-else-if="detail.type_detail.ef_code === 'EF3'" :type-detail="detail.type_detail" />
          <Ef4DetailBody v-else-if="detail.type_detail.ef_code === 'EF4'" :type-detail="detail.type_detail" />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.panel {
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 20px 24px;
  margin-bottom: 20px;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  color: #1a2230;
}
.loading {
  color: #8891a0;
  padding: 16px 0;
}
.panel-grid {
  display: grid;
  grid-template-columns: 420px 1fr 1fr;
  grid-template-rows: auto auto 150px;
  column-gap: 28px;
  row-gap: 6px;
  grid-template-areas:
    "eyebrow meta   meta"
    "name    title1 title2"
    "info    chart1 chart2";
}
.eyebrow {
  grid-area: eyebrow;
  font: 600 11px "IBM Plex Sans";
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #c4392b;
  align-self: end;
}
.meta {
  grid-area: meta;
  justify-self: end;
  align-self: end;
  font-size: 12px;
  color: #8891a0;
}
.name-row {
  grid-area: name;
  align-self: end;
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 10px;
}
.name {
  font-size: 18px;
  font-weight: 700;
}
.chip {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.total-score-badge {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 13px;
  font-weight: 700;
  color: #1a2230;
  background: #f4f5f7;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  padding: 3px 10px;
}
.chart-title {
  align-self: end;
  padding-top: 10px;
  margin-bottom: 13px;
  font-size: 13px;
  font-weight: 600;
  color: #4a5361;
}
.chart-title-1 {
  grid-area: title1;
}
.chart-title-2 {
  grid-area: title2;
}
.chart-cell {
  min-width: 0;
}
.chart-cell-1 {
  grid-area: chart1;
}
.chart-cell-2 {
  grid-area: chart2;
}
/* 왼쪽 칸(420×150)은 POF·COF·DOF 막대만 — 요약 4줄을 빼고 칸 전체를 채운다(2026-10-29).
   막대는 길이가 약 4배(90→320px)라 두께는 2배(5→10px)만 키워 납작한 비율을 유지한다. */
.left-col {
  grid-area: info;
  display: flex;
}
.score-bars {
  flex: 1;
  display: grid;
  grid-template-columns: 40px 1fr 40px;
  grid-template-rows: repeat(3, 1fr);
  column-gap: 12px;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: #8891a0;
}
.bar-track {
  height: 10px;
  background: #eef0f3;
  border-radius: 5px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 5px;
}
.bar-value {
  font-size: 14px;
  font-weight: 700;
  color: #4a5361;
  text-align: right;
}
.panel :deep(.mono) {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.muted {
  color: #8891a0;
}
.raw-section {
  margin-top: 16px;
}
.raw-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  padding: 6px 12px;
  border: 1px solid #d8dbe2;
  border-radius: 999px;
  background: #f7f8fa;
  color: #4a5361;
  font: 600 12px "IBM Plex Sans", system-ui, sans-serif;
  cursor: pointer;
}
.raw-toggle:hover {
  background: #eef0f3;
}
.raw-toggle svg {
  transition: transform 0.15s ease;
}
.raw-groups {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 4px;
  align-items: start;
}
.panel :deep(.raw-group) {
  border: 1px solid #eef0f3;
  border-radius: 8px;
  padding: 10px 12px;
  min-width: 0;
}
.panel :deep(.raw-title) {
  font-weight: 600;
  font-size: 12px;
  color: #c4392b;
  margin-bottom: 8px;
}
.panel :deep(.raw-subgrid) {
  display: grid;
  gap: 12px;
}
.panel :deep(.raw-subgroup) {
  min-width: 0;
}
.panel :deep(.raw-subtitle) {
  font-weight: 600;
  font-size: 11px;
  color: #4a5361;
  margin-bottom: 4px;
}
.panel :deep(.raw-fields) {
  display: grid;
  gap: 4px;
}
.panel :deep(.raw-field) {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: #4a5361;
}
.panel :deep(.raw-field span) {
  color: #8891a0;
}
.panel :deep(.raw-field b) {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 600;
  text-align: right;
  white-space: nowrap;
}
.panel :deep(.neg) {
  color: #c4392b;
}
.type-badge {
  font-size: 11px;
  font-weight: 600;
  color: #4a5568;
  background: #eef0f3;
  border-radius: 4px;
  padding: 2px 6px;
}
</style>
