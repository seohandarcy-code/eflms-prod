<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useEquipmentStore } from "../stores/equipment";
import RiskScatterChart from "../components/RiskScatterChart.vue";
import EquipmentCard from "../components/EquipmentCard.vue";
import EquipmentListTable from "../components/EquipmentListTable.vue";
import EquipmentDetailPanel from "../components/EquipmentDetailPanel.vue";
import MultiSelectFilter from "../components/MultiSelectFilter.vue";
import SelectedFacilityCard from "../components/SelectedFacilityCard.vue";
import ScoreSimulatorDialog from "../components/ScoreSimulatorDialog.vue";
import UserBadge from "../components/UserBadge.vue";
import FilterSummaryBox from "../components/FilterSummaryBox.vue";
import { getEvidence, getReasonsByAxis } from "../utils/scoreBreakdown";
import type { ReasonsByAxis } from "../utils/scoreBreakdown";
import { formatMonth } from "../utils/formatDate";
import { AXIS_NAME, formatScore } from "../utils/formatValue";
import { refreshCaption, refreshTooltip, scoreDateText } from "../utils/scoreRefresh";
import { statusColor, statusLabel } from "../utils/statusStyle";
import type { EquipmentDetail, EquipmentSummary } from "../types/equipment";

const store = useEquipmentStore();
const route = useRoute();
const router = useRouter();
const selectedId = ref<number | null>(null);
const hoveredId = ref<number | null>(null);
const reasonScrollEl = ref<HTMLDivElement | null>(null);
// 점수 시뮬레이터 팝업(Stage 19) — 설비유형 필터가 하나면 그 유형으로 연다
const simulatorOpen = ref(false);
// 점수 기준일 칸 캡션 — 마지막 점수 갱신 시각(자동/수동), Stage 21-1c
const refreshCaptionText = computed(() =>
  refreshCaption(store.summary?.score_refreshed_at, store.summary?.score_refresh_trigger),
);
const simulatorType = computed(() => (store.equipmentTypeFilters.length === 1 ? store.equipmentTypeFilters[0] : null));

// 사업장 옵션은 받아 둔 설비 목록에 실제로 있는 사업장만(store.factoryCodes) — 데이터가 늘면 자동으로 나타난다.
const factoryOptions = computed(() => store.factoryCodes.map((code) => ({ value: code, label: code })));
// 설비유형 옵션은 백엔드 레지스트리(/api/equipment-types)에서 온다 — 새 유형이 등록되면 자동으로 나타난다.
const equipmentTypeOptions = computed(() =>
  store.equipmentTypes.map((t) => ({ value: t.ef_code, label: t.ef_name, sub: t.ef_code })),
);

// KPI "전체 설비" 아래에 유형별 대수를 나눠 보여준다(필터 적용 후 목록 기준).
const typeCountText = computed(() =>
  store.visibleTypeCodes
    .map((code) => `${store.typeNames[code] ?? code} ${store.equipmentList.filter((item) => item.ef_code === code).length}`)
    .join(" · "),
);

// 선택한 설비유형을 URL(?type=EF1,EF2)에 남겨 링크로 공유할 수 있게 한다.
function typesFromQuery(): string[] {
  const raw = route.query.type;
  const value = Array.isArray(raw) ? raw.join(",") : (raw ?? "");
  return value.split(",").map((code) => code.trim()).filter(Boolean);
}

watch(
  () => store.equipmentTypeFilters,
  (codes) => {
    const type = codes.length > 0 ? codes.join(",") : undefined;
    if ((route.query.type ?? undefined) !== type) {
      router.replace({ query: { ...route.query, type } });
    }
  },
);

const EMPTY_REASONS: ReasonsByAxis = { pof: [], cof: [], dof: [] };

const detailReasons = computed(() =>
  store.needsInspectionList.map((item) => {
    const detail = store.detailCache[item.equipment_id] as EquipmentDetail | undefined;
    return {
      item,
      detail,
      reasons: detail ? getReasonsByAxis(detail.type_detail.score_detail, store.breakdownFor(detail.ef_code)) : EMPTY_REASONS,
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
  const filtered = query ? store.equipmentList.filter((item) => fuzzyMatch(item.equipment_name, query)) : store.equipmentList;

  const sorted = [...filtered];
  switch (sortKey.value) {
    case "score_asc":
      sorted.sort((a, b) => a.total_score - b.total_score);
      break;
    case "score_desc":
      sorted.sort((a, b) => b.total_score - a.total_score);
      break;
    case "name_asc":
      sorted.sort((a, b) => a.equipment_name.localeCompare(b.equipment_name));
      break;
    case "name_desc":
      sorted.sort((a, b) => b.equipment_name.localeCompare(a.equipment_name));
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

// 필터를 바꿔서 선택된 설비가 목록에서 빠지면, 남은 목록에서 가장 시급한 설비로 바꾼다.
watch(
  () => store.equipmentList,
  (list) => {
    if (list.length === 0) {
      selectedId.value = null;
    } else if (!list.some((item) => item.equipment_id === selectedId.value)) {
      selectedId.value = list[0].equipment_id;
    }
  },
);

onMounted(async () => {
  const queryTypes = typesFromQuery();
  if (queryTypes.length > 0) store.setEquipmentTypeFilters(queryTypes);
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

function reasonCardStyle(item: EquipmentSummary, isActive: boolean) {
  const color = statusColor(item.status);
  return isActive ? { borderColor: color, boxShadow: `0 0 0 2px ${color}26` } : { borderColor: color };
}
</script>

<template>
  <div class="dashboard">
    <header class="topbar">
      <div class="brand">
        <div class="brand-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
          </svg>
        </div>
        <div>
          <div class="title">전기설비 수명관리 시스템</div>
          <div class="subtitle">각 설비의 POF(설비상태), COF(고장영향성), DOF(고장예방력) 지수를 평가하여 점검 설비 우선 순위를 도출합니다.</div>
        </div>
      </div>
      <div class="filters">
        <!-- 위 오른쪽: 사업장·설비유형 2단 요약 + 맨 오른쪽 로그인 카드(2026-11-19 시안 D) -->
        <FilterSummaryBox :factories="store.factoryFilters" :types="store.equipmentTypeFilters" :type-names="store.typeNames" />
        <UserBadge />
      </div>
    </header>

    <div class="body">
      <aside class="rail">
        <MultiSelectFilter
          label="사업장"
          :options="factoryOptions"
          empty-text="사업장 데이터 없음"
          :model-value="store.factoryFilters"
          all-label="전체 사업장"
          @update:model-value="store.setFactoryFilters"
        />

        <div class="rail-group">
          <MultiSelectFilter
            label="설비유형"
            :options="equipmentTypeOptions"
            :model-value="store.equipmentTypeFilters"
            all-label="전체 설비유형"
            help-to="/guide/facilities"
            help-title="설비 안내 보기"
            help-caption="전력이 흐르는 순서와 설비별 역할을 그림과 표로 볼 수 있어요"
            @update:model-value="store.setEquipmentTypeFilters"
          />
          <SelectedFacilityCard
            :selected="store.equipmentTypeFilters"
            :items="store.equipmentList"
            :type-names="store.typeNames"
          />
        </div>

        <RouterLink to="/admin" class="admin-link">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          관리자
        </RouterLink>
      </aside>

      <main class="main">
        <div v-if="store.loading" class="loading">불러오는 중...</div>
        <div v-else-if="store.error" class="error">{{ store.error }}</div>
        <template v-else>
          <div class="kpi-row">
            <div class="card kpi">
              <div class="kpi-label">전체 설비</div>
              <div class="kpi-value">{{ store.equipmentList.length }}<span class="unit">대</span></div>
              <div class="kpi-sub">{{ typeCountText || "-" }}{{ store.factoryFilters.length > 0 ? ` · ${store.factoryFilters.join(", ")} 필터 적용` : "" }}</div>
            </div>
            <div class="card kpi">
              <div class="kpi-label">정상 설비</div>
              <div class="kpi-value" :style="{ color: statusColor('normal') }">{{ normalCount }}<span class="unit">대</span></div>
              <div class="kpi-sub">{{ statusLabel("normal") }} 기준 충족</div>
            </div>
            <div class="card kpi">
              <div class="kpi-label">교체검토 필요설비</div>
              <div class="kpi-value" :style="{ color: statusColor('review') }">{{ reviewCount }}<span class="unit">대</span></div>
              <div class="kpi-sub">POF 기준 경계 구간</div>
            </div>
            <div class="card kpi">
              <div class="kpi-label">즉시교체 필요설비</div>
              <div class="kpi-value" :style="{ color: statusColor('replace') }">{{ replaceCount }}<span class="unit">대</span></div>
              <div class="kpi-sub">POF 기준 미달</div>
            </div>
            <div class="card kpi" :title="refreshTooltip(store.summary?.score_refresh_auto ?? false)">
              <!-- 점수 기준일(매일 갱신)·마지막 갱신 시각과 진단 데이터 최근 반영일(입력·수정)을 나눠 보여준다(Stage 21-1/21-1c) -->
              <div class="kpi-label">점수 기준일</div>
              <div class="kpi-value small">{{ scoreDateText(store.summary?.score_as_of, store.summary?.score_as_of_latest) }}</div>
              <div v-if="refreshCaptionText" class="kpi-sub">{{ refreshCaptionText }}</div>
              <div class="kpi-sub kpi-sub-tight">진단 데이터 최근 반영일 <span class="nowrap">{{ store.summary?.data_updated_on ?? "-" }}</span></div>
            </div>
          </div>

          <div class="list-header">
            <div class="list-title">
              POF(설비상태)·COF(고장영향성)·DOF(고장예방력) 지수 3차원 분포도
              <span class="guide-link-wrap">
                <RouterLink to="/guide" class="guide-link">?</RouterLink>
                <div class="guide-tooltip">
                  <div class="gt-head">
                    <span class="gt-dot"></span>
                    <span class="gt-name">지표 설명 보기</span>
                  </div>
                  <div class="gt-caption">POF·COF·DOF 정의, 계산식, 판정 기준을 확인할 수 있어요</div>
                </div>
              </span>
              <span class="guide-link-wrap">
                <button type="button" class="sim-link" @click="simulatorOpen = true">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <rect x="4" y="2" width="16" height="20" rx="2" />
                    <line x1="8" y1="6" x2="16" y2="6" />
                    <line x1="8" y1="11" x2="8" y2="11" />
                    <line x1="12" y1="11" x2="12" y2="11" />
                    <line x1="16" y1="11" x2="16" y2="11" />
                    <line x1="8" y1="15" x2="8" y2="15" />
                    <line x1="12" y1="15" x2="12" y2="15" />
                    <line x1="16" y1="15" x2="16" y2="18" />
                  </svg>
                  시뮬레이터
                </button>
                <div class="guide-tooltip">
                  <div class="gt-head">
                    <span class="gt-dot"></span>
                    <span class="gt-name">점수 시뮬레이터</span>
                  </div>
                  <div class="gt-caption">설비유형과 입력값을 넣어 POF·COF·DOF와 종합점수를 직접 계산해 볼 수 있어요(DB에는 저장되지 않음)</div>
                </div>
              </span>
            </div>
          </div>

          <div class="risk-panel">
            <div class="risk-header">
              <div class="risk-count">{{ store.needsInspectionList.length }}<span class="risk-label">건 점검필요</span></div>
              <div class="risk-desc">교체검토 필요설비(노랑)·즉시교체 필요설비(빨강)를 표시</div>
            </div>
            <div class="risk-body">
              <div class="chart-col">
                <RiskScatterChart
                  :equipment-list="store.equipmentList"
                  :selected-id="selectedId"
                  :type-names="store.typeNames"
                  @select="selectCard"
                  @hover="onChartHover"
                />
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
                      <span class="reason-name">{{ entry.item.equipment_name }}</span>
                      <span class="reason-score" :style="{ color: statusColor(entry.item.status) }">
                        {{ statusLabel(entry.item.status) }} · 종합점수 {{ entry.item.total_score.toFixed(1) }}
                      </span>
                    </div>
                    <div class="reason-meta">{{ store.typeNames[entry.item.ef_code] ?? entry.item.ef_code }} · {{ entry.item.factory_code }} · 가동 {{ formatMonth(entry.item.operation_start_time) }}</div>

                    <div class="axis-grid">
                      <div class="axis-col">
                        <div class="axis-head">POF<span class="axis-ko">({{ AXIS_NAME.pof }})</span> <b>{{ formatScore(entry.item.pof) }}</b></div>
                        <div
                          v-for="reason in entry.reasons.pof"
                          :key="reason.label"
                          class="axis-reason"
                          @mouseenter="onReasonEnter($event, reason, entry.detail, statusColor(entry.item.status))"
                          @mouseleave="onReasonLeave"
                        >
                          <span class="reason-label">{{ reason.label }}</span> <span class="neg">{{ formatScore(reason.value) }}</span>
                        </div>
                        <div v-if="entry.reasons.pof.length === 0" class="axis-empty">감점 없음</div>
                      </div>
                      <div class="axis-col">
                        <div class="axis-head">COF<span class="axis-ko">({{ AXIS_NAME.cof }})</span> <b>{{ formatScore(entry.item.cof) }}</b></div>
                        <div
                          v-for="reason in entry.reasons.cof"
                          :key="reason.label"
                          class="axis-reason"
                          @mouseenter="onReasonEnter($event, reason, entry.detail, statusColor(entry.item.status))"
                          @mouseleave="onReasonLeave"
                        >
                          <span class="reason-label">{{ reason.label }}</span> <span class="neg">{{ formatScore(reason.value) }}</span>
                        </div>
                        <div v-if="entry.reasons.cof.length === 0" class="axis-empty">감점 없음</div>
                      </div>
                      <div class="axis-col">
                        <div class="axis-head">DOF<span class="axis-ko">({{ AXIS_NAME.dof }})</span> <b>{{ formatScore(entry.item.dof) }}</b></div>
                        <div
                          v-for="reason in entry.reasons.dof"
                          :key="reason.label"
                          class="axis-reason"
                          @mouseenter="onReasonEnter($event, reason, entry.detail, statusColor(entry.item.status))"
                          @mouseleave="onReasonLeave"
                        >
                          <span class="reason-label">{{ reason.label }}</span> <span class="neg">{{ formatScore(reason.value) }}</span>
                        </div>
                        <div v-if="entry.reasons.dof.length === 0" class="axis-empty">감점 없음</div>
                      </div>
                    </div>
                  </div>
                  <div v-if="detailReasons.length === 0" class="muted">점검필요 설비가 없습니다</div>

                  <div v-if="hoveredReason" class="reason-tooltip" :style="{ top: `${hoveredReason.top}px`, left: `${hoveredReason.left}px`, borderColor: hoveredReason.color }">
                    <div class="rt-head">
                      <span class="rt-label">{{ hoveredReason.label }}</span>
                      <span class="rt-value">{{ formatScore(hoveredReason.value) }}</span>
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
            <input v-model="searchQuery" type="text" class="search-input" placeholder="설비명·설비코드 검색 (예: BANK3)" />
            <select v-model="sortKey" class="sort-select">
              <option v-for="(label, key) in SORT_LABELS" :key="key" :value="key">{{ label }}</option>
            </select>
            <div class="view-toggle">
              <button class="view-btn" :class="{ active: viewMode === 'card' }" title="카드형" @click="viewMode = 'card'">⊞</button>
              <button class="view-btn" :class="{ active: viewMode === 'list' }" title="리스트형" @click="viewMode = 'list'">☰</button>
            </div>
          </div>

          <EquipmentDetailPanel v-if="selectedId !== null" :equipment-id="selectedId" />
          <ScoreSimulatorDialog
            :open="simulatorOpen"
            :types="store.equipmentTypes"
            :initial-type="simulatorType"
            @close="simulatorOpen = false"
          />

          <div v-if="displayList.length === 0" class="muted" style="padding: 24px 0">검색 결과가 없습니다</div>
          <template v-else>
            <div v-if="viewMode === 'card'" class="card-grid">
              <EquipmentCard
                v-for="item in pagedList"
                :key="item.equipment_id"
                :summary="item"
                :type-name="store.typeNames[item.ef_code]"
                :active="selectedId === item.equipment_id"
                @select="selectCard"
              />
            </div>
            <EquipmentListTable v-else :items="pagedList" :active-id="selectedId" :type-names="store.typeNames" @select="selectCard" />

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
  gap: 32px;
  padding: 0 32px 14px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}
.brand-icon {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: #0f8a8a;
  display: flex;
  align-items: center;
  justify-content: center;
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
  gap: 12px;
  min-width: 0;
}
.body {
  display: flex;
  flex: 1;
}
.rail {
  /* 넓은 화면에서 확실히 넓어지고(1920px → 346px), 노트북 화면에선 차트를 덜 좁히도록 화면 폭에 비례(Stage 17-4). */
  width: clamp(280px, 18vw, 360px);
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  gap: 22px;
  background: #fff;
  border-right: 1px solid #e2e5ea;
  padding: 24px 20px;
}
.rail-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.admin-link {
  /* .rail이 .main과 같은 높이로 늘어나므로(사이드바 배경을 끝까지 채우기 위함),
     margin-top:auto만으로는 버튼이 페이지 맨 아래로 밀려 화면 밖으로 벗어난다.
     position:sticky로 스크롤해도 화면 하단 근처에 계속 보이게 고정한다. */
  margin-top: auto;
  position: sticky;
  bottom: 24px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #4a5361;
  text-decoration: none;
  background: #fff;
}
.admin-link:hover {
  background: #f4f5f7;
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
  font-size: 11px;
  color: #8891a0;
  margin-top: 4px;
}
.kpi-sub-tight {
  margin-top: 1px;
}
.nowrap {
  white-space: nowrap;
}
.risk-panel {
  background: #fff;
  border: 1px solid #f0cfc9;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 28px;
}
.risk-header {
  display: flex;
  align-items: baseline;
  gap: 14px;
  padding: 18px 22px;
  background: #fcf1ef;
  border-bottom: 1px solid #f0cfc9;
}
.risk-count {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 28px;
  font-weight: 700;
  color: #c4392b;
}
.risk-label {
  font-size: 14px;
  font-family: "IBM Plex Sans";
  font-weight: 600;
}
.risk-desc {
  font-size: 12px;
  color: #96382f;
}
.risk-body {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(380px, 1.3fr);
  /* 차트(480px) + 아래 설명 최대 4줄(1366px 화면 · 전체 선택)까지 잘리지 않게(Stage 17). */
  height: 580px;
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
  font-size: 11px;
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
  font-size: 11px;
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
/* 영어 약자 옆 "(한글 이름)" — 표기는 화면 전체 POF(설비상태) 형식(2026-11-19), 칸이 좁으면 점수가 다음 줄로 */
.axis-ko {
  font-family: system-ui, sans-serif;
  font-size: 10px;
  font-weight: 600;
  color: #8891a0;
}
.axis-reason {
  font-size: 11px;
  color: #4a5361;
  line-height: 1.5;
  overflow-wrap: break-word;
  cursor: help;
}
.reason-label {
  border-bottom: 1px dotted #c7ccd3;
}
.axis-empty {
  font-size: 11px;
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
.guide-link-wrap {
  position: relative;
  display: inline-block;
  vertical-align: middle;
}
.guide-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-left: 6px;
  border-radius: 50%;
  border: 1px solid #1b8a5a;
  color: #1b8a5a;
  font-size: 11px;
  font-weight: 700;
  text-decoration: none;
  vertical-align: middle;
}
.guide-link:hover {
  background: #1b8a5a;
  color: #fff;
}
.sim-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 22px;
  margin-left: 6px;
  padding: 0 9px;
  border-radius: 999px;
  border: 1px solid #1b8a5a;
  background: #fff;
  color: #1b8a5a;
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  vertical-align: middle;
}
.sim-link:hover,
.sim-link:focus-visible {
  background: #1b8a5a;
  color: #fff;
}
.guide-tooltip {
  position: absolute;
  z-index: 6;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  width: 220px;
  background: #fff;
  border: 1px solid #1b8a5a;
  border-radius: 9px;
  padding: 11px 14px;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.14);
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.12s ease;
  pointer-events: none;
}
.guide-link-wrap:hover .guide-tooltip {
  opacity: 1;
  visibility: visible;
}
.gt-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.gt-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #1b8a5a;
  flex: 0 0 auto;
}
.gt-name {
  font-size: 15px;
  font-weight: 700;
  color: #1b8a5a;
}
.gt-caption {
  font-size: 11px;
  color: #4a5361;
  opacity: 0.85;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  padding-top: 6px;
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
