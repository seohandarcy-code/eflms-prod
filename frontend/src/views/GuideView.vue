<script setup lang="ts">
import { nextTick, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useEquipmentStore } from "../stores/equipment";
import type { Axis, BreakdownItem } from "../types/equipment";
import { statusColor, statusLabel } from "../utils/statusStyle";
import { TYPE_GUIDES } from "../utils/typeGuide";
import GuideTabs from "../components/GuideTabs.vue";

// 지표 설명 페이지(/guide). 글자 크기·폭·카드 모양은 설비 안내(FacilityGuideView.vue)와 같은 양식을 쓴다.
// 구성 항목은 설비유형별 감점 메타데이터(/api/equipment-types)를 그대로 보여준다(Stage 8-5).
// 유형별 계산 방법 설명은 utils/typeGuide.ts — 없는 유형은 항목 목록만 나온다.
const store = useEquipmentStore();
const route = useRoute();

const AXIS_TITLES: Record<Axis, string> = { pof: "POF 구성 항목", cof: "COF 구성 항목", dof: "DOF 구성 항목" };
const AXES: Axis[] = ["pof", "cof", "dof"];

// 그룹(예: GIS PoF의 기계적/전기적/화학적)이 있으면 그룹별로 묶는다. 그룹이 없으면 한 덩어리.
function groupItems(items: BreakdownItem[]): { group: string | null; items: BreakdownItem[] }[] {
  const groups: { group: string | null; items: BreakdownItem[] }[] = [];
  for (const item of items) {
    const last = groups[groups.length - 1];
    if (last && last.group === item.group) last.items.push(item);
    else groups.push({ group: item.group, items: [item] });
  }
  return groups;
}

// typeGuide.ts의 수식 문자열은 여러 식을 공백 3칸 이상으로 이어 둔다 — 화면에서는 한 줄에 한 식씩 보여준다.
function exprLines(expr: string): string[] {
  return expr.split(/\s{3,}/).filter((line) => line.length > 0);
}

function typeAnchor(efCode: string): string {
  return efCode.toLowerCase();
}

// #ef3 같은 앵커로 처음 들어오면, 유형 목록을 받은 뒤 그 위치로 스크롤한다(설비 안내와 같은 방식).
onMounted(async () => {
  await store.loadTypes();
  if (!/^#[\w-]+$/.test(route.hash)) return;
  await nextTick();
  document.querySelector(route.hash)?.scrollIntoView({ block: "start" });
});
</script>

<template>
  <div class="guide">
    <GuideTabs />

    <main class="body">
      <section class="intro">
        <h1>설비 점수는 이렇게 매겨집니다</h1>
        <p>
          EFLMS는 설비 하나마다 POF·COF·DOF 세 가지 축으로 건전성을 평가합니다. 각 축은 100점에서 기준에 못 미친 항목의 감점을 뺀 값이고,
          세 축을 가중합한 종합점수와 판정 기준으로 정상·교체검토·즉시교체를 나눕니다.
        </p>
      </section>

      <section class="card">
        <h2>1. 세 가지 평가 축</h2>
        <p class="caption">각 축은 0~100점 · 100에서 감점 항목들을 뺀 값</p>
        <div class="axis-cards">
          <div class="axis-card">
            <div class="axis-name">POF</div>
            <div class="axis-full">설비상태 (Probability of Failure)</div>
            <p>설비 자체의 상태·진단 결과를 바탕으로, 이 설비가 실제로 고장날 가능성이 얼마나 되는지를 나타냅니다. 변압기는 Furan·부분방전·절연내력 시험 등, GIS는 차단기 동작이력·SF6 가스·부분방전 등 설비유형마다 다른 진단 결과가 반영됩니다(아래 "4. 설비유형별 계산 방법").</p>
          </div>
          <div class="axis-card">
            <div class="axis-name">COF</div>
            <div class="axis-full">고장영향성 (Consequence of Failure)</div>
            <p>이 설비가 실제로 고장 났을 때 파급되는 영향의 크기입니다. 전압·용량이 클수록, 화재 확산 위험이 크거나 비상대응·교체에 시간과 비용이 많이 들수록 영향이 큰 것으로 평가됩니다.</p>
          </div>
          <div class="axis-card">
            <div class="axis-name">DOF</div>
            <div class="axis-full">고장예방력 (Defense of Failure)</div>
            <p>고장이 나더라도 피해를 줄여줄 예비 설비·보호 장치가 얼마나 갖춰져 있는지입니다. 예비화·자동전환, 상시 감시와 정기 점검, 설계 강화 여부 등이 반영됩니다(설비유형별 항목은 아래).</p>
          </div>
        </div>
      </section>

      <section class="card">
        <h2>2. 종합점수 계산</h2>
        <p class="caption">모든 설비유형에 같은 비율 — 유형이 달라도 종합점수로 함께 비교할 수 있습니다</p>
        <p class="lead">세 축의 점수를 아래 비율로 가중합해 종합점수를 만듭니다 — POF의 비중이 가장 크고, DOF가 가장 작습니다.</p>
        <div class="formula formula-main">종합점수 = 0.5 × POF + 0.3 × COF + 0.2 × DOF</div>
        <p class="lead lead-after">입력 데이터에 값이 없어 <b>N/A</b>로 들어온 항목은 평가하지 않습니다 — 그 항목의 감점은 0이고, 상세 화면에는 값이 "N/A"로 표시됩니다. 따라서 N/A가 많은 설비는 실제보다 점수가 높게 보일 수 있습니다.</p>
      </section>

      <section class="card">
        <h2>3. 정상 / 교체검토 / 즉시교체 판정 기준</h2>
        <p class="caption">모든 설비유형에 같은 기준</p>
        <p class="lead">COF·DOF가 둘 다 60을 넘으면(다른 방어 수단이 충분하면) POF 기준이 완화되고, 그렇지 않으면 더 엄격한 기준이 적용됩니다.</p>
        <div class="table-scroll">
          <table class="rule-table">
            <thead>
              <tr>
                <th>조건</th>
                <th :style="{ color: statusColor('normal') }">{{ statusLabel("normal") }}</th>
                <th :style="{ color: statusColor('review') }">{{ statusLabel("review") }}</th>
                <th :style="{ color: statusColor('replace') }">{{ statusLabel("replace") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>COF &gt; 60 <b>그리고</b> DOF &gt; 60</td>
                <td>POF &gt; 50</td>
                <td>30 ≤ POF ≤ 50</td>
                <td>POF &lt; 30</td>
              </tr>
              <tr>
                <td>COF ≤ 60 <b>또는</b> DOF ≤ 60</td>
                <td>POF &gt; 60</td>
                <td>40 ≤ POF ≤ 60</td>
                <td>POF &lt; 40</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="type-section">
        <h2 class="section-title">4. 설비유형별 계산 방법과 구성 항목</h2>
        <p class="caption">
          아래 항목에서 기준 미달이 있으면 해당 축에서 감점됩니다 · 대시보드 "점검필요 순위"에서 항목에 마우스를 올리면 그 설비의 실제 측정값을 볼 수 있습니다
        </p>
        <nav v-if="store.equipmentTypes.length > 0" class="type-jump" aria-label="설비유형 바로가기">
          <RouterLink
            v-for="info in store.equipmentTypes"
            :key="info.ef_code"
            :to="{ path: '/guide', hash: `#${typeAnchor(info.ef_code)}` }"
            class="type-chip"
          >
            <b>{{ info.ef_code }}</b> {{ info.ef_name }}
          </RouterLink>
        </nav>

        <div class="type-list">
          <article v-for="info in store.equipmentTypes" :id="typeAnchor(info.ef_code)" :key="info.ef_code" class="card type-card">
            <h3>{{ info.ef_name }} <span class="muted">{{ info.ef_code }}</span></h3>
            <div class="axis-cards">
              <div v-for="axis in AXES" :key="axis" class="axis-card">
                <div class="axis-name">{{ AXIS_TITLES[axis] }}</div>
                <div v-if="TYPE_GUIDES[info.ef_code]" class="axis-desc">
                  <div class="axis-formula">{{ TYPE_GUIDES[info.ef_code].axes[axis][0] }}</div>
                  <p v-for="(line, i) in TYPE_GUIDES[info.ef_code].axes[axis].slice(1)" :key="i">{{ line }}</p>
                </div>
                <template v-for="block in groupItems(info.breakdown[axis])" :key="block.group ?? 'all'">
                  <div v-if="block.group" class="axis-group">{{ block.group }}</div>
                  <ul>
                    <li v-for="item in block.items" :key="item.field">{{ item.label }}</li>
                  </ul>
                </template>
              </div>
            </div>
            <div v-if="TYPE_GUIDES[info.ef_code]?.formulas" class="type-formulas">
              <div v-for="f in TYPE_GUIDES[info.ef_code].formulas" :key="f.label" class="type-formula">
                <div class="type-formula-label">{{ f.label }}</div>
                <div class="formula">
                  <div v-for="(line, i) in exprLines(f.expr)" :key="i" class="formula-line">{{ line }}</div>
                </div>
                <div v-if="f.note" class="type-formula-note">{{ f.note }}</div>
              </div>
            </div>
            <ul v-if="TYPE_GUIDES[info.ef_code]?.notes" class="type-notes">
              <li v-for="(n, i) in TYPE_GUIDES[info.ef_code].notes" :key="i">{{ n }}</li>
            </ul>
          </article>
          <div v-if="store.equipmentTypes.length === 0" class="card">
            <p class="lead">설비유형 정보를 불러오는 중입니다...</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
/* 설비 안내(FacilityGuideView.vue)와 같은 양식: 폭 1160, 카드 22·24, 제목 16, 본문 13, 보조 12 */
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
.card {
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 22px 24px;
  min-width: 0;
}
h2,
.section-title {
  margin: 0;
  font-size: 16px;
}
.section-title {
  margin-bottom: 6px;
}
.caption {
  margin: 6px 0 16px;
  font-size: 12px;
  color: #8891a0;
  line-height: 1.6;
}
.lead {
  font-size: 13px;
  color: #4a5361;
  line-height: 1.65;
  margin: 0 0 14px;
}
.lead-after {
  margin: 14px 0 0;
}
.muted {
  font-size: 12px;
  font-weight: 600;
  color: #8891a0;
}
.axis-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
  gap: 14px;
}
.axis-card {
  background: #f9fafb;
  border: 1px solid #eef0f3;
  border-radius: 8px;
  padding: 16px;
  min-width: 0;
}
.axis-name {
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 2px;
}
.axis-full {
  font-size: 12px;
  color: #8891a0;
  margin-bottom: 8px;
}
.axis-card p {
  font-size: 13px;
  color: #4a5361;
  line-height: 1.65;
  margin: 0;
}
.axis-card ul {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #4a5361;
  line-height: 1.75;
}
/* 수식: 불러오지 않는 고정폭 글꼴 대신 본문 글꼴 + 숫자 폭만 고르게. 카드 폭을 넘지 않고 줄바꿈한다. */
.formula,
.axis-formula {
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}
.formula {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.6;
  color: #1a2230;
  background: #f9fafb;
  border: 1px solid #eef0f3;
  border-radius: 8px;
  padding: 12px 16px;
}
.formula-main {
  font-size: 15px;
  font-weight: 600;
  padding: 14px 18px;
}
.formula-line + .formula-line {
  margin-top: 4px;
}
.table-scroll {
  overflow-x: auto;
}
.rule-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 520px;
}
.rule-table th {
  text-align: left;
  font-size: 12px;
  font-weight: 700;
  background: #f7f8fa;
  padding: 10px 12px;
  border-bottom: 1px solid #e2e5ea;
}
.rule-table th:first-child {
  color: #6b7482;
  font-weight: 600;
}
.rule-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #eef0f3;
  line-height: 1.5;
}
.rule-table tr:last-child td {
  border-bottom: none;
}
.type-jump {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.type-chip {
  font-size: 13px;
  color: #1a2230;
  text-decoration: none;
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 999px;
  padding: 6px 14px;
}
.type-chip b {
  color: #0b6f6f;
  margin-right: 2px;
}
.type-chip:hover {
  border-color: #0f8a8a;
}
.type-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.type-card {
  scroll-margin-top: 16px;
}
.type-card:target {
  border-color: #0f8a8a;
  box-shadow: 0 0 0 3px rgba(15, 138, 138, 0.15);
}
.type-card h3 {
  margin: 0 0 14px;
  font-size: 17px;
}
.axis-desc {
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px dashed #e2e5ea;
}
.axis-formula {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.55;
  color: #1a2230;
  margin-bottom: 6px;
}
.axis-desc p + p {
  margin-top: 4px;
}
.type-formulas {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
  margin-top: 16px;
}
.type-formula {
  min-width: 0;
}
.type-formula-label {
  font-size: 13px;
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 6px;
}
.type-formula-note {
  font-size: 12px;
  color: #8891a0;
  line-height: 1.6;
  margin-top: 6px;
}
.type-notes {
  margin: 14px 0 0;
  padding-left: 18px;
  font-size: 12px;
  color: #4a5361;
  line-height: 1.7;
}
.axis-group {
  font-size: 12px;
  font-weight: 600;
  color: #4a5568;
  margin-top: 8px;
}
@media (max-width: 640px) {
  .card {
    padding: 18px 16px;
  }
}
</style>
