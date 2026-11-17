<script setup lang="ts">
import { computed } from "vue";
import type { EquipmentSummary } from "../types/equipment";
import FacilityImage from "./FacilityImage.vue";
import { countByType, FACILITY_INFO, facilityAnchor, sortByFlow } from "../utils/facilityInfo";

// 대시보드 왼쪽 "선택한 설비" 카드(Stage 17). 0개 = 안내 문구, 1개 = 사진이 위에 오는 큰 카드,
// 2개 이상 = 작은 사진 2열. 사진은 1개·여러 개 모두 움직이는 사진. 숫자는 지금 목록(사업장 필터 적용 후)으로 세서 위쪽 KPI와 항상 같다.
const props = defineProps<{
  selected: string[];
  items: EquipmentSummary[];
  typeNames: Record<string, string>;
}>();

const GUIDE_PATH = "/guide/facilities";

const counts = computed(() => countByType(props.items));

const cards = computed(() =>
  sortByFlow(props.selected).map((code) => ({
    code,
    name: props.typeNames[code] ?? code,
    info: FACILITY_INFO[code] ?? null,
    total: counts.value[code]?.total ?? 0,
    needsInspection: counts.value[code]?.needsInspection ?? 0,
    to: { path: GUIDE_PATH, hash: `#${facilityAnchor(code)}` },
  })),
);
</script>

<template>
  <div v-if="cards.length === 0" class="sfc-hint">설비유형을 고르면 사진과 간단한 설명이 여기에 나옵니다.</div>

  <div v-else-if="cards.length === 1" class="sfc-card">
    <div class="sfc-kicker">선택한 설비</div>
    <FacilityImage v-if="cards[0].info" class="sfc-img" :info="cards[0].info" :alt="`${cards[0].name} 설비 사진`" animated />
    <div v-else class="sfc-img sfc-noimg" aria-hidden="true">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
      </svg>
    </div>
    <div class="sfc-name">
      {{ cards[0].name }} <span class="sfc-code">{{ cards[0].code }}</span>
    </div>
    <div v-if="cards[0].info" class="sfc-summary">{{ cards[0].info.summary }}</div>
    <div class="sfc-count">
      <b>{{ cards[0].total }}</b>대 ·
      <span :class="cards[0].needsInspection > 0 ? 'sfc-warn' : 'sfc-ok'">점검필요 {{ cards[0].needsInspection }}</span>
    </div>
    <RouterLink :to="cards[0].to" class="sfc-link">자세히 보기 →</RouterLink>
  </div>

  <div v-else class="sfc-card">
    <div class="sfc-kicker">선택한 설비 {{ cards.length }}</div>
    <div class="sfc-grid">
      <RouterLink v-for="card in cards" :key="card.code" :to="card.to" class="sfc-thumb">
        <FacilityImage v-if="card.info" class="sfc-img" :info="card.info" alt="" animated />
        <div v-else class="sfc-img sfc-noimg" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
          </svg>
        </div>
        <b class="sfc-thumb-name">{{ card.name }}</b>
        <span class="sfc-thumb-count">
          {{ card.total }}대 · <span :class="card.needsInspection > 0 ? 'sfc-warn' : 'sfc-ok'">점검 {{ card.needsInspection }}</span>
        </span>
      </RouterLink>
    </div>
    <RouterLink :to="GUIDE_PATH" class="sfc-link">설비 안내 보기 →</RouterLink>
  </div>
</template>

<style scoped>
.sfc-hint {
  font-size: 12px;
  color: #8891a0;
  line-height: 1.6;
  padding: 0 2px;
}
.sfc-card {
  border: 1px solid #b9dfdf;
  background: #f3fafa;
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.sfc-kicker {
  font-size: 11px;
  font-weight: 700;
  color: #0b6f6f;
}
.sfc-img {
  display: block;
  width: 100%;
  aspect-ratio: 496 / 366;
  object-fit: contain;
  border-radius: 8px;
  background: #f3f5fb;
  border: 1px solid #e2e5ea;
  box-sizing: border-box;
}
.sfc-noimg {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #b4bac4;
}
.sfc-name {
  font-size: 15px;
  font-weight: 700;
  color: #1a2230;
}
.sfc-code {
  font-size: 11px;
  font-weight: 600;
  color: #8891a0;
}
.sfc-summary {
  font-size: 12px;
  color: #4a5361;
  line-height: 1.55;
}
.sfc-count {
  font-size: 12px;
  color: #1a2230;
}
.sfc-warn {
  color: #a8590a;
  font-weight: 600;
}
.sfc-ok {
  color: #0b6f6f;
  font-weight: 600;
}
.sfc-link {
  font-size: 12px;
  font-weight: 600;
  color: #0b6f6f;
  text-decoration: none;
}
.sfc-link:hover {
  text-decoration: underline;
}
.sfc-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.sfc-thumb {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  padding: 6px;
  color: #1a2230;
  text-decoration: none;
}
.sfc-thumb:hover {
  border-color: #0f8a8a;
}
.sfc-thumb .sfc-img {
  border: 0;
  border-radius: 6px;
}
.sfc-thumb-name {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sfc-thumb-count {
  font-size: 11px;
  color: #8891a0;
}
</style>
