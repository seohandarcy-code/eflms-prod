<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import Plotly from "plotly.js-gl3d-dist-min";
import type { Data, Layout, PlotlyHTMLElement } from "plotly.js";
import type { EquipmentSummary } from "../types/equipment";

const props = defineProps<{ equipmentList: EquipmentSummary[]; selectedId: number | null }>();
const emit = defineEmits<{ select: [equipmentId: number]; hover: [equipmentId: number | null] }>();

// trace 인덱스: 0=정상범위 박스, 1=정상범위 모서리선, 2=축 임계값 투영선, 3=마커
const BOX_TRACE_INDICES = [0, 1];
const PROJECTION_TRACE_INDEX = 2;

const plotEl = ref<HTMLDivElement | null>(null);
const hovering = ref(false);
let gd: PlotlyHTMLElement | null = null;

// 정상 범위(점검불필요 기준: PoF>=20, CoF>=30, DoF>=20)에 해당하는 직육면체
const NORMAL_RANGE = { xMin: 20, xMax: 100, yMin: 30, yMax: 100, zMin: 20, zMax: 100 };

function buildNormalRangeBox(): Data {
  const { xMin, xMax, yMin, yMax, zMin, zMax } = NORMAL_RANGE;
  return {
    type: "mesh3d",
    x: [xMin, xMax, xMax, xMin, xMin, xMax, xMax, xMin],
    y: [yMin, yMin, yMax, yMax, yMin, yMin, yMax, yMax],
    z: [zMin, zMin, zMin, zMin, zMax, zMax, zMax, zMax],
    i: [0, 0, 4, 4, 0, 0, 3, 3, 0, 0, 1, 1],
    j: [1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 2, 6],
    k: [2, 3, 6, 7, 5, 4, 6, 7, 7, 4, 6, 5],
    opacity: 0.1,
    color: "#1B8A5A",
    flatshading: true,
    hoverinfo: "skip",
    showlegend: false,
    visible: false,
  } as unknown as Data;
}

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
    visible: false,
  } as Data;
}

interface ProjectionSegments {
  x: (number | null)[];
  y: (number | null)[];
  z: (number | null)[];
}

// 기준 미달 축마다 "현재 위치 → 그 축만 기준값으로 바꾼 위치"로 향하는 선분을 만든다.
function buildProjectionSegments(pof: number, cof: number, dof: number): ProjectionSegments {
  const segments: [[number, number, number], [number, number, number]][] = [];
  if (pof < NORMAL_RANGE.xMin) segments.push([[pof, cof, dof], [NORMAL_RANGE.xMin, cof, dof]]);
  if (cof < NORMAL_RANGE.yMin) segments.push([[pof, cof, dof], [pof, NORMAL_RANGE.yMin, dof]]);
  if (dof < NORMAL_RANGE.zMin) segments.push([[pof, cof, dof], [pof, cof, NORMAL_RANGE.zMin]]);

  const x: (number | null)[] = [];
  const y: (number | null)[] = [];
  const z: (number | null)[] = [];
  for (const [a, b] of segments) {
    x.push(a[0], b[0], null);
    y.push(a[1], b[1], null);
    z.push(a[2], b[2], null);
  }
  return { x, y, z };
}

function buildProjectionTrace(pof: number, cof: number, dof: number): Data {
  const { x, y, z } = buildProjectionSegments(pof, cof, dof);
  return {
    type: "scatter3d",
    mode: "lines",
    x,
    y,
    z,
    line: { color: "#C4392B", width: 4, dash: "dot" },
    hoverinfo: "skip",
    showlegend: false,
    visible: false,
  } as unknown as Data;
}

function buildEmptyProjectionTrace(): Data {
  // 세 축 모두 기준을 만족하는 값을 넣어 선분이 하나도 생기지 않게 한다.
  return buildProjectionTrace(NORMAL_RANGE.xMax, NORMAL_RANGE.yMax, NORMAL_RANGE.zMax);
}

function buildTrace(list: EquipmentSummary[], selectedId: number | null): Data[] {
  const selectedIndex = selectedId === null ? -1 : list.findIndex((item) => item.equipment_id === selectedId);

  const trace: Record<string, unknown> = {
    type: "scatter3d",
    mode: "markers",
    x: list.map((item) => item.pof),
    y: list.map((item) => item.cof),
    z: list.map((item) => item.dof),
    text: list.map((item) => item.transformer_name),
    customdata: list.map((item) => [item.equipment_id, item.total_score]),
    hovertemplate: "<b>%{text}</b><br>PoF %{x}<br>CoF %{y}<br>DoF %{z}<br>종합점수 %{customdata[1]:.1f}<extra></extra>",
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

  return [buildNormalRangeBox(), buildNormalRangeEdges(), buildEmptyProjectionTrace(), trace as Data];
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

onMounted(async () => {
  if (!plotEl.value) return;
  gd = await Plotly.newPlot(plotEl.value, buildTrace(props.equipmentList, props.selectedId), layout, config);
  gd.on("plotly_click", (event) => {
    const customdata = event.points?.[0]?.customdata as unknown as number[] | undefined;
    const id = customdata?.[0];
    if (typeof id === "number") emit("select", id);
  });
  gd.on("plotly_hover", (event) => {
    hovering.value = true;
    if (!gd) return;

    const point = event.points?.[0] as (typeof event.points)[0] & { z?: number };
    const customdata = point?.customdata as unknown as number[] | undefined;
    const id = customdata?.[0];
    emit("hover", typeof id === "number" ? id : null);

    Plotly.restyle(gd, { visible: true }, BOX_TRACE_INDICES);

    if (point && typeof point.x === "number" && typeof point.y === "number" && typeof point.z === "number") {
      const projection = buildProjectionSegments(point.x, point.y, point.z);
      Plotly.restyle(gd, { x: [projection.x], y: [projection.y], z: [projection.z], visible: true }, [PROJECTION_TRACE_INDEX]);
    }
  });
  gd.on("plotly_unhover", () => {
    hovering.value = false;
    emit("hover", null);
    if (!gd) return;
    Plotly.restyle(gd, { visible: false }, [...BOX_TRACE_INDICES, PROJECTION_TRACE_INDEX]);
  });
});

watch(
  [() => props.equipmentList, () => props.selectedId],
  ([list, selectedId]) => {
    if (gd) {
      Plotly.react(gd, buildTrace(list, selectedId), layout, config);
    }
  },
);

onUnmounted(() => {
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
    <div ref="plotEl" :style="{ width: '100%', height: '480px', cursor: hovering ? 'pointer' : 'default' }"></div>
    <div style="font-size: 11px; color: #8891a0; padding: 0 8px 6px">
      ● 정상 {{ healthyCount }}대&nbsp;&nbsp;● 점검필요 {{ flaggedCount }}대 · 드래그로 회전 · 스크롤로 확대/축소 · 점 클릭 시 설비 선택 · 연한 초록 박스 = 정상 범위(PoF≥20·CoF≥30·DoF≥20)
    </div>
  </div>
</template>
