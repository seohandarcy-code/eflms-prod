<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import type { EquipmentSummary } from "../types/equipment";

const props = defineProps<{ equipmentList: EquipmentSummary[]; selectedPof: number; highlightColor: string }>();

const NEUTRAL = "#C7CCD3";
const PAD_L = 20;
const PAD_B = 16;
const PAD_T = 14;
const BAR_GAP = 3;
const CARD_WIDTH = 180;

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

const hoveredBin = ref<number | null>(null);
const cursorPos = ref({ x: 0, y: 0 });

function onBarEnter(i: number) {
  hoveredBin.value = i;
}
function onBarLeave() {
  hoveredBin.value = null;
}
function onWrapMouseMove(event: MouseEvent) {
  if (!wrapEl.value) return;
  const rect = wrapEl.value.getBoundingClientRect();
  cursorPos.value = { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

const tooltipStyle = computed(() => {
  const maxLeft = Math.max(width.value - CARD_WIDTH - 4, 4);
  const left = Math.min(Math.max(cursorPos.value.x + 14, 4), maxLeft);
  const top = Math.min(Math.max(cursorPos.value.y - 12, 4), height.value - 4);
  return { left: `${left}px`, top: `${top}px` };
});
</script>

<template>
  <div class="chart-block">
    <div ref="wrapEl" class="chart-svg-wrap" @mousemove="onWrapMouseMove">
      <svg :viewBox="`0 0 ${width} ${height}`" class="chart-svg" preserveAspectRatio="none">
        <line :x1="PAD_L" :y1="height - PAD_B" :x2="width" :y2="height - PAD_B" stroke="#EEF0F3" stroke-width="1" />
        <g v-for="(bar, i) in bars" :key="i">
          <rect
            :x="bar.x"
            :y="bar.y"
            :width="bar.width"
            :height="bar.height"
            rx="2"
            :fill="bar.isSelected ? highlightColor : NEUTRAL"
            @mouseenter="onBarEnter(i)"
            @mouseleave="onBarLeave"
          />
          <text v-if="bar.isSelected" :x="bar.x + bar.width / 2" :y="bar.y - 4" text-anchor="middle" class="bar-count" :fill="highlightColor">
            {{ bar.count }}
          </text>
          <text :x="bar.x + bar.width / 2" :y="height - PAD_B + 10" text-anchor="middle" class="axis-tick">{{ bar.label }}</text>
        </g>
      </svg>

      <div v-if="hoveredBin !== null" class="bar-tooltip" :style="tooltipStyle">
        <div class="bt-head">
          <span class="bt-dot"></span>
          <span class="bt-name">POF {{ hoveredBin * 10 }}-{{ hoveredBin * 10 + 10 }}</span>
          <span class="bt-value">{{ bars[hoveredBin].count }}대</span>
        </div>
        <div class="bt-caption">이 구간에 속한 설비 수</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chart-block {
  min-width: 0;
  height: 150px;
}
.chart-svg-wrap {
  position: relative;
  width: 100%;
  max-width: 660px;
  height: 150px;
}
.chart-svg {
  width: 100%;
  height: 100%;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.axis-tick {
  font-size: 11px;
  fill: #b4bac4;
}
.bar-count {
  font-size: 12px;
  font-weight: 700;
}
.bar-tooltip {
  position: absolute;
  z-index: 6;
  width: 180px;
  background: #fff;
  border: 1px solid #1b8a5a;
  border-radius: 9px;
  padding: 10px 12px;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.14);
  pointer-events: none;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
}
.bt-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.bt-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #1b8a5a;
  flex: 0 0 auto;
}
.bt-name {
  font-weight: 700;
  color: #1b8a5a;
  font-size: 12px;
}
.bt-value {
  margin-left: auto;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 700;
  color: #1a2230;
  font-size: 12px;
}
.bt-caption {
  font-size: 11px;
  color: #4a5361;
  opacity: 0.85;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  padding-top: 6px;
}
</style>
