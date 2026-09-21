<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useEquipmentStore } from "../stores/equipment";
import RiskScatterChart from "../components/RiskScatterChart.vue";
import EquipmentCard from "../components/EquipmentCard.vue";
import EquipmentListTable from "../components/EquipmentListTable.vue";
import EquipmentDetailPanel from "../components/EquipmentDetailPanel.vue";
import MultiSelectFilter from "../components/MultiSelectFilter.vue";
import { getEvidence, getReasonsByAxis } from "../utils/scoreBreakdown";
import type { ReasonsByAxis } from "../utils/scoreBreakdown";
import { statusColor, statusLabel } from "../utils/statusStyle";
import type { EquipmentDetail, EquipmentSummary } from "../types/equipment";

const store = useEquipmentStore();
const selectedId = ref<number | null>(null);
const hoveredId = ref<number | null>(null);
const reasonScrollEl = ref<HTMLDivElement | null>(null);

const FACTORY_OPTIONS = [
  { value: "H1", label: "H1" },
  { value: "H2", label: "H2" },
  { value: "K1", label: "K1" },
  { value: "P1", label: "P1" },
];
const EQUIPMENT_TYPE_OPTIONS = [{ value: "EF1", label: "EF1 · 변압기" }];

const filterSummaryText = computed(() => {
  const factoryText = store.factoryFilters.length === 0 ? "전체 사업장" : store.factoryFilters.join(", ");
  const typeText = store.equipmentTypeFilters.length === 0 ? "EF1 · 변압기" : store.equipmentTypeFilters.join(", ");
  return `${typeText} · ${factoryText}`;
});

const EMPTY_REASONS: ReasonsByAxis = { pof: [], cof: [], dof: [] };

const detailReasons = computed(() =>
  store.needsInspectionList.map((item) => {
    const detail = store.detailCache[item.equipment_id] as EquipmentDetail | undefined;
    return {
      item,
      detail,
      reasons: detail ? getReasonsByAxis(detail.score_detail) : EMPTY_REASONS,
    };
  }),
);

interface ReasonTooltip {
  label: string;
  value: number;
  evidence: string;
  color: string;
  top: number;
  left: number;
}

const hoveredReason = ref<ReasonTooltip | null>(null);

function onReasonEnter(event: MouseEvent, reason: { label: string; value: number; field: string }, detail: EquipmentDetail | undefined, color: string) {
  if (!detail || !reasonScrollEl.value) return;
  const evidence = getEvidence(reason.field, detail);
  if (!evidence) return;

  const containerRect = reasonScrollEl.value.getBoundingClientRect();
  const targetRect = (event.currentTarget as HTMLElement).getBoundingClientRect();
  hoveredReason.value = {
    label: reason.label,
    value: reason.value,
    evidence,
    color,
    top: targetRect.top - containerRect.top + reasonScrollEl.value.scrollTop - 6,
    left: targetRect.left - containerRect.left,
  };
}

function onReasonLeave() {
  hoveredReason.value = null;
}

const normalCount = computed(() => store.equipmentList.filter((item) => item.status === "normal").length);
const reviewCount = computed(() => store.equipmentList.filter((item) => item.status === "review").length);
const replaceCount = computed(() => store.equipmentList.filter((item) => item.status === "replace").length);

type SortKey = "score_asc" | "score_desc" | "name_asc" | "name_desc";
const SORT_LABELS: Record<SortKey, string> = {
  score_asc: "종합점수 낮은순",
  score_desc: "종합점수 높은순",
  name_asc: "설비명 오름차순",
  name_desc: "설비명 내림차순",
};

const searchQuery = ref("");
const sortKey = ref<SortKey>("score_asc");

// 완전 일치가 아니어도(순서만 같으면 중간에 다른 글자가 끼어 있어도) 매치되는 느슨한 검색.
// 예: "bk3"는 "BANK3"에 매치됨(b→B, k→K, 3→3 순서대로 등장).
function fuzzyMatch(target: string, query: string): boolean {
  let qi = 0;
  const t = target.toLowerCase();
  for (let ti = 0; ti < t.length && qi < query.length; ti++) {
    if (t[ti] === query[qi]) qi++;
  }
  return qi === query.length;
}

const displayList = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  const filtered = query ? store.equipmentList.filter((item) => fuzzyMatch(item.transformer_name, query)) : store.equipmentList;

  const sorted = [...filtered];
  switch (sortKey.value) {
    case "score_asc":
      sorted.sort((a, b) => a.total_score - b.total_score);
      break;
    case "score_desc":
      sorted.sort((a, b) => b.total_score - a.total_score);
      break;
    case "name_asc":
      sorted.sort((a, b) => a.transformer_name.localeCompare(b.transformer_name));
      break;
    case "name_desc":
      sorted.sort((a, b) => b.transformer_name.localeCompare(a.transformer_name));
      break;
  }
  return sorted;
});

const PAGE_SIZE = 24;
const viewMode = ref<"card" | "list">("card");
const currentPage = ref(1);

const totalPages = computed(() => Math.max(1, Math.ceil(displayList.value.length / PAGE_SIZE)));

const pagedList = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE;
  return displayList.value.slice(start, start + PAGE_SIZE);
});

// 검색/정렬/필터가 바뀌면 지금 보던 페이지 번호가 더 이상 유효하지 않을 수 있어 1페이지로 되돌린다.
watch([searchQuery, sortKey, () => store.factoryFilters, () => store.equipmentTypeFilters], () => {
  currentPage.value = 1;
});

function goToPage(page: number) {
  currentPage.value = Math.min(Math.max(page, 1), totalPages.value);
}

onMounted(async () => {
  await store.load();
  // 점검필요 순위 리스트의 감점 사유를 보여주기 위해 상세를 미리 불러온다.
  await Promise.all(store.needsInspectionList.map((item) => store.loadDetail(item.equipment_id)));
  // 기본값: 종합점수가 가장 낮은(가장 시급한) 설비를 자동 선택
  if (selectedId.value === null && store.equipmentList.length > 0) {
    selectedId.value = store.equipmentList[0].equipment_id;
  }
});

function selectCard(equipmentId: number) {
  selectedId.value = equipmentId;
}

function onChartHover(equipmentId: number | null) {
  hoveredId.value = equipmentId;
  if (equipmentId === null || !reasonScrollEl.value) return;
  reasonScrollEl.value.querySelector(`[data-equipment-id="${equipmentId}"]`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function formatDateTime(value: string | null): string {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 16);
}

function reasonCardStyle(item: EquipmentSummary, isActive: boolean) {
  const color = statusColor(item.status);
  return isActive ? { borderColor: color, boxShadow: `0 0 0 2px ${color}26` } : { borderColor: color };
}
</script>

<template>
  <div class="dashboard">
    <header class="topbar">
      <div class="brand">
        <div class="title">전기설비 수명관리 시스템</div>
        <div class="subtitle">각 설비의 POF, COF, DOF 지수를 평가하여 점검 설비 우선 순위를 도출합니다.</div>
      </div>
      <div class="filters">
        <span class="filter-badge">{{ filterSummaryText }}</span>
      </div>
    </header>

    <div class="body">
      <aside class="rail">
        <MultiSelectFilter
          label="설비유형"
          :options="EQUIPMENT_TYPE_OPTIONS"
          :model-value="store.equipmentTypeFilters"
          all-label="전체 설비유형"
          @update:model-value="store.setEquipmentTypeFilters"
        />
        <div class="rail-hint">EF2~EF22 설비유형 추가 예정</div>

        <MultiSelectFilter
          label="사업장"
          :options="FACTORY_OPTIONS"
          :model-value="store.factoryFilters"
          all-label="전체 사업장"
          @update:model-value="store.setFactoryFilters"
        />
      </aside>

      <main class="main">
        <div v-if="store.loading" class="loading">불러오는 중...</div>
        <div v-else-if="store.error" class="error">{{ store.error }}</div>
        <template v-else>
          <div class="kpi-row">
            <div class="card kpi">
              <div class="kpi-label">전체 설비</div>
              <div class="kpi-value">{{ store.equipmentList.length }}<span class="unit">대</span></div>
              <div class="kpi-sub">EF1 · 변압기 기준{{ store.factoryFilters.length > 0 ? ` · ${store.factoryFilters.join(", ")} 필터 적용` : "" }}</div>
            </div>
            <div class="card kpi">
              <div class="kpi-label">정상 설비</div>
              <div class="kpi-value" :style="{ color: statusColor('normal') }">{{ normalCount }}<span class="unit">대</span></div>
              <div class="kpi-sub">{{ statusLabel("normal") }} 기준 충족</div>
            </div>
            <div class="card kpi">
              <div class="kpi-label">교체검토 설비</div>
              <div class="kpi-value" :style="{ color: statusColor('review') }">{{ reviewCount }}<span class="unit">대</span></div>
              <div class="kpi-sub">POF 기준 경계 구간</div>
            </div>
            <div class="card kpi">
              <div class="kpi-label">즉시교체 설비</div>
              <div class="kpi-value" :style="{ color: statusColor('replace') }">{{ replaceCount }}<span class="unit">대</span></div>
              <div class="kpi-sub">POF 기준 미달</div>
            </div>
            <div class="card kpi">
              <div class="kpi-label">최근 데이터 갱신</div>
              <div class="kpi-value small">{{ formatDateTime(store.summary?.last_updated ?? null) }}</div>
              <div class="kpi-sub">DGA · Furan 정기점검 반영</div>
            </div>
          </div>

          <div class="list-header">
            <div class="list-title">
              POF·COF·DOF 지수 3차원 분포도
              <RouterLink to="/guide" class="guide-link" title="지표 설명 보기">?</RouterLink>
            </div>
          </div>

          <div class="risk-panel">
            <div class="risk-header">
              <div class="risk-count">{{ store.needsInspectionList.length }}<span class="risk-label">건 점검필요</span></div>
              <div class="risk-desc">교체검토(노랑)·즉시교체(빨강) 설비를 표시</div>
            </div>
            <div class="risk-body">
              <div class="chart-col">
                <RiskScatterChart :equipment-list="store.equipmentList" :selected-id="selectedId" @select="selectCard" @hover="onChartHover" />
              </div>
              <div class="reason-col">
                <div class="reason-title">점검필요 순위 · 종합점수 낮은순</div>
                <div class="reason-hint">항목이 많아지면 이 영역 안에서만 스크롤됩니다</div>
                <div class="reason-scroll" ref="reasonScrollEl">
                  <div
                    v-for="entry in detailReasons"
                    :key="entry.item.equipment_id"
                    class="reason-card"
                    :class="{ active: selectedId === entry.item.equipment_id, hovered: hoveredId === entry.item.equipment_id }"
                    :style="reasonCardStyle(entry.item, selectedId === entry.item.equipment_id)"
                    :data-equipment-id="entry.item.equipment_id"
                    @click="selectCard(entry.item.equipment_id)"
                  >
                    <div class="reason-row">
                      <span class="reason-name">{{ entry.item.transformer_name }}</span>
                      <span class="reason-score" :style="{ color: statusColor(entry.item.status) }">
                        {{ statusLabel(entry.item.status) }} · 종합점수 {{ entry.item.total_score.toFixed(1) }}
                      </span>
                    </div>
                    <div class="reason-meta">{{ entry.item.factory_code }} · {{ entry.item.voltage.toLocaleString() }}V</div>

                    <div class="axis-grid">
                      <div class="axis-col">
                        <div class="axis-head">POF <b>{{ entry.item.pof }}</b></div>
                        <div
                          v-for="reason in entry.reasons.pof"
                          :key="reason.label"
                          class="axis-reason"
                          @mouseenter="onReasonEnter($event, reason, entry.detail, statusColor(entry.item.status))"
                          @mouseleave="onReasonLeave"
                        >
                          <span class="reason-label">{{ reason.label }}</span> <span class="neg">{{ reason.value }}</span>
                        </div>
                        <div v-if="entry.reasons.pof.length === 0" class="axis-empty">감점 없음</div>
                      </div>
                      <div class="axis-col">
                        <div class="axis-head">COF <b>{{ entry.item.cof }}</b></div>
                        <div
                          v-for="reason in entry.reasons.cof"
                          :key="reason.label"
                          class="axis-reason"
                          @mouseenter="onReasonEnter($event, reason, entry.detail, statusColor(entry.item.status))"
                          @mouseleave="onReasonLeave"
                        >
                          <span class="reason-label">{{ reason.label }}</span> <span class="neg">{{ reason.value }}</span>
                        </div>
                        <div v-if="entry.reasons.cof.length === 0" class="axis-empty">감점 없음</div>
                      </div>
                      <div class="axis-col">
                        <div class="axis-head">DOF <b>{{ entry.item.dof }}</b></div>
                        <div
                          v-for="reason in entry.reasons.dof"
                          :key="reason.label"
                          class="axis-reason"
                          @mouseenter="onReasonEnter($event, reason, entry.detail, statusColor(entry.item.status))"
                          @mouseleave="onReasonLeave"
                        >
                          <span class="reason-label">{{ reason.label }}</span> <span class="neg">{{ reason.value }}</span>
                        </div>
                        <div v-if="entry.reasons.dof.length === 0" class="axis-empty">감점 없음</div>
                      </div>
                    </div>
                  </div>
                  <div v-if="detailReasons.length === 0" class="muted">점검필요 설비가 없습니다</div>

                  <div v-if="hoveredReason" class="reason-tooltip" :style="{ top: `${hoveredReason.top}px`, left: `${hoveredReason.left}px`, borderColor: hoveredReason.color }">
                    <div class="rt-head">
                      <span class="rt-label">{{ hoveredReason.label }}</span>
                      <span class="rt-value">{{ hoveredReason.value }}</span>
                    </div>
                    <div class="rt-evidence">{{ hoveredReason.evidence }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="list-header">
            <div class="list-title">설비 목록</div>
            <div class="list-hint">
              {{ searchQuery ? `전체 ${store.equipmentList.length}건 중 ${displayList.length}건 검색됨` : `전체 ${displayList.length}건` }}
              · 정렬: {{ SORT_LABELS[sortKey] }} · 카드를 클릭하면(또는 위 3D 그래프의 점을 클릭하면) 아래 상세정보가 갱신됩니다
            </div>
          </div>

          <div class="list-controls">
            <input v-model="searchQuery" type="text" class="search-input" placeholder="설비명 검색 (예: BANK3)" />
            <select v-model="sortKey" class="sort-select">
              <option v-for="(label, key) in SORT_LABELS" :key="key" :value="key">{{ label }}</option>
            </select>
            <div class="view-toggle">
              <button class="view-btn" :class="{ active: viewMode === 'card' }" title="카드형" @click="viewMode = 'card'">⊞</button>
              <button class="view-btn" :class="{ active: viewMode === 'list' }" title="리스트형" @click="viewMode = 'list'">☰</button>
            </div>
          </div>

          <EquipmentDetailPanel v-if="selectedId !== null" :equipment-id="selectedId" />

          <div v-if="displayList.length === 0" class="muted" style="padding: 24px 0">검색 결과가 없습니다</div>
          <template v-else>
            <div v-if="viewMode === 'card'" class="card-grid">
              <EquipmentCard
                v-for="item in pagedList"
                :key="item.equipment_id"
                :summary="item"
                :active="selectedId === item.equipment_id"
                @select="selectCard"
              />
            </div>
            <EquipmentListTable v-else :items="pagedList" :active-id="selectedId" @select="selectCard" />

            <div v-if="totalPages > 1" class="pagination">
              <button class="page-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">이전</button>
              <button
                v-for="page in totalPages"
                :key="page"
                class="page-btn"
                :class="{ active: page === currentPage }"
                @click="goToPage(page)"
              >
                {{ page }}
              </button>
              <button class="page-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">다음</button>
            </div>
          </template>
        </template>
      </main>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: #f4f5f7;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  color: #1a2230;
  display: flex;
  flex-direction: column;
}
.topbar {
  height: 96px;
  flex: 0 0 auto;
  background: #fff;
  border-bottom: 1px solid #e2e5ea;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 0 32px 14px;
}
.title {
  font-size: 24px;
  font-weight: 700;
}
.subtitle {
  font-size: 14px;
  color: #8891a0;
  margin-top: 4px;
}
.filters {
  display: flex;
  align-items: center;
  gap: 8px;
}
.filter-badge {
  font-size: 12px;
  font-weight: 600;
  color: #4a5361;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  padding: 5px 10px;
}
.body {
  display: flex;
  flex: 1;
}
.rail {
  width: 224px;
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  gap: 22px;
  background: #fff;
  border-right: 1px solid #e2e5ea;
  padding: 24px 20px;
}
.rail-hint {
  font-size: 11.5px;
  color: #b4bac4;
  margin-top: -14px;
}
.main {
  flex: 1;
  padding: 28px 32px 40px;
  overflow: auto;
}
.loading,
.error {
  padding: 40px;
  text-align: center;
  color: #8891a0;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.card {
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  padding: 16px 18px;
}
.kpi-label {
  font: 600 11px "IBM Plex Sans";
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #8891a0;
}
.kpi-value {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 28px;
  font-weight: 600;
  margin-top: 6px;
}
.kpi-value.small {
  font-size: 20px;
}
.unit {
  font-size: 14px;
  color: #8891a0;
  font-weight: 500;
}
.kpi-sub {
  font-size: 11.5px;
  color: #8891a0;
  margin-top: 4px;
}
.risk-panel {
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 28px;
}
.risk-header {
  display: flex;
  align-items: baseline;
  gap: 14px;
  padding: 18px 22px;
  background: #f4f5f7;
  border-bottom: 1px solid #e2e5ea;
}
.risk-count {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 30px;
  font-weight: 700;
  color: #1a2230;
}
.risk-label {
  font-size: 14px;
  font-family: "IBM Plex Sans";
  font-weight: 600;
}
.risk-desc {
  font-size: 12px;
  color: #8891a0;
}
.risk-body {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(380px, 1.3fr);
  height: 540px;
}
.chart-col {
  padding: 18px 10px 8px 18px;
  border-right: 1px solid #eef0f3;
}
.reason-col {
  padding: 18px 22px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}
.reason-title {
  font: 600 11px "IBM Plex Sans";
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #8891a0;
  margin-bottom: 4px;
}
.reason-hint {
  font-size: 10.5px;
  color: #b4bac4;
  margin-bottom: 10px;
}
.reason-scroll {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 6px;
}
.reason-tooltip {
  position: absolute;
  transform: translateY(calc(-100% - 6px));
  z-index: 5;
  min-width: 160px;
  max-width: 220px;
  background: #fff;
  border: 1px solid #1a2230;
  border-radius: 9px;
  padding: 8px 10px;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.14);
  pointer-events: none;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
}
.rt-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}
.rt-label {
  font-size: 11px;
  font-weight: 700;
  color: #1a2230;
}
.rt-value {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px;
  font-weight: 700;
  color: #c4392b;
}
.rt-evidence {
  font-size: 10px;
  color: #4a5361;
  line-height: 1.5;
}
.reason-card {
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 10px;
  cursor: pointer;
}
.reason-card.active {
  border-width: 2px;
  padding: 11px 13px;
  background: #fafbfc;
}
.reason-card.hovered:not(.active) {
  box-shadow: 0 0 0 2px rgba(15, 138, 138, 0.15);
}
.reason-row {
  display: flex;
  justify-content: space-between;
}
.reason-name {
  font-weight: 700;
}
.reason-score {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 700;
}
.reason-meta {
  font-size: 11px;
  color: #8891a0;
  margin-bottom: 8px;
}
.axis-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0 10px;
}
.axis-col {
  min-width: 0;
  border-left: 1px solid #eef0f3;
  padding-left: 8px;
}
.axis-col:first-child {
  border-left: none;
  padding-left: 0;
}
.axis-head {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px;
  font-weight: 600;
  color: #4a5361;
  margin-bottom: 4px;
}
.axis-reason {
  font-size: 10.5px;
  color: #4a5361;
  line-height: 1.5;
  overflow-wrap: break-word;
  cursor: help;
}
.reason-label {
  border-bottom: 1px dotted #c7ccd3;
}
.axis-empty {
  font-size: 10.5px;
  color: #b4bac4;
}
.neg {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  color: #c4392b;
}
.list-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 14px;
}
.list-title {
  font-size: 15px;
  font-weight: 700;
}
.guide-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-left: 6px;
  border-radius: 50%;
  border: 1px solid #c7ccd3;
  color: #8891a0;
  font-size: 11px;
  font-weight: 700;
  text-decoration: none;
  vertical-align: middle;
}
.guide-link:hover {
  border-color: #0f8a8a;
  color: #0f8a8a;
}
.list-hint {
  font-size: 12px;
  color: #8891a0;
}
.list-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.search-input {
  flex: 1;
  max-width: 320px;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  padding: 8px 12px;
  font: 500 13px "IBM Plex Sans", sans-serif;
  color: #1a2230;
}
.search-input:focus {
  outline: none;
  border-color: #0f8a8a;
}
.sort-select {
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  padding: 8px 12px;
  font: 500 13px "IBM Plex Sans", sans-serif;
  color: #1a2230;
  background: #fff;
}
.view-toggle {
  display: flex;
  gap: 2px;
  margin-left: auto;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  padding: 2px;
}
.view-btn {
  border: none;
  background: transparent;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 15px;
  line-height: 1;
  color: #8891a0;
  cursor: pointer;
}
.view-btn.active {
  background: #1a2230;
  color: #fff;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 16px;
}
.pagination {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 20px;
  justify-content: center;
}
.page-btn {
  border: 1px solid #e2e5ea;
  background: #fff;
  border-radius: 6px;
  padding: 6px 12px;
  font: 500 13px "IBM Plex Mono", ui-monospace, monospace;
  color: #4a5361;
  cursor: pointer;
}
.page-btn:disabled {
  color: #c7ccd3;
  cursor: not-allowed;
}
.page-btn.active {
  background: #1a2230;
  border-color: #1a2230;
  color: #fff;
}
.muted {
  color: #8891a0;
  font-size: 12px;
}
</style>
