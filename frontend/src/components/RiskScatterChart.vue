<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import Plotly from "plotly.js-gl3d-dist-min";
import type { Data, Layout } from "plotly.js";
import type { EquipmentSummary } from "../types/equipment";

const props = defineProps<{ equipmentList: EquipmentSummary[] }>();

const plotEl = ref<HTMLDivElement | null>(null);

function buildTrace(list: EquipmentSummary[]): Data[] {
  return [
    {
      type: "scatter3d",
      mode: "markers",
      x: list.map((item) => item.pof),
      y: list.map((item) => item.cof),
      z: list.map((item) => item.dof),
      text: list.map((item) => item.transformer_name),
      hovertemplate: "<b>%{text}</b><br>PoF %{x}<br>CoF %{y}<br>DoF %{z}<extra></extra>",
      marker: {
        size: list.map((item) => (item.needs_inspection ? 7 : 5)),
        color: list.map((item) => (item.needs_inspection ? "#C4392B" : "#3E8E8E")),
      },
    },
  ];
}

const layout: Partial<Layout> = {
  autosize: true,
  margin: { l: 0, r: 0, t: 10, b: 0 },
  paper_bgcolor: "rgba(0,0,0,0)",
  scene: {
    xaxis: { title: { text: "PoF" }, range: [0, 100], backgroundcolor: "#F4F5F7", gridcolor: "#E2E5EA", zerolinecolor: "#C7CCD3" },
    yaxis: { title: { text: "CoF" }, range: [0, 100], backgroundcolor: "#F4F5F7", gridcolor: "#E2E5EA", zerolinecolor: "#C7CCD3" },
    zaxis: { title: { text: "DoF" }, range: [0, 100], backgroundcolor: "#F4F5F7", gridcolor: "#E2E5EA", zerolinecolor: "#C7CCD3" },
    camera: { eye: { x: 1.4, y: -1.4, z: 1.0 } },
  },
};

const config = { displayModeBar: false, responsive: true };

onMounted(() => {
  if (plotEl.value) {
    Plotly.newPlot(plotEl.value, buildTrace(props.equipmentList), layout, config);
  }
});

watch(
  () => props.equipmentList,
  (list) => {
    if (plotEl.value) {
      Plotly.react(plotEl.value, buildTrace(list), layout, config);
    }
  },
);

onUnmounted(() => {
  if (plotEl.value) {
    Plotly.purge(plotEl.value);
  }
});

const healthyCount = computed(() => props.equipmentList.filter((item) => !item.needs_inspection).length);
const flaggedCount = computed(() => props.equipmentList.filter((item) => item.needs_inspection).length);
</script>

<template>
  <div>
    <div ref="plotEl" style="width: 100%; height: 480px"></div>
    <div style="font-size: 11px; color: #8891a0; padding: 0 8px 6px">
      ● 정상 {{ healthyCount }}대&nbsp;&nbsp;● 점검필요 {{ flaggedCount }}대 · 드래그로 회전 · 스크롤로 확대/축소
    </div>
  </div>
</template>
