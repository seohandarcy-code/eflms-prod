<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { EquipmentSummary } from "../types/equipment";
import { useEquipmentStore } from "../stores/equipment";

const props = defineProps<{ summary: EquipmentSummary; expanded: boolean }>();
const emit = defineEmits<{ toggle: [equipmentId: number] }>();

const store = useEquipmentStore();
const detail = ref(store.detailCache[props.summary.equipment_id] ?? null);
const loading = ref(false);

watch(
  () => props.expanded,
  async (isExpanded) => {
    if (!isExpanded || detail.value) return;
    loading.value = true;
    try {
      detail.value = await store.loadDetail(props.summary.equipment_id);
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

const statusColor = computed(() => (props.summary.needs_inspection ? "#C4392B" : "#1B8A5A"));
</script>

<template>
  <div
    class="equipment-card"
    :class="{ expanded }"
    :style="{ gridColumn: expanded ? '1 / -1' : undefined, borderColor: expanded ? '#C4392B' : undefined }"
    @click="emit('toggle', summary.equipment_id)"
  >
    <div class="card-head">
      <div>
        <span class="name">{{ summary.transformer_name }}</span>
        <span v-if="!expanded" class="meta">{{ summary.factory_code }} · {{ summary.voltage.toLocaleString() }}V</span>
      </div>
      <span class="chip" :style="{ background: summary.needs_inspection ? '#FBE7E4' : '#E4F3EA', color: statusColor }">
        <span class="dot" :style="{ background: statusColor }"></span>
        {{ summary.needs_inspection ? "점검필요" : "정상" }}
      </span>
    </div>

    <div v-if="!expanded" class="mini-bars">
      <div class="bar-row">
        <span>PoF</span>
        <div class="bar-track"><div class="bar-fill" :style="{ width: clampWidth(summary.pof) + '%', background: summary.pof < 20 ? '#C4392B' : '#3E8E8E' }" /></div>
        <span class="bar-value mono">{{ summary.pof }}</span>
      </div>
      <div class="bar-row">
        <span>CoF</span>
        <div class="bar-track"><div class="bar-fill" :style="{ width: clampWidth(summary.cof) + '%', background: summary.cof < 30 ? '#C4392B' : '#3E8E8E' }" /></div>
        <span class="bar-value mono">{{ summary.cof }}</span>
      </div>
      <div class="bar-row">
        <span>DoF</span>
        <div class="bar-track"><div class="bar-fill" :style="{ width: clampWidth(summary.dof) + '%', background: summary.dof < 20 ? '#C4392B' : '#3E8E8E' }" /></div>
        <span class="bar-value mono">{{ summary.dof }}</span>
      </div>
      <div class="foot">
        <span class="score">{{ summary.total_score.toFixed(1) }}</span>
        <span class="date">{{ summary.last_diag_date }}</span>
      </div>
    </div>

    <div v-else class="detail">
      <div v-if="loading || !detail">불러오는 중...</div>
      <template v-else>
        <div class="expanded-meta">
          {{ detail.factory_code }} · {{ detail.voltage.toLocaleString() }}V · ONAN {{ detail.onan_val }}MVA · 가동 {{ formatMonth(detail.operation_start_time) }}
        </div>

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

        <div class="divider"></div>

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
      </template>
    </div>
  </div>
</template>

<style scoped>
.equipment-card {
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
  gap: 8px;
}
.name {
  font-weight: 700;
}
.meta {
  display: block;
  font-size: 11px;
  color: #8891a0;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.mini-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.bar-row {
  display: grid;
  grid-template-columns: 34px 1fr 30px;
  gap: 8px;
  align-items: center;
  font-size: 10.5px;
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
.expanded-meta {
  font-size: 12px;
  color: #8891a0;
  margin-bottom: 14px;
}
.score-bars {
  display: grid;
  grid-template-columns: 120px 1fr 34px;
  gap: 6px 14px;
  align-items: center;
  font-size: 12px;
  color: #8891a0;
}
.divider {
  height: 1px;
  background: #eef0f3;
  margin: 16px 0;
}
.foot {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 11px;
  color: #8891a0;
}
.score {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 700;
  color: #1a2230;
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
