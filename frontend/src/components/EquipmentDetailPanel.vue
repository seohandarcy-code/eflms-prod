<script setup lang="ts">
import { ref, watch } from "vue";
import { useEquipmentStore } from "../stores/equipment";
import type { EquipmentDetail } from "../types/equipment";

const props = defineProps<{ equipmentId: number }>();

const store = useEquipmentStore();
const detail = ref<EquipmentDetail | null>(store.detailCache[props.equipmentId] ?? null);
const loading = ref(false);

watch(
  () => props.equipmentId,
  async (id) => {
    detail.value = store.detailCache[id] ?? null;
    if (detail.value) return;
    loading.value = true;
    try {
      detail.value = await store.loadDetail(id);
    } finally {
      loading.value = false;
    }
  },
  { immediate: true },
);

function clampWidth(value: number): number {
  return Math.max(0, Math.min(100, value));
}

function formatMonth(isoDate: string): string {
  return isoDate.slice(0, 7);
}
</script>

<template>
  <div class="panel">
    <div v-if="loading || !detail" class="loading">불러오는 중...</div>
    <template v-else>
      <div class="eyebrow">선택된 설비</div>
      <div class="panel-head">
        <div class="name-row">
          <span class="name">{{ detail.transformer_name }}</span>
          <span class="chip" :style="{ background: detail.needs_inspection ? '#FBE7E4' : '#E4F3EA', color: detail.needs_inspection ? '#C4392B' : '#1B8A5A' }">
            {{ detail.needs_inspection ? "점검필요" : "정상" }}
          </span>
        </div>
        <div class="meta">
          {{ detail.factory_code }} · {{ detail.voltage.toLocaleString() }}V · ONAN {{ detail.onan_val }}MVA · 가동 {{ formatMonth(detail.operation_start_time) }}
        </div>
      </div>

      <div class="body">
        <div class="score-bars">
          <span>PoF</span>
          <div class="bar-track"><div class="bar-fill" :style="{ width: clampWidth(detail.score.pof) + '%', background: detail.score.pof < 20 ? '#C4392B' : '#3E8E8E' }" /></div>
          <span class="bar-value mono">{{ detail.score.pof }}</span>
          <span>CoF</span>
          <div class="bar-track"><div class="bar-fill" :style="{ width: clampWidth(detail.score.cof) + '%', background: detail.score.cof < 30 ? '#C4392B' : '#3E8E8E' }" /></div>
          <span class="bar-value mono">{{ detail.score.cof }}</span>
          <span>DoF</span>
          <div class="bar-track"><div class="bar-fill" :style="{ width: clampWidth(detail.score.dof) + '%', background: detail.score.dof < 20 ? '#C4392B' : '#3E8E8E' }" /></div>
          <span class="bar-value mono">{{ detail.score.dof }}</span>
        </div>

        <div class="detail-grid">
          <div class="detail-col">
            <div class="detail-title">DGA (유중가스)</div>
            <div class="mono">TCG {{ detail.score_detail.dga_tcg }}ppm</div>
            <div class="muted">판정: {{ detail.score_detail.dga_diag }}</div>
          </div>
          <div class="detail-col">
            <div class="detail-title">부하 · 온도</div>
            <div class="mono">부하율 {{ detail.load.load_percent }}%</div>
            <div class="muted">권선 최고온도 {{ detail.load.coil_max_temp }}℃</div>
          </div>
          <div class="detail-col">
            <div class="detail-title">절연 · 유중시험</div>
            <div class="mono">절연내력 평균 {{ detail.score_detail.dielec_str_te_avg.toFixed(1) }}kV</div>
            <div class="muted">산가도 {{ detail.score_detail.acid_measure_desc }}</div>
          </div>
          <div class="detail-col">
            <div class="detail-title">설계속성</div>
            <div class="muted">예비화 {{ detail.design.redundancy }} · 계통자동전환 {{ detail.design.ato }}</div>
            <div class="muted">온라인 유중가스 {{ detail.design.online_og_chk }} · 안전공사 정밀점검 {{ detail.design.offline_safety_chk }}</div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.panel {
  background: #fff;
  border: 1px solid #c4392b;
  box-shadow: 0 0 0 2px rgba(196, 57, 43, 0.12);
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
.eyebrow {
  font: 600 11px "IBM Plex Sans";
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #c4392b;
  margin-bottom: 8px;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
}
.name-row {
  display: flex;
  align-items: center;
  gap: 10px;
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
.meta {
  font-size: 12px;
  color: #8891a0;
}
.body {
  margin-top: 16px;
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 24px;
}
.score-bars {
  display: grid;
  grid-template-columns: 34px 1fr 34px;
  gap: 8px 10px;
  align-items: center;
  font-size: 12px;
  color: #8891a0;
}
.bar-track {
  height: 5px;
  background: #eef0f3;
  border-radius: 3px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
}
.bar-value {
  font-size: 11px;
  color: #4a5361;
  text-align: right;
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  font-size: 12.5px;
}
.detail-title {
  font-weight: 600;
  color: #4a5361;
  margin-bottom: 6px;
}
.mono {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.muted {
  color: #8891a0;
}
</style>
