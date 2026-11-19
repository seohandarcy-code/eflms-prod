<script setup lang="ts">
import { computed, nextTick, onMounted } from "vue";
import { useRoute } from "vue-router";
import FacilityFlowDiagram from "../components/FacilityFlowDiagram.vue";
import FacilityImage from "../components/FacilityImage.vue";
import GuideTabs from "../components/GuideTabs.vue";
import { useEquipmentStore } from "../stores/equipment";
import { countByType, FACILITY_INFO, facilityAnchor, pofHighlights, sortByFlow } from "../utils/facilityInfo";

// 설비 안내 페이지(/guide/facilities, Stage 17) — 전기설비를 잘 모르는 사용자를 위한 계통도·기능표·상세 설명.
// 설명 문구와 사진은 utils/facilityInfo.ts, 이름·감점 항목은 /api/equipment-types, 현황 숫자는
// 전체 사업장 기준 설비 목록(대시보드와 같은 스토어)에서 센다.
const store = useEquipmentStore();
const route = useRoute();

const counts = computed(() => countByType(store.allEquipment));
const hasCounts = computed(() => store.allEquipment.length > 0);

const facilities = computed(() =>
  sortByFlow(store.equipmentTypes.map((t) => t.ef_code)).map((code) => ({
    code,
    anchor: facilityAnchor(code),
    name: store.typeNames[code] ?? code,
    info: FACILITY_INFO[code] ?? null,
    count: counts.value[code] ?? { total: 0, needsInspection: 0 },
    checks: pofHighlights(store.breakdownFor(code).pof),
    dashboardLink: { path: "/", query: { type: code } },
  })),
);

// 처음 들어올 때 #ef7 같은 앵커가 있으면, 목록이 그려진 뒤에 그 위치로 스크롤한다
// (라우터 scrollBehavior가 도는 시점엔 아직 설비 목록을 받기 전일 수 있다).
async function scrollToHash() {
  if (!/^#[\w-]+$/.test(route.hash)) return;
  await nextTick();
  document.querySelector(route.hash)?.scrollIntoView({ block: "start" });
}

onMounted(async () => {
  if (store.allEquipment.length === 0) await store.load();
  else await store.loadTypes();
  await scrollToHash();
});
</script>

<template>
  <div class="guide">
    <GuideTabs />

    <main class="body">
      <section class="intro">
        <h1>반도체 공장의 전기는 이렇게 흐릅니다</h1>
        <p>
          한전에서 받은 154kV 전기는 땅속 케이블로 들어와, 개폐장치(GIS)를 거쳐 변압기에서 22.9kV로 낮춰지고, 수배전반이 공장 곳곳으로 나눠 보냅니다.
          멈추면 안 되는 장비 앞에는 정전에 대비한 UPS·배터리와 순간 전압 저하에 대비한 VDP가 있습니다. 이 시스템은 이 설비들의 상태를 점수로 관리합니다.
        </p>
      </section>

      <div v-if="store.error" class="error">{{ store.error }}</div>

      <section class="card">
        <h2>1. 전력설비 계통도</h2>
        <p class="caption">각 설비를 누르면 아래 상세 설명으로 이동합니다 · 설비 칸의 숫자는 지금 시스템 현황(전체 사업장)</p>
        <FacilityFlowDiagram :counts="counts" :type-names="store.typeNames" />
      </section>

      <section class="card">
        <h2>2. 설비별 주요 기능과 반도체 Fab에서의 역할</h2>
        <p class="caption">전기가 흐르는 순서대로 · "고장 나면"은 COF(고장영향성) 점수가 뜻하는 것</p>
        <div class="table-scroll">
          <table class="role-table">
            <thead>
              <tr>
                <th>설비</th>
                <th>계통 위치</th>
                <th>주요 기능</th>
                <th>Fab에서의 역할</th>
                <th>고장 나면</th>
                <th>현황</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in facilities" :key="f.code">
                <td>
                  <RouterLink :to="{ path: '/guide/facilities', hash: `#${f.anchor}` }" class="facility-cell">
                    <img v-if="f.info" :src="f.info.image" alt="" class="table-img" />
                    <span><b>{{ f.name }}</b><br /><span class="muted">{{ f.code }}</span></span>
                  </RouterLink>
                </td>
                <td class="nowrap">{{ f.info?.position ?? "-" }}</td>
                <td>{{ f.info?.role ?? "-" }}</td>
                <td>{{ f.info?.fabRole ?? "-" }}</td>
                <td>{{ f.info?.failure ?? "-" }}</td>
                <td class="nowrap">
                  <template v-if="hasCounts">
                    {{ f.count.total }}대 · <span :class="f.count.needsInspection > 0 ? 'warn' : 'ok'">점검 {{ f.count.needsInspection }}</span>
                  </template>
                  <template v-else>-</template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 class="section-title">3. 설비별 상세 설명</h2>
        <div class="detail-grid">
          <article v-for="f in facilities" :id="f.anchor" :key="f.code" class="detail-card">
            <FacilityImage v-if="f.info" class="detail-img" :info="f.info" :alt="`${f.name} 사진`" animated lazy />
            <div class="detail-body">
              <div class="detail-name">
                {{ f.name }} <span class="muted">{{ f.code }}<template v-if="f.info"> · {{ f.info.subtitle }}</template></span>
              </div>
              <template v-if="f.info">
                <p class="detail-overview">{{ f.info.overview }}</p>
                <div class="detail-line"><b>주요 구성</b> · {{ f.info.parts }}</div>
                <div class="detail-line"><b>노화·고장 원인</b> · {{ f.info.causes }}</div>
              </template>
              <div v-if="f.checks.labels.length > 0" class="detail-line muted-line">
                <b>이 시스템이 보는 항목</b> · {{ f.checks.labels.join(" · ") }}<template v-if="f.checks.rest > 0"> · 외 POF {{ f.checks.rest }}개</template>
              </div>
              <RouterLink :to="f.dashboardLink" class="detail-link">
                <template v-if="hasCounts">{{ f.count.total }}대 · 점검필요 {{ f.count.needsInspection }} — </template>대시보드에서 이 설비만 보기 →
              </RouterLink>
            </div>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.guide {
  min-height: 100vh;
  background: #f4f5f7;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  color: #1a2230;
  /* 한글은 띄어쓰기에서만 줄바꿈, 띄어쓰기 없는 긴 덩어리만 칸을 넘을 때 끊는다 */
  word-break: keep-all;
  overflow-wrap: anywhere;
}
.body {
  max-width: 1160px;
  margin: 0 auto;
  padding: 32px 24px 60px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.intro h1 {
  margin: 0 0 8px;
  font-size: 22px;
}
.intro p {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #4a5361;
  text-wrap: pretty;
}
.error {
  padding: 12px 16px;
  border-radius: 8px;
  background: #fcf1ef;
  color: #c4392b;
  font-size: 13px;
}
.card {
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 22px 24px;
}
h2,
.section-title {
  margin: 0;
  font-size: 16px;
}
.section-title {
  margin-bottom: 14px;
}
.caption {
  margin: 6px 0 16px;
  font-size: 12px;
  color: #8891a0;
}
.table-scroll {
  overflow-x: auto;
}
.role-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 860px;
}
.role-table th {
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #6b7482;
  background: #f7f8fa;
  padding: 10px 12px;
  border-bottom: 1px solid #e2e5ea;
}
.role-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #eef0f3;
  vertical-align: middle;
  line-height: 1.5;
}
.role-table tr:last-child td {
  border-bottom: none;
}
.facility-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  color: inherit;
  text-decoration: none;
  white-space: nowrap;
}
.table-img {
  width: 54px;
  height: 40px;
  object-fit: contain;
  border-radius: 4px;
  background: #f3f5fb;
}
.muted {
  font-size: 11px;
  font-weight: 600;
  color: #8891a0;
}
.nowrap {
  white-space: nowrap;
}
.warn {
  color: #a8590a;
  font-weight: 600;
}
.ok {
  color: #0b6f6f;
  font-weight: 600;
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 520px), 1fr));
  gap: 16px;
}
.detail-card {
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  gap: 18px;
  scroll-margin-top: 16px;
}
.detail-card:target {
  border-color: #0f8a8a;
  box-shadow: 0 0 0 3px rgba(15, 138, 138, 0.15);
}
.detail-img {
  flex: 0 0 auto;
  width: 176px;
  height: 130px;
  object-fit: contain;
  border-radius: 8px;
  background: #f3f5fb;
  border: 1px solid #e2e5ea;
}
.detail-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.detail-name {
  font-size: 17px;
  font-weight: 700;
}
.detail-overview {
  margin: 0;
  font-size: 13px;
  color: #4a5361;
  line-height: 1.65;
}
.detail-line {
  font-size: 12px;
  line-height: 1.6;
}
.muted-line {
  color: #4a5361;
}
.detail-link {
  margin-top: 2px;
  font-size: 12px;
  font-weight: 600;
  color: #0b6f6f;
  text-decoration: none;
}
.detail-link:hover {
  text-decoration: underline;
}
@media (max-width: 640px) {
  .detail-card {
    flex-direction: column;
  }
  .detail-img {
    width: 100%;
    height: auto;
    aspect-ratio: 496 / 366;
  }
}
</style>
