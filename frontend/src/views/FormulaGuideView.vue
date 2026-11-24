<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchFormulaDocs } from "../api/equipment";
import GuideTabs from "../components/GuideTabs.vue";
import MathTex from "../components/MathTex.vue";
import { useEquipmentStore } from "../stores/equipment";
import type { FormulaDocs, FormulaItem } from "../types/equipment";
import { KIND_LABELS, axisTex, formatMinus, mapRows, stepRows } from "../utils/formulaDocs";

// 지표설명 상세 — 계산식(/guide/formulas?type=EF3, Stage 22-11). 감점 항목마다 수식·구간표·등급표를 보여준다.
// 내용은 백엔드 FORMULA_DOCS(실제 계산과 같은지 테스트로 확인)에서 받는다. 양식은 지표 설명(GuideView)과 같다.
const store = useEquipmentStore();
const route = useRoute();
const router = useRouter();

const cache = ref<Record<string, FormulaDocs>>({});
const loading = ref(false);
const errorMsg = ref("");

const selected = computed(() => {
  const q = typeof route.query.type === "string" ? route.query.type.toUpperCase() : "";
  const codes = store.equipmentTypes.map((t) => t.ef_code);
  return codes.includes(q) ? q : (codes[0] ?? "");
});
const docs = computed(() => cache.value[selected.value] ?? null);

function selectType(code: string) {
  router.replace({ query: { ...route.query, type: code } });
}

async function load(code: string) {
  if (!code || cache.value[code]) return;
  loading.value = true;
  errorMsg.value = "";
  try {
    cache.value = { ...cache.value, [code]: await fetchFormulaDocs(code) };
  } catch {
    errorMsg.value = "계산식을 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
}

watch(selected, (code) => load(code));
onMounted(async () => {
  await store.loadTypes();
  await load(selected.value);
});

function anchor(field: string): string {
  return `f-${field}`;
}

function jumpTo(field: string) {
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  document.getElementById(anchor(field))?.scrollIntoView({ block: "start", behavior: reduceMotion ? "auto" : "smooth" });
}

// 그룹(EF2 기계적/전기적/화학적)이 바뀌는 첫 항목 앞에 소제목을 단다.
function groupStart(items: FormulaItem[], i: number): string | null {
  const g = items[i].group;
  return g && (i === 0 || items[i - 1].group !== g) ? g : null;
}
</script>

<template>
  <div class="guide">
    <GuideTabs />

    <main class="body">
      <section class="intro">
        <h1>감점 항목 계산식</h1>
        <p>
          설비유형마다 POF·COF·DOF 각 항목이 어떤 값으로 어떻게 감점되는지 정리했습니다. 구간표·등급표는 실제 계산 코드와 같은지
          자동으로 확인한 값이며, 수식 항목의 예시도 시스템이 계산한 결과입니다.
        </p>
      </section>

      <nav v-if="store.equipmentTypes.length > 0" class="type-tabs" role="tablist" aria-label="설비유형">
        <button
          v-for="info in store.equipmentTypes"
          :key="info.ef_code"
          type="button"
          role="tab"
          class="type-tab"
          :class="{ active: info.ef_code === selected }"
          :aria-selected="info.ef_code === selected"
          @click="selectType(info.ef_code)"
        >
          <b>{{ info.ef_code }}</b> {{ info.ef_name }}
        </button>
      </nav>

      <div v-if="errorMsg" class="card"><p class="lead">{{ errorMsg }}</p></div>
      <div v-else-if="!docs" class="card"><p class="lead">계산식을 불러오는 중입니다...</p></div>

      <template v-else>
        <section class="card summary">
          <h2>{{ docs.ef_name }} <span class="muted">{{ docs.ef_code }}</span></h2>
          <div class="formula formula-main"><MathTex :tex="docs.total_tex" /></div>
          <ul class="rules">
            <li v-for="(rule, i) in docs.common_rules" :key="i">{{ rule }}</li>
          </ul>
        </section>

        <div v-if="!docs.documented" class="card">
          <p class="lead">
            이 유형의 항목별 계산식은 준비 중입니다. 구성 항목과 요약 설명은
            <RouterLink :to="{ path: '/guide', hash: `#${docs.ef_code.toLowerCase()}` }">지표 설명</RouterLink>에서 볼 수 있습니다.
          </p>
        </div>

        <section v-for="axis in docs.documented ? docs.axes : []" :key="axis.axis" class="axis-section">
          <div class="axis-head">
            <h2>{{ axis.label }}</h2>
            <div class="formula axis-eq"><MathTex :tex="axisTex(axis.axis)" /></div>
            <nav class="item-chips" :aria-label="`${axis.label} 항목 바로가기`">
              <button v-for="item in axis.items" :key="item.field" type="button" class="item-chip" @click="jumpTo(item.field)">
                {{ item.label }}
              </button>
            </nav>
          </div>

          <template v-for="(item, i) in axis.items" :key="item.field">
            <div v-if="groupStart(axis.items, i)" class="group-title">{{ groupStart(axis.items, i) }}</div>
            <article :id="anchor(item.field)" class="card item-card">
              <header class="item-head">
                <h3>{{ item.label }}</h3>
                <span class="kind" :class="`kind-${item.kind}`">{{ KIND_LABELS[item.kind] }}</span>
                <span v-if="!item.summed" class="kind kind-off">합산 안 함(참고용)</span>
              </header>
              <div class="inputs">
                입력:
                <span v-for="(inp, k) in item.inputs" :key="inp.name">
                  {{ inp.label }} <code>{{ inp.name }}</code><template v-if="k < item.inputs.length - 1"> · </template>
                </span>
              </div>

              <!-- 수식 -->
              <template v-if="item.kind === 'expr'">
                <div class="formula">
                  <MathTex v-for="(tex, k) in item.tex" :key="k" :tex="tex" />
                </div>
                <div v-if="item.table" class="table-scroll">
                  <table class="rule-table criteria">
                    <thead><tr><th v-for="col in item.table.columns" :key="col">{{ col }}</th></tr></thead>
                    <tbody>
                      <tr v-for="(row, r) in item.table.rows" :key="r">
                        <td v-for="(cell, c) in row" :key="c" :class="{ blank: cell === '' }">{{ cell === "" ? "–" : cell }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="item.symbols.length" class="table-scroll">
                  <table class="rule-table narrow">
                    <thead><tr><th>기호</th><th>뜻</th></tr></thead>
                    <tbody>
                      <tr v-for="s in item.symbols" :key="s.sym"><td class="sym">{{ s.sym }}</td><td>{{ s.label }}</td></tr>
                    </tbody>
                  </table>
                </div>
                <ul v-if="item.examples.length" class="examples">
                  <li v-for="ex in item.examples" :key="ex.text">예) {{ ex.text }}</li>
                </ul>
              </template>

              <!-- 구간표 -->
              <template v-else-if="item.kind === 'steps'">
                <div v-if="item.tex" class="formula"><MathTex :tex="item.tex" /></div>
                <div class="table-scroll">
                  <table class="rule-table narrow">
                    <thead><tr><th>{{ item.var_label }}</th><th class="num">감점</th></tr></thead>
                    <tbody>
                      <tr v-for="row in stepRows(item)" :key="row.cond">
                        <td>{{ row.cond }}</td>
                        <td class="num" :class="{ zero: row.minus === 0 }">{{ formatMinus(row.minus) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>

              <!-- 등급표 / 1·2 중 나쁜 값 -->
              <template v-else>
                <div v-if="item.kind === 'worse'" class="formula">
                  <MathTex :tex="`\\text{감점} = \\min\\big(\\text{감점}(\\text{${item.inputs[0].label}}),\\ \\text{감점}(\\text{${item.inputs[1].label}})\\big)`" />
                </div>
                <div class="table-scroll">
                  <table class="rule-table narrow">
                    <thead><tr><th>{{ item.kind === "worse" ? "값(1·2 공통)" : item.inputs[0].label }}</th><th class="num">감점</th></tr></thead>
                    <tbody>
                      <tr v-for="row in mapRows(item)" :key="row.value">
                        <td>{{ row.value }}</td>
                        <td class="num" :class="{ zero: row.minus === 0 }">{{ formatMinus(row.minus) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>

              <p v-if="item.note" class="note">{{ item.note }}</p>
            </article>
          </template>
        </section>
      </template>
      <p v-if="loading && docs" class="caption">불러오는 중...</p>
    </main>
  </div>
</template>

<style scoped>
/* 지표 설명(GuideView.vue)과 같은 양식: 폭 1160, 카드 22·24, 제목 16, 본문 13, 보조 12 */
.guide {
  min-height: 100vh;
  background: #f4f5f7;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  color: #1a2230;
  word-break: keep-all;
  overflow-wrap: anywhere;
}
.body {
  max-width: 1160px;
  margin: 0 auto;
  padding: 32px 24px 60px;
  display: flex;
  flex-direction: column;
  gap: 16px;
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
h2 {
  margin: 0;
  font-size: 16px;
}
.muted {
  font-size: 12px;
  font-weight: 600;
  color: #8891a0;
}
.lead {
  font-size: 13px;
  color: #4a5361;
  line-height: 1.65;
  margin: 0;
}
.caption {
  font-size: 12px;
  color: #8891a0;
  margin: 0;
}
.type-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.type-tab {
  font: inherit;
  font-size: 13px;
  color: #1a2230;
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 999px;
  padding: 7px 15px;
  cursor: pointer;
}
.type-tab b {
  color: #0b6f6f;
  margin-right: 2px;
}
.type-tab:hover {
  border-color: #0f8a8a;
}
.type-tab.active {
  background: #0f8a8a;
  border-color: #0f8a8a;
  color: #fff;
}
.type-tab.active b {
  color: #fff;
}
.type-tab:focus-visible,
.item-chip:focus-visible {
  outline: 2px solid #0f8a8a;
  outline-offset: 2px;
}
.summary h2 {
  margin-bottom: 12px;
}
.formula {
  background: #f9fafb;
  border: 1px solid #eef0f3;
  border-radius: 8px;
  padding: 10px 16px;
  margin-top: 10px;
  color: #1a2230;
}
.formula-main {
  padding: 14px 18px;
  font-size: 15px;
}
.rules {
  margin: 14px 0 0;
  padding-left: 18px;
  font-size: 12px;
  color: #4a5361;
  line-height: 1.75;
}
.axis-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
}
.axis-head {
  background: #e6f3f3;
  border: 1px solid #cfe7e7;
  border-radius: 10px;
  padding: 18px 22px;
}
.axis-head h2 {
  color: #0b6f6f;
}
.axis-eq {
  background: #fff;
  border-color: #cfe7e7;
}
.item-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}
.item-chip {
  font: inherit;
  font-size: 12px;
  color: #1a2230;
  background: #fff;
  border: 1px solid #cfe7e7;
  border-radius: 999px;
  padding: 4px 11px;
  cursor: pointer;
}
.item-chip:hover {
  border-color: #0f8a8a;
}
.group-title {
  font-size: 13px;
  font-weight: 700;
  color: #4a5568;
  margin: 4px 0 -2px 2px;
}
.item-card {
  scroll-margin-top: 16px;
}
.item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.item-head h3 {
  margin: 0;
  font-size: 15px;
}
.kind {
  font-size: 11px;
  font-weight: 600;
  border-radius: 999px;
  padding: 2px 9px;
  background: #f1f2f4;
  color: #4a5361;
}
.kind-expr {
  background: #eef2ff;
  color: #3b4bb5;
}
.kind-steps {
  background: #fff4e5;
  color: #9a5b00;
}
.kind-map,
.kind-worse {
  background: #e6f3f3;
  color: #0b6f6f;
}
.kind-off {
  background: #f4f5f7;
  color: #8891a0;
}
.inputs {
  font-size: 12px;
  color: #6b7482;
  margin-top: 6px;
  line-height: 1.7;
}
.inputs code {
  font-size: 11px;
  color: #8891a0;
  background: #f4f5f7;
  border-radius: 4px;
  padding: 1px 5px;
}
.table-scroll {
  overflow-x: auto;
  margin-top: 10px;
}
.rule-table {
  border-collapse: collapse;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}
.rule-table.narrow {
  min-width: 260px;
  width: auto;
}
.rule-table th {
  text-align: left;
  font-size: 12px;
  font-weight: 700;
  background: #f7f8fa;
  padding: 8px 14px;
  border-bottom: 1px solid #e2e5ea;
}
.rule-table td {
  padding: 8px 14px;
  border-bottom: 1px solid #eef0f3;
  line-height: 1.5;
}
.rule-table tr:last-child td {
  border-bottom: none;
}
.rule-table .num {
  text-align: right;
  min-width: 64px;
  font-weight: 600;
  color: #c0392b;
}
.rule-table th.num {
  color: inherit;
}
.rule-table.criteria {
  min-width: 320px;
}
.rule-table.criteria td:first-child {
  font-weight: 600;
  white-space: nowrap;
}
.rule-table td.blank {
  color: #c4c9d1;
}
.rule-table .num.zero {
  color: #8891a0;
  font-weight: 500;
}
.sym {
  white-space: nowrap;
  font-weight: 600;
}
.examples {
  margin: 10px 0 0;
  padding-left: 18px;
  font-size: 13px;
  color: #1a2230;
  line-height: 1.7;
}
.note {
  font-size: 12px;
  color: #6b7482;
  line-height: 1.6;
  margin: 10px 0 0;
}
@media (max-width: 640px) {
  .body {
    padding: 24px 16px 48px;
  }
  .card {
    padding: 18px 16px;
  }
  .axis-head {
    padding: 16px;
  }
}
</style>
