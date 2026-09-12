<script setup lang="ts">
import { computed } from "vue";
import type { EquipmentSummary } from "../types/equipment";
import { axisEndPoint, projectScorePoint } from "../utils/scoreBreakdown";

const props = defineProps<{ equipmentList: EquipmentSummary[] }>();

const pofAxis = axisEndPoint("pof");
const cofAxis = axisEndPoint("cof");
const dofAxis = axisEndPoint("dof");
const pofTick = axisEndPoint("pof", 20);
const cofTick = axisEndPoint("cof", 30);
const dofTick = axisEndPoint("dof", 20);
const origin = axisEndPoint("pof", 0);

const points = computed(() =>
  props.equipmentList.map((item) => ({
    ...projectScorePoint(item.pof, item.cof, item.dof),
    item,
  })),
);

const healthyCount = computed(() => props.equipmentList.filter((item) => !item.needs_inspection).length);
const flaggedCount = computed(() => props.equipmentList.filter((item) => item.needs_inspection).length);
</script>

<template>
  <div>
    <svg style="width: 100%; height: auto; max-height: 480px; display: block" viewBox="0 0 560 300">
      <line :x1="origin.x" :y1="origin.y" :x2="pofAxis.x" :y2="pofAxis.y" stroke="#C7CCD3" stroke-width="1.4" />
      <line :x1="origin.x" :y1="origin.y" :x2="cofAxis.x" :y2="cofAxis.y" stroke="#C7CCD3" stroke-width="1.4" />
      <line :x1="origin.x" :y1="origin.y" :x2="dofAxis.x" :y2="dofAxis.y" stroke="#C7CCD3" stroke-width="1.4" />

      <circle :cx="pofTick.x" :cy="pofTick.y" r="2.6" fill="#C4392B" />
      <text :x="pofTick.x + 6" :y="pofTick.y + 4" font-family="IBM Plex Mono" font-size="10" fill="#B23124">20</text>
      <circle :cx="cofTick.x" :cy="cofTick.y" r="2.6" fill="#C4392B" />
      <text :x="cofTick.x - 25" :y="cofTick.y + 4" font-family="IBM Plex Mono" font-size="10" fill="#B23124">30</text>
      <circle :cx="dofTick.x" :cy="dofTick.y" r="2.6" fill="#C4392B" />
      <text :x="dofTick.x + 6" :y="dofTick.y + 3" font-family="IBM Plex Mono" font-size="10" fill="#B23124">20</text>

      <text :x="pofAxis.x + 8" :y="pofAxis.y + 6" font-family="IBM Plex Sans" font-size="12" font-weight="600" fill="#5B6472">PoF</text>
      <text :x="cofAxis.x - 30" :y="cofAxis.y + 6" font-family="IBM Plex Sans" font-size="12" font-weight="600" fill="#5B6472">CoF</text>
      <text :x="dofAxis.x - 14" :y="dofAxis.y - 8" font-family="IBM Plex Sans" font-size="12" font-weight="600" fill="#5B6472">DoF</text>

      <g v-for="p in points" :key="p.item.equipment_id">
        <circle
          :cx="p.x"
          :cy="p.y"
          :r="p.item.needs_inspection ? 7.5 : 5"
          :fill="p.item.needs_inspection ? '#C4392B' : '#3E8E8E'"
          :stroke="p.item.needs_inspection ? '#fff' : 'none'"
          stroke-width="1.5"
        >
          <title>{{ p.item.transformer_name }} · PoF {{ p.item.pof }} · CoF {{ p.item.cof }} · DoF {{ p.item.dof }}</title>
        </circle>
      </g>
    </svg>
    <div style="font-size: 11px; color: #8891a0; padding: 0 8px 6px">
      ● 정상 {{ healthyCount }}대&nbsp;&nbsp;● 점검필요 {{ flaggedCount }}대 · 붉은 점 = 기준 미달 축 보유 설비
    </div>
  </div>
</template>
