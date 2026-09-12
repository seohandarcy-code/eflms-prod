<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import Plotly from "plotly.js-gl3d-dist-min";
import type { Data, Layout, PlotlyHTMLElement } from "plotly.js";
import type { EquipmentSummary } from "../types/equipment";

const props = defineProps<{ equipmentList: EquipmentSummary[]; selectedId: number | null }>();
const emit = defineEmits<{ select: [equipmentId: number] }>();

const plotEl = ref<HTMLDivElement | null>(null);
let gd: PlotlyHTMLElement | null = null;

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
    hovertemplate: "<b>%{text}</b><br>PoF %{x}<br>CoF %{y}<br>DoF %{z}<extra></extra>",
    marker: {
      size: list.map((item) => (item.needs_inspection ? 7 : 5)),
      color: list.map((item) => (item.needs_inspection ? "#C4392B" : "#3E8E8E")),
    },
  };

  if (selectedIndex >= 0) {
    trace.selectedpoints = [selectedIndex];
    trace.selected = { marker: { size: 13, color: "#0F8A8A", opacity: 1 } };
    trace.unselected = { marker: { opacity: 0.35 } };
  }

  return [trace as Data];
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
    const id = event.points?.[0]?.customdata;
    if (typeof id === "number") emit("select", id);
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
    Plotly.purge(gd);
  }
});

const healthyCount = computed(() => props.equipmentList.filter((item) => !item.needs_inspection).length);
const flaggedCount = computed(() => props.equipmentList.filter((item) => item.needs_inspection).length);
</script>

<template>
  <div>
    <div ref="plotEl" style="width: 100%; height: 480px"></div>
    <div style="font-size: 11px; color: #8891a0; padding: 0 8px 6px">
      ● 정상 {{ healthyCount }}대&nbsp;&nbsp;● 점검필요 {{ flaggedCount }}대 · 드래그로 회전 · 스크롤로 확대/축소 · 점 클릭 시 설비 선택
    </div>
  </div>
</template>
