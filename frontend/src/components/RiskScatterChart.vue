<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import Plotly from "plotly.js-gl3d-dist-min";
import type { Data, Layout, PlotlyHTMLElement } from "plotly.js";
import type { EquipmentStatus, EquipmentSummary } from "../types/equipment";
import { statusColor, statusLabel } from "../utils/statusStyle";

const props = defineProps<{ equipmentList: EquipmentSummary[]; selectedId: number | null }>();
const emit = defineEmits<{ select: [equipmentId: number]; hover: [equipmentId: number | null] }>();

const CARD_WIDTH = 192;
const CARD_HEIGHT = 92;

const plotEl = ref<HTMLDivElement | null>(null);
const hovering = ref(false);
const hoveredItem = ref<EquipmentSummary | null>(null);
const cursorPos = ref({ x: 0, y: 0 });
let gd: PlotlyHTMLElement | null = null;

interface Box {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
  zMin: number;
  zMax: number;
}

// 3단계 판정 경계(docs 참고: backend app/services/equipment_service.py의 classify_status와 반드시 일치시킨다).
// x=POF, y=COF, z=DOF.
// COF·DOF가 둘 다 60 초과인 "구석"에서는 기준선이 완화되기 때문에, 경계는 큰 상자(POF가 그 값보다
// 크면 항상 통과) + 그 구석에 붙은 작은 상자(완화된 구간)로 이루어진 계단형 입체가 된다.
const NORMAL_BIG: Box = { xMin: 60, xMax: 100, yMin: 0, yMax: 100, zMin: 0, zMax: 100 };
const NORMAL_NOTCH: Box = { xMin: 50, xMax: 60, yMin: 60, yMax: 100, zMin: 60, zMax: 100 };
const REVIEW_BIG: Box = { xMin: 40, xMax: 100, yMin: 0, yMax: 100, zMin: 0, zMax: 100 };
const REVIEW_NOTCH: Box = { xMin: 30, xMax: 40, yMin: 60, yMax: 100, zMin: 60, zMax: 100 };

type Pt = [number, number, number];

function faceEdges(points: Pt[]): [Pt, Pt][] {
  return points.map((p, i) => [p, points[(i + 1) % points.length]]);
}

function edgeKey(a: Pt, b: Pt): string {
  const [p, q] = [a, b].sort((u, v) => u[0] - v[0] || u[1] - v[1] || u[2] - v[2]);
  return `${p.join(",")}|${q.join(",")}`;
}

// big 상자와, big의 xMin 면 한쪽 구석(notch.yMin~big.yMax, notch.zMin~big.zMax)에 flush로 붙은
// notch 상자의 "합쳐진 입체"의 진짜 바깥 테두리만 그린다. 맞닿는 면은 내부로 사라지므로 중복선이
// 생기지 않는다 — 9개 면(맞닿아 없어지는 면 1개 제외)의 모서리를 모아 겹치는 선을 한 번만 남긴다.
// `drawnKeys`를 여러 와이어프레임 호출에 공유하면, 먼저 그린 경계(예: 정상)와 좌표가 완전히 같은
// 선(예: 두 경계가 똑같이 맞닿는 가장 먼 벽면)은 나중 경계(예: 교체검토)에서 건너뛰어 중복을 없앤다.
function buildNotchedBoxEdges(big: Box, notch: Box, color: string, drawnKeys: Set<string>): Data {
  const { xMin: X1, xMax: X2, yMin: Y0, yMax: Y1, zMin: Z0, zMax: Z1 } = big;
  const NX = notch.xMin;
  const NY = notch.yMin;
  const NZ = notch.zMin;

  const faces: Pt[][] = [
    [[X2, Y0, Z0], [X2, Y1, Z0], [X2, Y1, Z1], [X2, Y0, Z1]], // X = X2 (그대로)
    [[X1, Y0, Z0], [X2, Y0, Z0], [X2, Y0, Z1], [X1, Y0, Z1]], // Y = Y0 (그대로)
    [[X1, Y0, Z0], [X2, Y0, Z0], [X2, Y1, Z0], [X1, Y1, Z0]], // Z = Z0 (그대로)
    [[X1, Y0, Z0], [X1, Y1, Z0], [X1, Y1, NZ], [X1, NY, NZ], [X1, NY, Z1], [X1, Y0, Z1]], // X = X1, 구석이 파임
    [[X2, Y1, Z0], [X2, Y1, Z1], [NX, Y1, Z1], [NX, Y1, NZ], [X1, Y1, NZ], [X1, Y1, Z0]], // Y = Y1, notch만큼 확장
    [[X2, Y0, Z1], [X2, Y1, Z1], [NX, Y1, Z1], [NX, NY, Z1], [X1, NY, Z1], [X1, Y0, Z1]], // Z = Z1, notch만큼 확장
    [[NX, NY, NZ], [NX, Y1, NZ], [NX, Y1, Z1], [NX, NY, Z1]], // notch 바깥 캡 X = NX
    [[NX, NY, NZ], [X1, NY, NZ], [X1, NY, Z1], [NX, NY, Z1]], // notch 밑면 Y = NY
    [[NX, NY, NZ], [X1, NY, NZ], [X1, Y1, NZ], [NX, Y1, NZ]], // notch 밑면 Z = NZ
  ];

  const dedup = new Map<string, [Pt, Pt]>();
  for (const face of faces) {
    for (const [a, b] of faceEdges(face)) dedup.set(edgeKey(a, b), [a, b]);
  }

  const x: (number | null)[] = [];
  const y: (number | null)[] = [];
  const z: (number | null)[] = [];
  for (const [key, [a, b]] of dedup) {
    if (drawnKeys.has(key)) continue;
    drawnKeys.add(key);
    x.push(a[0], b[0], null);
    y.push(a[1], b[1], null);
    z.push(a[2], b[2], null);
  }
  return {
    type: "scatter3d",
    mode: "lines",
    x,
    y,
    z,
    line: { color, width: 3 },
    hoverinfo: "skip",
    showlegend: false,
  } as Data;
}

const cardStyle = computed(() => {
  const width = plotEl.value?.clientWidth ?? 0;
  const height = plotEl.value?.clientHeight ?? 0;
  const maxLeft = Math.max(width - CARD_WIDTH - 4, 4);
  const maxTop = Math.max(height - CARD_HEIGHT - 4, 4);
  const left = Math.min(Math.max(cursorPos.value.x + 16, 4), maxLeft);
  const top = Math.min(Math.max(cursorPos.value.y + 16, 4), maxTop);
  const color = hoveredItem.value ? statusColor(hoveredItem.value.status) : "#1a2230";
  return { left: `${left}px`, top: `${top}px`, borderColor: color };
});

// 정상/교체검토/즉시교체 설비를 별도 trace로 그려, 범례에서 각각 독립적으로 켜고 끌 수 있게 한다.
function buildMarkerTrace(
  groupList: EquipmentSummary[],
  name: string,
  color: string,
  size: number,
  selectedId: number | null,
  selectionExists: boolean,
): Data {
  const selectedIndex = selectedId === null ? -1 : groupList.findIndex((item) => item.equipment_id === selectedId);

  const trace: Record<string, unknown> = {
    type: "scatter3d",
    mode: "markers",
    name,
    showlegend: true,
    x: groupList.map((item) => item.pof),
    y: groupList.map((item) => item.cof),
    z: groupList.map((item) => item.dof),
    text: groupList.map((item) => item.transformer_name),
    customdata: groupList.map((item) => item.equipment_id),
    // 네이티브 호버 라벨은 쓰지 않는다 — 커스텀 오버레이 카드로 완전히 대체한다.
    // (Plotly의 loneHover/hovertemplateString 렌더링 경로 자체를 타지 않게 됨)
    hoverinfo: "none",
    marker: {
      // Plotly gl3d는 marker.size가 스칼라일 때와 배열일 때 크기 산정 방식이 달라
      // 눈에 띄게 다르게 보인다. 분리 전(단일 trace, 배열 크기)과 동일하게 보이도록
      // 그룹 내 모든 점에 같은 값을 반복한 배열로 넘긴다.
      size: groupList.map(() => size),
      color,
      line: { color: "#fff", width: 1 },
    },
  };

  // 선택된 설비가 (어느 trace든) 실제로 존재할 때만 강조/흐림을 적용한다.
  // 이 그룹에 없으면 selectedpoints:[]가 되어 이 trace 전체가 흐려진다.
  if (selectionExists) {
    trace.selectedpoints = selectedIndex >= 0 ? [selectedIndex] : [];
    trace.selected = { marker: { size: 16, color: "#0F8A8A", opacity: 1 } };
    trace.unselected = { marker: { opacity: 0.35 } };
  }

  return trace as Data;
}

function groupByStatus(list: EquipmentSummary[], status: EquipmentStatus): EquipmentSummary[] {
  return list.filter((item) => item.status === status);
}

function buildTrace(list: EquipmentSummary[], selectedId: number | null): Data[] {
  const normalList = groupByStatus(list, "normal");
  const reviewList = groupByStatus(list, "review");
  const replaceList = groupByStatus(list, "replace");
  const selectionExists = selectedId !== null && list.some((item) => item.equipment_id === selectedId);

  const drawnEdgeKeys = new Set<string>();

  return [
    buildNotchedBoxEdges(NORMAL_BIG, NORMAL_NOTCH, statusColor("normal"), drawnEdgeKeys),
    buildNotchedBoxEdges(REVIEW_BIG, REVIEW_NOTCH, statusColor("review"), drawnEdgeKeys),
    buildMarkerTrace(normalList, `정상 설비 : ${normalList.length} 건`, statusColor("normal"), 7, selectedId, selectionExists),
    buildMarkerTrace(reviewList, `교체검토 설비 : ${reviewList.length} 건`, statusColor("review"), 8, selectedId, selectionExists),
    buildMarkerTrace(replaceList, `즉시교체 설비 : ${replaceList.length} 건`, statusColor("replace"), 9, selectedId, selectionExists),
  ];
}

const layout: Partial<Layout> = {
  autosize: true,
  margin: { l: 0, r: 0, t: 10, b: 0 },
  paper_bgcolor: "rgba(0,0,0,0)",
  scene: {
    aspectmode: "cube",
    xaxis: { title: { text: "POF" }, range: [0, 100], backgroundcolor: "#F4F5F7", gridcolor: "#E2E5EA", zerolinecolor: "#C7CCD3" },
    yaxis: { title: { text: "COF" }, range: [0, 100], backgroundcolor: "#F4F5F7", gridcolor: "#E2E5EA", zerolinecolor: "#C7CCD3" },
    zaxis: { title: { text: "DOF" }, range: [0, 100], backgroundcolor: "#F4F5F7", gridcolor: "#E2E5EA", zerolinecolor: "#C7CCD3" },
    // 원근 투영(perspective)은 스크롤 확대가 카메라를 시선 방향으로 실제로 이동시키는 방식이라
    // 여러 번 스크롤하면 회전이 섞인 것처럼 느껴지는 부작용이 있다. 직교 투영(orthographic)은
    // 확대가 순수한 배율 변경이라 이 문제가 없다.
    // (plotly.js 타입 정의에 projection이 아직 없어 캐스팅— 런타임에는 정식 지원되는 옵션)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    camera: { eye: { x: 1.4, y: -1.4, z: 1.0 }, projection: { type: "orthographic" } } as any,
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
    const item = resolvedId !== null ? (props.equipmentList.find((eq) => eq.equipment_id === resolvedId) ?? null) : null;
    hoveredItem.value = item;
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

const normalCount = computed(() => groupByStatus(props.equipmentList, "normal").length);
const reviewCount = computed(() => groupByStatus(props.equipmentList, "review").length);
const replaceCount = computed(() => groupByStatus(props.equipmentList, "replace").length);
</script>

<template>
  <div>
    <div class="chart-wrap">
      <div ref="plotEl" :style="{ width: '100%', height: '480px', cursor: hovering ? 'pointer' : 'default' }"></div>

      <div v-if="hoveredItem" class="hover-card" :style="cardStyle">
        <div class="hc-head">
          <span class="hc-dot" :style="{ background: statusColor(hoveredItem.status) }"></span>
          <span class="hc-name">{{ hoveredItem.transformer_name }}</span>
          <span class="hc-score">{{ hoveredItem.total_score.toFixed(1) }}점</span>
        </div>
        <div class="hc-status" :style="{ color: statusColor(hoveredItem.status) }">{{ statusLabel(hoveredItem.status) }}</div>
        <div class="hc-axes">POF {{ hoveredItem.pof }} · COF {{ hoveredItem.cof }} · DOF {{ hoveredItem.dof }}</div>
      </div>
    </div>

    <div style="font-size: 11px; color: #8891a0; padding: 0 8px 6px">
      ● 정상 {{ normalCount }}대&nbsp;&nbsp;● 교체검토 {{ reviewCount }}대&nbsp;&nbsp;● 즉시교체 {{ replaceCount }}대 · 드래그로 회전 · 오른쪽 드래그로 이동 · 스크롤로 확대/축소 · 점 클릭 시 설비 선택 · 초록 테두리 = 정상 경계 · 노랑 테두리 = 교체검토 경계(그 안쪽은 즉시교체)
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
  background: #fff;
  border: 1px solid #1a2230;
  border-radius: 9px;
  padding: 11px 14px;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.14);
  pointer-events: none;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
}
.hc-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #4a5361;
  margin-bottom: 6px;
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
.hc-status {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 6px;
}
.hc-axes {
  font-size: 11px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  color: #4a5361;
  opacity: 0.85;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  padding-top: 6px;
}
</style>
