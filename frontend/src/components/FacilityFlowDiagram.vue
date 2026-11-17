<script setup lang="ts">
import { computed } from "vue";
import { FACILITY_INFO, facilityAnchor, type FacilityCount } from "../utils/facilityInfo";

// 설비 안내 페이지의 전력설비 계통도(Stage 17). 지금 등록된 7개 유형에 맞춘 고정 배치이고,
// 칸마다 사진과 현재 대수·점검필요를 보여준다. 칸을 누르면 아래 상세 설명(#ef3 등)으로 이동한다.
// 새 유형은 표·상세 카드에는 자동으로 나오지만 계통도에 넣으려면 NODES 배치를 손봐야 한다.
const props = defineProps<{
  counts: Record<string, FacilityCount>;
  typeNames: Record<string, string>;
}>();

const W = 1040;
const H = 640;
const NODE_W = 140;
const NODE_H = 150;

const NODES: { code: string; x: number; y: number }[] = [
  { code: "EF3", x: 236, y: 55 },
  { code: "EF2", x: 448, y: 55 },
  { code: "EF1", x: 660, y: 55 },
  { code: "EF4", x: 872, y: 55 },
  { code: "EF7", x: 24, y: 340 },
  { code: "EF5", x: 236, y: 340 },
  { code: "EF6", x: 552, y: 340 },
];

const nodes = computed(() =>
  NODES.map((node) => ({
    ...node,
    name: props.typeNames[node.code] ?? node.code,
    image: FACILITY_INFO[node.code]?.image ?? null,
    count: props.counts[node.code] ?? null,
    to: { path: "/guide/facilities", hash: `#${facilityAnchor(node.code)}` },
  })),
);

const box = (x: number, y: number, w = NODE_W, h = NODE_H) => ({ left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${h}px` });
</script>

<template>
  <div class="flow-scroll">
    <div class="flow" :style="{ width: `${W}px`, height: `${H}px` }">
      <svg class="flow-lines" :width="W" :height="H" :viewBox="`0 0 ${W} ${H}`" aria-hidden="true">
        <defs>
          <marker id="flow-head" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 L8 4 L0 8 Z" fill="#0f8a8a" />
          </marker>
          <marker id="flow-head-grey" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 L8 4 L0 8 Z" fill="#6b7482" />
          </marker>
          <marker id="flow-head-backup" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 L8 4 L0 8 Z" fill="#a8590a" />
          </marker>
        </defs>
        <!-- 154kV 수전 → 변압기 → 수배전반 -->
        <path d="M164 130 H234" class="line grey" marker-end="url(#flow-head-grey)" />
        <path d="M376 130 H446" class="line" marker-end="url(#flow-head)" />
        <path d="M588 130 H658" class="line" marker-end="url(#flow-head)" />
        <path d="M800 130 H870" class="line" marker-end="url(#flow-head)" />
        <!-- 수배전반 → 저압 배전 모선 → UPS · VDP · 일반 배전 -->
        <path d="M942 205 V268 H306" class="line" />
        <path d="M306 268 V338" class="line" marker-end="url(#flow-head)" />
        <path d="M622 268 V338" class="line" marker-end="url(#flow-head)" />
        <path d="M942 268 V338" class="line" marker-end="url(#flow-head)" />
        <!-- 배터리 → UPS (정전 때 백업) -->
        <path d="M164 415 H234" class="line backup" marker-end="url(#flow-head-backup)" />
        <!-- → 반도체 Fab 생산설비 -->
        <path d="M306 490 V550" class="line" marker-end="url(#flow-head)" />
        <path d="M622 490 V550" class="line" marker-end="url(#flow-head)" />
        <path d="M942 490 V550" class="line" marker-end="url(#flow-head)" />
      </svg>

      <div class="label" :style="{ left: '172px', top: '106px' }">154kV</div>
      <div class="label" :style="{ left: '384px', top: '106px' }">154kV</div>
      <div class="label" :style="{ left: '596px', top: '106px' }">154kV</div>
      <div class="label" :style="{ left: '808px', top: '106px' }">22.9kV</div>
      <div class="label backup" :style="{ left: '172px', top: '391px' }">백업</div>
      <div class="label wide" :style="{ left: '520px', top: '244px' }">저압 배전 (380 / 220V)</div>

      <div class="node external" :style="box(24, 55)">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#4a5361" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 2 L7 22 M12 2 L17 22 M8.5 16 L15.5 16 M9.8 10 L14.2 10 M4 6 L20 6" />
        </svg>
        <span class="node-text"><b>한전 변전소</b><span class="node-sub">154kV 송전</span></span>
      </div>

      <RouterLink v-for="node in nodes" :key="node.code" :to="node.to" class="node" :style="box(node.x, node.y)">
        <img v-if="node.image" :src="node.image" alt="" class="node-img" />
        <span class="node-text">
          <b>{{ node.name }}</b>
          <span class="node-sub">{{ node.code }}<template v-if="node.count"> · {{ node.count.total }}대</template></span>
          <span v-if="node.count" :class="['node-check', node.count.needsInspection > 0 ? 'warn' : 'ok']">점검필요 {{ node.count.needsInspection }}</span>
        </span>
      </RouterLink>

      <div class="node external" :style="box(872, 340)">
        <span class="node-text"><b>일반 배전</b><span class="node-sub">공조·용수·조명 등<br />(평가 대상 아님)</span></span>
      </div>

      <div class="fab" :style="box(236, 552, 776, 72)">
        <b>반도체 Fab 생산설비</b>
        <span class="fab-sub">· 노광·식각·증착 장비, 클린룸 공조, 초순수 등</span>
      </div>

      <div class="legend" :style="{ left: '24px', top: '578px' }">전력이 흐르는 방향 →</div>
    </div>
  </div>
</template>

<style scoped>
.flow-scroll {
  overflow-x: auto;
}
.flow {
  position: relative;
  margin: 0 auto;
}
.flow-lines {
  position: absolute;
  inset: 0;
}
.line {
  fill: none;
  stroke: #0f8a8a;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.line.grey {
  stroke: #6b7482;
}
.line.backup {
  stroke: #a8590a;
  stroke-dasharray: 6 6;
}
.label {
  position: absolute;
  width: 56px;
  text-align: center;
  font-size: 12px;
  line-height: 16px;
  font-weight: 600;
  color: #4a5361;
}
.label.backup {
  color: #a8590a;
}
.label.wide {
  width: 200px;
  background: #fff;
  font-weight: 500;
}
.node {
  position: absolute;
  padding: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  text-align: center;
  background: #fff;
  border: 1px solid #0f8a8a;
  border-radius: 10px;
  font-size: 13px;
  color: #1a2230;
  text-decoration: none;
}
a.node:hover,
a.node:focus-visible {
  box-shadow: 0 0 0 3px rgba(15, 138, 138, 0.18);
}
.node.external {
  background: #f4f5f7;
  border: 1px dashed #b4bac4;
}
.node-img {
  width: 96px;
  height: 70px;
  object-fit: contain;
  border-radius: 6px;
  background: #f3f5fb;
}
.node-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.node-sub {
  font-size: 11px;
  color: #6b7482;
}
.node-check {
  font-size: 11px;
  font-weight: 600;
}
.node-check.warn {
  color: #a8590a;
}
.node-check.ok {
  color: #0b6f6f;
}
.fab {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #1a2230;
  color: #fff;
  border-radius: 10px;
  font-size: 14px;
}
.fab-sub {
  color: #c9ced6;
  font-size: 12px;
}
.legend {
  position: absolute;
  font-size: 12px;
  color: #6b7482;
}
</style>
