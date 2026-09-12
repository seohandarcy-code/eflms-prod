<script setup lang="ts">
import { computed } from "vue";
import type { EquipmentSummary } from "../types/equipment";

const props = defineProps<{ summary: EquipmentSummary; active?: boolean }>();
const emit = defineEmits<{ select: [equipmentId: number] }>();

function clampWidth(value: number): number {
  return Math.max(0, Math.min(100, value));
}

const statusColor = computed(() => (props.summary.needs_inspection ? "#C4392B" : "#1B8A5A"));
</script>

<template>
  <div class="equipment-card" :class="{ active }" @click="emit('select', summary.equipment_id)">
    <div class="card-head">
      <div>
        <span class="name">{{ summary.transformer_name }}</span>
        <span class="meta">{{ summary.factory_code }} · {{ summary.voltage.toLocaleString() }}V</span>
      </div>
      <span class="chip" :style="{ background: summary.needs_inspection ? '#FBE7E4' : '#E4F3EA', color: statusColor }">
        <span class="dot" :style="{ background: statusColor }"></span>
        {{ summary.needs_inspection ? "점검필요" : "정상" }}
      </span>
    </div>

    <div class="mini-bars">
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
.equipment-card.active {
  border-color: #c4392b;
  box-shadow: 0 0 0 2px rgba(196, 57, 43, 0.15);
}
.equipment-card:hover {
  border-color: #c7ccd3;
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
.mono {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
</style>
