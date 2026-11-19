<script setup lang="ts">
// 5개년 POF 예측(Stage 21-2) — 서버 projection(저장된 입력으로 기준일만 1~5년 늦춰 같은 공식으로 다시 계산)을 그린다.
// 점 색은 그 해 판정, 마우스를 올리면 그 해 POF·판정·바뀐 감점 항목. POF가 오른 해는 ▲와 이유(utils/projection.ts).
import { computed, onMounted, onUnmounted, ref } from "vue";
import type { ProjectionPoint } from "../types/equipment";
import { formatScore } from "../utils/formatValue";
import { projectionView, risingReason, signed } from "../utils/projection";
import { statusColor, statusLabel } from "../utils/statusStyle";

const props = defineProps<{ points: ProjectionPoint[]; color: string }>();

const PAD_L = 26;
const PAD_R = 22;
const PAD_T = 18;
const PAD_B = 33;
const CARD_WIDTH = 220;

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

const views = computed(() => projectionView(props.points));

const dots = computed(() => {
  const values = views.value.map((v) => v.pof);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(1, max - min);
  const plotW = width.value - PAD_L - PAD_R;
  const plotH = height.value - PAD_T - PAD_B;
  const last = Math.max(1, views.value.length - 1);
  return views.value.map((v, i) => ({
    ...v,
    x: PAD_L + (i / last) * plotW,
    y: PAD_T + plotH - ((v.pof - min) / range) * plotH,
    fill: statusColor(v.status),
  }));
});

const linePath = computed(() => dots.value.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" "));

const hovered = ref<number | null>(null);
const hoveredView = computed(() => (hovered.value === null ? null : dots.value[hovered.value]));
const tooltipStyle = computed(() => {
  const dot = hoveredView.value;
  if (!dot) return {};
  const maxLeft = Math.max(width.value - CARD_WIDTH - 4, 4);
  const left = Math.min(Math.max(dot.x - CARD_WIDTH / 2, 4), maxLeft);
  return { left: `${left}px`, top: `${Math.max(dot.y - 10, 4)}px`, transform: "translateY(-100%)" };
});
</script>

<template>
  <div class="chart-block">
    <div ref="wrapEl" class="chart-svg-wrap">
      <svg v-if="dots.length" :viewBox="`0 0 ${width} ${height}`" class="chart-svg" preserveAspectRatio="none">
        <line :x1="PAD_L" :y1="height - PAD_B" :x2="width - PAD_R" :y2="height - PAD_B" stroke="#EEF0F3" stroke-width="1" />
        <path :d="linePath" fill="none" :stroke="color" stroke-width="2" stroke-dasharray="4 3" />
        <g v-for="(p, i) in dots" :key="i" class="dot" @mouseenter="hovered = i" @mouseleave="hovered = null">
          <circle :cx="p.x" :cy="p.y" r="12" fill="transparent" />
          <circle :cx="p.x" :cy="p.y" r="4.5" :fill="p.fill" :stroke="hovered === i ? '#1a2230' : '#fff'" stroke-width="1.5" />
          <text :x="p.x" :y="p.y - 9" text-anchor="middle" class="point-value" :fill="p.fill">
            {{ p.rising ? "▲" : "" }}{{ formatScore(p.pof) }}
          </text>
          <text :x="p.x" :y="height - PAD_B + 22" text-anchor="middle" class="axis-tick">{{ p.label }}</text>
        </g>
      </svg>
      <div v-else class="empty">예측할 입력 데이터가 없습니다</div>

      <div v-if="hoveredView" class="proj-tooltip" :style="{ ...tooltipStyle, borderColor: hoveredView.fill }">
        <div class="pt-head">
          <span class="pt-dot" :style="{ background: hoveredView.fill }"></span>
          <span class="pt-name">{{ hoveredView.label }} · {{ points[hovered ?? 0].as_of }}</span>
        </div>
        <div class="pt-row">
          POF <b>{{ formatScore(hoveredView.pof) }}</b>
          <span :style="{ color: hoveredView.fill }">· {{ statusLabel(hoveredView.status) }}</span>
        </div>
        <div v-if="risingReason(hoveredView)" class="pt-rise">{{ risingReason(hoveredView) }}</div>
        <ul v-if="hoveredView.changes.length" class="pt-changes">
          <li v-for="c in hoveredView.changes.slice(0, 6)" :key="c.field">
            <span>{{ c.label }}</span>
            <span :class="c.delta > 0 ? 'up' : 'down'">{{ signed(c.delta) }}</span>
          </li>
          <li v-if="hoveredView.changes.length > 6" class="more">외 {{ hoveredView.changes.length - 6 }}개 항목</li>
        </ul>
        <div v-else-if="(hovered ?? 0) > 0" class="pt-caption">직전 해와 같은 감점</div>
        <div v-else class="pt-caption">지금 저장된 점수(점수 기준일)</div>
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
.dot {
  cursor: help;
}
.axis-tick {
  font-size: 11px;
  fill: #b4bac4;
}
.point-value {
  font-size: 12px;
  font-weight: 700;
}
.empty {
  font-size: 12px;
  color: #8891a0;
  padding-top: 40px;
}
.proj-tooltip {
  position: absolute;
  z-index: 6;
  width: 220px;
  background: #fff;
  border: 1px solid #1a2230;
  border-radius: 9px;
  padding: 10px 12px;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.14);
  pointer-events: none;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  font-size: 12px;
  color: #1a2230;
}
.pt-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.pt-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.pt-name {
  font-weight: 700;
}
.pt-row b {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.pt-rise {
  margin-top: 4px;
  color: #a86b00;
  font-weight: 600;
}
.pt-changes {
  list-style: none;
  margin: 6px 0 0;
  padding: 6px 0 0;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}
.pt-changes li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  line-height: 1.6;
  color: #4a5361;
}
.pt-changes .up {
  color: #a86b00;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.pt-changes .down {
  color: #c0392b;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.pt-changes .more {
  color: #8891a0;
}
.pt-caption {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  color: #8891a0;
  font-size: 11px;
}
</style>
