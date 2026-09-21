<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import type { EquipmentSummary } from "../types/equipment";

const props = defineProps<{ equipmentList: EquipmentSummary[]; selectedPof: number; highlightColor: string }>();

const NEUTRAL = "#C7CCD3";
const PAD_L = 20;
const PAD_B = 16;
const PAD_T = 14;
const BAR_GAP = 3;

const wrapEl = ref<HTMLDivElement | null>(null);
const width = ref(280);
const height = ref(130);
let observer: ResizeObserver | null = null;

onMounted(() => {
  if (!wrapEl.value) return;
  observer = new ResizeObserver((entries) => {
    const box = entries[0]?.contentRect;
    if (box) {
      width.value = box.width;
      height.value = box.height;
    }
  });
  observer.observe(wrapEl.value);
});

onUnmounted(() => observer?.disconnect());

function binIndex(value: number): number {
  return Math.min(9, Math.max(0, Math.floor(Math.min(99, Math.max(0, value)) / 10)));
}

const bars = computed(() => {
  const counts = new Array(10).fill(0);
  for (const item of props.equipmentList) counts[binIndex(item.pof)]++;
  const selected = binIndex(props.selectedPof);
  const max = Math.max(1, ...counts);
  const plotW = width.value - PAD_L;
  const plotH = height.value - PAD_T - PAD_B;
  const barW = plotW / 10 - BAR_GAP;

  return counts.map((count, i) => {
    const barH = (count / max) * plotH;
    return {
      x: PAD_L + i * (plotW / 10) + BAR_GAP / 2,
      y: PAD_T + (plotH - barH),
      width: Math.max(0, barW),
      height: barH,
      count,
      isSelected: i === selected,
      label: i % 2 === 0 ? `${i * 10}` : "",
    };
  });
});
</script>

<template>
  <div class="chart-block">
    <div ref="wrapEl" class="chart-svg-wrap">
      <svg :viewBox="`0 0 ${width} ${height}`" class="chart-svg" preserveAspectRatio="none">
        <line :x1="PAD_L" :y1="height - PAD_B" :x2="width" :y2="height - PAD_B" stroke="#EEF0F3" stroke-width="1" />
        <g v-for="(bar, i) in bars" :key="i">
          <rect :x="bar.x" :y="bar.y" :width="bar.width" :height="bar.height" rx="2" :fill="bar.isSelected ? highlightColor : NEUTRAL">
            <title>POF {{ i * 10 }}-{{ i * 10 + 10 }} · {{ bar.count }}대</title>
          </rect>
          <text v-if="bar.isSelected" :x="bar.x + bar.width / 2" :y="bar.y - 4" text-anchor="middle" class="bar-count" :fill="highlightColor">
            {{ bar.count }}
          </text>
          <text :x="bar.x + bar.width / 2" :y="height - PAD_B + 10" text-anchor="middle" class="axis-tick">{{ bar.label }}</text>
        </g>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.chart-block {
  min-width: 0;
  height: 150px;
}
.chart-svg-wrap {
  width: 100%;
  height: 150px;
}
.chart-svg {
  width: 100%;
  height: 100%;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.axis-tick {
  font-size: 6.5px;
  fill: #b4bac4;
}
.bar-count {
  font-size: 8px;
  font-weight: 700;
}
</style>
