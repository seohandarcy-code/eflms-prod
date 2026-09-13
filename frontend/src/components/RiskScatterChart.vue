<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import Plotly from "plotly.js-gl3d-dist-min";
import type { Data, Layout, PlotlyHTMLElement } from "plotly.js";
import type { EquipmentSummary } from "../types/equipment";

const props = defineProps<{ equipmentList: EquipmentSummary[]; selectedId: number | null }>();
const emit = defineEmits<{ select: [equipmentId: number]; hover: [equipmentId: number | null] }>();

const THRESHOLDS = { pof: 20, cof: 30, dof: 20 };
const CARD_WIDTH = 192;
const CARD_HEIGHT = 128;

const plotEl = ref<HTMLDivElement | null>(null);
const hovering = ref(false);
const hoveredItem = ref<EquipmentSummary | null>(null);
const cursorPos = ref({ x: 0, y: 0 });
let gd: PlotlyHTMLElement | null = null;

// 정상 범위(점검불필요 기준: PoF>=20, CoF>=30, DoF>=20)에 해당하는 직육면체.
// 면을 채우지 않고 모서리 와이어프레임만 항상 표시한다 — 채운 반투명 박스는
// 점 위에 표면이 겹쳐 클릭 피킹을 방해하는 느낌이 있어(2단계 검증 후 피드백),
// 면이 없는 와이어프레임은 그 표면 자체가 없어 호버 토글 없이도 항상 안전하다.
const NORMAL_RANGE = { xMin: 20, xMax: 100, yMin: 30, yMax: 100, zMin: 20, zMax: 100 };

function buildNormalRangeEdges(): Data {
  const { xMin, xMax, yMin, yMax, zMin, zMax } = NORMAL_RANGE;
  const corners = [
    [xMin, yMin, zMin],
    [xMax, yMin, zMin],
    [xMax, yMax, zMin],
    [xMin, yMax, zMin],
    [xMin, yMin, zMax],
    [xMax, yMin, zMax],
    [xMax, yMax, zMax],
    [xMin, yMax, zMax],
  ];
  const edges: [number, number][] = [
    [0, 1], [1, 2], [2, 3], [3, 0],
    [4, 5], [5, 6], [6, 7], [7, 4],
    [0, 4], [1, 5], [2, 6], [3, 7],
  ];
  const x: (number | null)[] = [];
  const y: (number | null)[] = [];
  const z: (number | null)[] = [];
  for (const [a, b] of edges) {
    x.push(corners[a][0], corners[b][0], null);
    y.push(corners[a][1], corners[b][1], null);
    z.push(corners[a][2], corners[b][2], null);
  }
  return {
    type: "scatter3d",
    mode: "lines",
    x,
    y,
    z,
    line: { color: "#1B8A5A", width: 3 },
    hoverinfo: "skip",
    showlegend: false,
  } as Data;
}

interface SpotlightAxis {
  key: "pof" | "cof" | "dof";
  label: string;
  value: number;
  threshold: number;
}

// 미달 축이 여럿이면 기준값과의 차이(deficit)가 가장 큰 축 하나만 스포트라이트로 고른다.
function findSpotlightAxis(item: EquipmentSummary): SpotlightAxis | null {
  const candidates: SpotlightAxis[] = [];
  if (item.pof < THRESHOLDS.pof) candidates.push({ key: "pof", label: "PoF", value: item.pof, threshold: THRESHOLDS.pof });
  if (item.cof < THRESHOLDS.cof) candidates.push({ key: "cof", label: "CoF", value: item.cof, threshold: THRESHOLDS.cof });
  if (item.dof < THRESHOLDS.dof) candidates.push({ key: "dof", label: "DoF", value: item.dof, threshold: THRESHOLDS.dof });
  if (candidates.length === 0) return null;
  return candidates.reduce((worst, cur) => (cur.threshold - cur.value > worst.threshold - worst.value ? cur : worst));
}

const spotlight = computed(() => (hoveredItem.value ? findSpotlightAxis(hoveredItem.value) : null));

const otherAxes = computed(() => {
  if (!hoveredItem.value) return [];
  const item = hoveredItem.value;
  const all: SpotlightAxis[] = [
    { key: "pof", label: "PoF", value: item.pof, threshold: THRESHOLDS.pof },
    { key: "cof", label: "CoF", value: item.cof, threshold: THRESHOLDS.cof },
    { key: "dof", label: "DoF", value: item.dof, threshold: THRESHOLDS.dof },
  ];
  return spotlight.value ? all.filter((a) => a.key !== spotlight.value!.key) : all;
});

const cardStyle = computed(() => {
  const width = plotEl.value?.clientWidth ?? 0;
  const height = plotEl.value?.clientHeight ?? 0;
  const maxLeft = Math.max(width - CARD_WIDTH - 4, 4);
  const maxTop = Math.max(height - CARD_HEIGHT - 4, 4);
  const left = Math.min(Math.max(cursorPos.value.x + 16, 4), maxLeft);
  const top = Math.min(Math.max(cursorPos.value.y + 16, 4), maxTop);
  return { left: `${left}px`, top: `${top}px` };
});

function buildTrace(list: EquipmentSummary[], selectedId: number | null): Data[] {
  const selectedIndex = selectedId === null ? -1 : list.findIndex((item) => item.equipment_id === selectedId);

  const trace: Record<string, unknown> = {
    type: "scatter3d",
    mode: "markers",
    x: list.map((item) => item.pof),
    y: list.map((item) => item.cof),
    z: list.map((item) => item.dof),
    text: list.map((item) => item.transformer_name),
    customdata: list.map((item) => item.equipment_id),
    // 네이티브 호버 라벨은 쓰지 않는다 — 커스텀 오버레이 카드로 완전히 대체한다.
    // (Plotly의 loneHover/hovertemplateString 렌더링 경로 자체를 타지 않게 됨)
    hoverinfo: "none",
    marker: {
      size: list.map((item) => (item.needs_inspection ? 9 : 7)),
      color: list.map((item) => (item.needs_inspection ? "#C4392B" : "#3E8E8E")),
      line: { color: "#fff", width: 1 },
    },
  };

  if (selectedIndex >= 0) {
    trace.selectedpoints = [selectedIndex];
    trace.selected = { marker: { size: 16, color: "#0F8A8A", opacity: 1 } };
    trace.unselected = { marker: { opacity: 0.35 } };
  }

  return [buildNormalRangeEdges(), trace as Data];
}

const layout: Partial<Layout> = {
  autosize: true,
  margin: { l: 0, r: 0, t: 10, b: 0 },
  paper_bgcolor: "rgba(0,0,0,0)",
  scene: {
    aspectmode: "cube",
    xaxis: { title: { text: "PoF" }, range: [0, 100], backgroundcolor: "#F4F5F7", gridcolor: "#E2E5EA", zerolinecolor: "#C7CCD3" },
    yaxis: { title: { text: "CoF" }, range: [0, 100], backgroundcolor: "#F4F5F7", gridcolor: "#E2E5EA", zerolinecolor: "#C7CCD3" },
    zaxis: { title: { text: "DoF" }, range: [0, 100], backgroundcolor: "#F4F5F7", gridcolor: "#E2E5EA", zerolinecolor: "#C7CCD3" },
    camera: { eye: { x: 1.4, y: -1.4, z: 1.0 } },
  },
};

const config = { displayModeBar: false, responsive: true };

function onContainerMouseMove(event: MouseEvent) {
  if (!plotEl.value) return;
  const rect = plotEl.value.getBoundingClientRect();
  cursorPos.value = { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

onMounted(async () => {
  if (!plotEl.value) return;
  plotEl.value.addEventListener("mousemove", onContainerMouseMove);

  gd = await Plotly.newPlot(plotEl.value, buildTrace(props.equipmentList, props.selectedId), layout, config);
  gd.on("plotly_click", (event) => {
    const id = event.points?.[0]?.customdata;
    if (typeof id === "number") emit("select", id);
  });
  gd.on("plotly_hover", (event) => {
    hovering.value = true;
    const id = event.points?.[0]?.customdata;
    const resolvedId = typeof id === "number" ? id : null;
    hoveredItem.value = resolvedId !== null ? (props.equipmentList.find((item) => item.equipment_id === resolvedId) ?? null) : null;
    emit("hover", resolvedId);
  });
  gd.on("plotly_unhover", () => {
    hovering.value = false;
    hoveredItem.value = null;
    emit("hover", null);
  });
});

watch(
  [() => props.equipmentList, () => props.selectedId],
  ([list, selectedId]) => {
    if (gd) {
      hoveredItem.value = null;
      Plotly.react(gd, buildTrace(list, selectedId), layout, config);
    }
  },
);

onUnmounted(() => {
  plotEl.value?.removeEventListener("mousemove", onContainerMouseMove);
  if (gd) {
    gd.removeAllListeners("plotly_click");
    gd.removeAllListeners("plotly_hover");
    gd.removeAllListeners("plotly_unhover");
    Plotly.purge(gd);
  }
});

const healthyCount = computed(() => props.equipmentList.filter((item) => !item.needs_inspection).length);
const flaggedCount = computed(() => props.equipmentList.filter((item) => item.needs_inspection).length);
</script>

<template>
  <div>
    <div class="chart-wrap">
      <div ref="plotEl" :style="{ width: '100%', height: '480px', cursor: hovering ? 'pointer' : 'default' }"></div>

      <div v-if="hoveredItem" class="hover-card" :class="{ fail: !!spotlight }" :style="cardStyle">
        <div class="hc-head">
          <span class="hc-dot" :style="{ background: hoveredItem.needs_inspection ? '#C4392B' : '#3E8E8E' }"></span>
          <span class="hc-name">{{ hoveredItem.transformer_name }}</span>
          <span class="hc-score">{{ hoveredItem.total_score.toFixed(1) }}점</span>
        </div>

        <template v-if="spotlight">
          <div class="hc-spotlight">
            <div class="hc-big">{{ spotlight.label }} {{ spotlight.value }}</div>
            <div class="hc-sub">기준 {{ spotlight.threshold }} 미달 · {{ spotlight.value - spotlight.threshold }}</div>
          </div>
          <div class="hc-others">{{ otherAxes.map((a) => `${a.label} ${a.value}`).join(" · ") }}</div>
        </template>
        <template v-else>
          <div class="hc-spotlight ok">
            <div class="hc-big ok">정상 범위</div>
          </div>
          <div class="hc-others">{{ otherAxes.map((a) => `${a.label} ${a.value}`).join(" · ") }}</div>
        </template>
      </div>
    </div>

    <div style="font-size: 11px; color: #8891a0; padding: 0 8px 6px">
      ● 정상 {{ healthyCount }}대&nbsp;&nbsp;● 점검필요 {{ flaggedCount }}대 · 드래그로 회전 · 스크롤로 확대/축소 · 점 클릭 시 설비 선택 · 초록 테두리 = 정상 범위(PoF≥20·CoF≥30·DoF≥20)
    </div>
  </div>
</template>

<style scoped>
.chart-wrap {
  position: relative;
}
.hover-card {
  position: absolute;
  width: 192px;
  background: #e4f3ea;
  border: 1px solid #1b8a5a;
  border-radius: 9px;
  padding: 11px 14px;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.14);
  pointer-events: none;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
}
.hover-card.fail {
  background: #fbe7e4;
  border-color: #c4392b;
}
.hc-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #4a5361;
  margin-bottom: 8px;
}
.hover-card.fail .hc-head {
  color: #8a3327;
}
.hc-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: 0 0 auto;
}
.hc-name {
  font-weight: 700;
  color: #1a2230;
}
.hc-score {
  margin-left: auto;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.hc-spotlight {
  margin-bottom: 8px;
}
.hc-big {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 22px;
  font-weight: 700;
  color: #c4392b;
  line-height: 1;
}
.hc-big.ok {
  font-size: 16px;
  color: #1b8a5a;
}
.hc-sub {
  font-size: 10.5px;
  color: #8a3327;
  margin-top: 3px;
}
.hc-others {
  font-size: 10.5px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  color: #4a5361;
  opacity: 0.85;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  padding-top: 6px;
}
</style>
