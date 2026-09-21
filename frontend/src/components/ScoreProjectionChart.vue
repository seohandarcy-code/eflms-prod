<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

const props = defineProps<{ currentScore: number; color: string }>();

const YEARS = [0, 1, 2, 3, 4, 5];
const PAD_L = 26;
const PAD_R = 8;
const PAD_T = 18;
const PAD_B = 20;

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

const points = computed(() => {
  const values = YEARS.map((y) => props.currentScore - y);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(1, max - min);
  const plotW = width.value - PAD_L - PAD_R;
  const plotH = height.value - PAD_T - PAD_B;

  return values.map((value, i) => ({
    x: PAD_L + (i / (YEARS.length - 1)) * plotW,
    y: PAD_T + plotH - ((value - min) / range) * plotH,
    value,
    label: i === 0 ? "현재" : `${i}년후`,
  }));
});

const linePath = computed(() => points.value.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" "));
</script>

<template>
  <div class="chart-block">
    <div ref="wrapEl" class="chart-svg-wrap">
      <svg :viewBox="`0 0 ${width} ${height}`" class="chart-svg" preserveAspectRatio="none">
        <line :x1="PAD_L" :y1="height - PAD_B" :x2="width - PAD_R" :y2="height - PAD_B" stroke="#EEF0F3" stroke-width="1" />
        <path :d="linePath" fill="none" :stroke="color" stroke-width="2" stroke-dasharray="4 3" />
        <g v-for="(p, i) in points" :key="i">
          <circle :cx="p.x" :cy="p.y" r="4" :fill="color" />
          <text :x="p.x" :y="p.y - 8" text-anchor="middle" class="point-value" :fill="color">{{ p.value.toFixed(1) }}</text>
          <text :x="p.x" :y="height - PAD_B + 11" text-anchor="middle" class="axis-tick">{{ p.label }}</text>
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
  font-size: 7px;
  fill: #b4bac4;
}
.point-value {
  font-size: 8.5px;
  font-weight: 700;
}
</style>
