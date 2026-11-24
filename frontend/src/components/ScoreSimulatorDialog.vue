<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import {
  calculateSimulation,
  fetchSimulatorForm,
  fetchSimulatorSample,
  type SimulatorColumn,
  type SimulatorForm,
  type SimulatorResult,
} from "../api/simulator";
import { AXIS_NAME, formatScore, typeLabel } from "../utils/formatValue";
import { statusBg, statusColor, statusLabel } from "../utils/statusStyle";
import {
  NA,
  blankValues,
  changedFields,
  deltaLabel,
  dtypeLabel,
  errorsByField,
  ruleLabel,
  topDeductions,
} from "../utils/simulator";

// 점수 시뮬레이터 팝업(Stage 19, 시안 A — 왼쪽 입력 | 오른쪽 결과). 계산은 "계산하기"를 눌렀을 때만,
// DB에는 저장하지 않는다. 입력 양식·값 검사는 관리자 데이터 입력과 같은 규칙(백엔드 simulator_service).
// 사업장은 DB에 그 유형 설비가 있는 곳만, EF7은 방전이력이 있는 사업장만 고를 수 있다.
const props = defineProps<{
  open: boolean;
  types: { ef_code: string; ef_name: string }[];
  initialType?: string | null;
}>();
const emit = defineEmits<{ close: [] }>();

type StartMode = "example" | "equipment" | "blank";

const efCode = ref("");
const form = ref<SimulatorForm | null>(null);
const startMode = ref<StartMode>("example");
const equipmentId = ref<number | null>(null);
const values = ref<Record<string, string>>({});
const start = ref<Record<string, string>>({});
const baseline = ref<SimulatorResult | null>(null);
const result = ref<SimulatorResult | null>(null);
const calcValues = ref<Record<string, string> | null>(null);
const view = ref<"result" | "template">("result");
const loading = ref(false);
const calculating = ref(false);
const loadError = ref("");
const dialogEl = ref<HTMLElement | null>(null);

const columns = computed<SimulatorColumn[]>(() => form.value?.columns ?? []);
const changed = computed(() => new Set(changedFields(values.value, start.value)));
const errors = computed(() => errorsByField(result.value && !result.value.ok ? result.value : null));
const noSites = computed(() => form.value !== null && form.value.sites.length === 0);
const stale = computed(
  () => calcValues.value !== null && changedFields(values.value, calcValues.value).length > 0,
);
/** 오른쪽에 보여줄 결과 — 계산한 적이 없으면 시작값의 결과 */
const shown = computed<SimulatorResult | null>(() => {
  if (result.value?.ok) return result.value;
  if (result.value === null && baseline.value?.ok) return baseline.value;
  return null;
});
const compare = computed(() => (result.value?.ok && baseline.value?.ok ? baseline.value : null));
const deductions = computed(() => (shown.value ? topDeductions(shown.value) : []));
const siteNote = computed(() => {
  const f = form.value;
  if (!f || f.excluded_sites.length === 0) return "";
  const ok = f.sites.map((s) => s.factory_code).join(", ") || "없음";
  return `참고표에 데이터가 있는 사업장만 계산할 수 있습니다 (지금: ${ok}) · 제외: ${f.excluded_sites
    .map((s) => s.factory_code)
    .join(", ")}`;
});
const statusText = computed(() => {
  if (calculating.value) return "계산 중…";
  if (result.value && !result.value.ok) return `입력값 오류 ${result.value.errors.length}건 — 빨간 칸을 고친 뒤 다시 계산하기`;
  if (stale.value) return "값이 바뀌었습니다 — 계산하기를 눌러 주세요";
  if (result.value?.ok) return "계산 완료";
  return "값을 바꾸고 계산하기를 누르면 바뀐 점수를 보여줍니다";
});

const AXES = [
  { key: "pof", label: "POF", full: AXIS_NAME.pof },
  { key: "cof", label: "COF", full: AXIS_NAME.cof },
  { key: "dof", label: "DOF", full: AXIS_NAME.dof },
] as const;

function axisValue(r: SimulatorResult | null, key: "pof" | "cof" | "dof"): number | null {
  return r ? r[key] : null;
}

function barStyle(value: number | null) {
  const pct = value == null ? 0 : Math.max(0, Math.min(100, value));
  return { width: `${pct}%` };
}

function setValues(next: Record<string, string>, base: SimulatorResult | null) {
  values.value = { ...next };
  start.value = { ...next };
  baseline.value = base;
  result.value = null;
  calcValues.value = null;
}

async function loadSample() {
  if (!form.value) return;
  if (startMode.value === "blank") {
    setValues(blankValues(columns.value, { ...values.value, EF_code: efCode.value }), null);
    return;
  }
  if (startMode.value === "equipment" && equipmentId.value === null) return;
  loading.value = true;
  loadError.value = "";
  try {
    const sample = await fetchSimulatorSample(efCode.value, startMode.value === "equipment" ? equipmentId.value : null);
    setValues(sample.values, sample.baseline);
  } catch {
    loadError.value = "시작값을 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
}

async function loadForm() {
  if (!efCode.value) return;
  loading.value = true;
  loadError.value = "";
  form.value = null;
  try {
    const f = await fetchSimulatorForm(efCode.value);
    form.value = f;
    equipmentId.value = f.equipment[0]?.equipment_id ?? null;
    if (startMode.value === "equipment" && equipmentId.value === null) startMode.value = "example";
    if (f.sites.length === 0) {
      setValues(blankValues(f.columns, { EF_code: efCode.value }), null);
      return;
    }
  } catch {
    loadError.value = "입력 양식을 불러오지 못했습니다.";
    return;
  } finally {
    loading.value = false;
  }
  await loadSample();
}

async function calculate() {
  if (!form.value || noSites.value || calculating.value) return;
  calculating.value = true;
  const snapshot = { ...values.value };
  try {
    result.value = await calculateSimulation(efCode.value, snapshot);
    calcValues.value = snapshot;
    view.value = "result";
  } catch {
    loadError.value = "계산 요청에 실패했습니다.";
  } finally {
    calculating.value = false;
  }
}

function resetValues() {
  values.value = { ...start.value };
}

function pickStart(mode: StartMode) {
  if (mode === "equipment" && (form.value?.equipment.length ?? 0) === 0) return;
  startMode.value = mode;
  void loadSample();
}

function close() {
  emit("close");
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") close();
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      document.addEventListener("keydown", onKeydown);
      const first = props.types[0]?.ef_code ?? "";
      const wanted = props.initialType && props.types.some((t) => t.ef_code === props.initialType) ? props.initialType : first;
      view.value = "result";
      if (efCode.value !== wanted) {
        efCode.value = wanted; // watch(efCode)가 양식을 불러온다
      } else if (form.value === null) {
        await loadForm();
      } else {
        await loadSample();
      }
      await nextTick();
      dialogEl.value?.focus();
    } else {
      document.removeEventListener("keydown", onKeydown);
    }
  },
  { immediate: true },
);
watch(efCode, () => void loadForm());
onBeforeUnmount(() => document.removeEventListener("keydown", onKeydown));

function columnLabel(name: string): string {
  return columns.value.find((c) => c.name === name)?.label || name;
}

function inputKind(col: SimulatorColumn): "site" | "fixed" | "choice" | "date" | "text" {
  if (col.name === "factory_code") return "site";
  if (col.name === "EF_code") return "fixed";
  if (col.choices && col.choices.length > 0) return "choice";
  if (col.dtype === "date" && !col.na_allowed) return "date";
  return "text";
}

function placeholder(col: SimulatorColumn): string {
  const base = { int: "정수", float: "숫자", date: "YYYY-MM-DD", str: "글자" }[col.dtype] ?? "";
  return col.na_allowed ? `${base} 또는 N/A` : base;
}

function fieldClass(name: string) {
  return { "sim-chg": changed.value.has(name), "sim-err": name in errors.value };
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="sim-backdrop" @click.self="close">
      <section ref="dialogEl" class="sim" role="dialog" aria-modal="true" aria-labelledby="sim-title" tabindex="-1">
        <header class="sim-head">
          <div>
            <h2 id="sim-title">시뮬레이터</h2>
            <p>입력값을 바꾸고 계산하기를 누르면 POF·COF·DOF와 종합점수를 계산합니다 · DB에는 저장되지 않습니다</p>
          </div>
          <button type="button" class="sim-x" aria-label="닫기" @click="close">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
              <line x1="6" y1="6" x2="18" y2="18" />
              <line x1="18" y1="6" x2="6" y2="18" />
            </svg>
          </button>
        </header>

        <div class="sim-bar">
          <label class="sim-fld sim-type">
            <span class="sim-lab">설비유형</span>
            <select v-model="efCode" class="sim-box">
              <option v-for="t in types" :key="t.ef_code" :value="t.ef_code">{{ typeLabel(t.ef_name, t.ef_code) }}</option>
            </select>
          </label>
          <div class="sim-fld">
            <span class="sim-lab">시작값</span>
            <div class="sim-seg" role="group" aria-label="시작값">
              <button type="button" :class="{ on: startMode === 'example' }" :disabled="noSites" @click="pickStart('example')">예시값</button>
              <button
                type="button"
                :class="{ on: startMode === 'equipment' }"
                :disabled="noSites || (form?.equipment.length ?? 0) === 0"
                @click="pickStart('equipment')"
              >
                기존 설비
              </button>
              <button type="button" :class="{ on: startMode === 'blank' }" @click="pickStart('blank')">모두 비우기</button>
            </div>
          </div>
          <label class="sim-fld sim-eq">
            <span class="sim-lab">불러올 설비</span>
            <select v-model="equipmentId" class="sim-box" :disabled="startMode !== 'equipment'" @change="loadSample">
              <option v-for="e in form?.equipment ?? []" :key="e.equipment_id" :value="e.equipment_id">
                {{ e.factory_code }} · {{ e.equipment_name }}
              </option>
            </select>
          </label>
          <div class="sim-grow"></div>
          <button type="button" class="sim-btn sim-line" :aria-pressed="view === 'template'" @click="view = view === 'template' ? 'result' : 'template'">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <line x1="3" y1="9" x2="21" y2="9" />
              <line x1="9" y1="9" x2="9" y2="21" />
            </svg>
            {{ view === "template" ? "결과 보기" : "데이터 양식 보기" }}
          </button>
        </div>

        <div class="sim-main">
          <div class="sim-inputs">
            <div v-if="loadError" class="sim-alert">{{ loadError }}</div>
            <div v-if="noSites" class="sim-alert">
              이 설비유형은 지금 계산할 수 있는 사업장이 없습니다.
              <template v-if="form && form.excluded_sites.length > 0">
                ({{ form.excluded_sites.map((s) => `${s.factory_code}: ${s.reason}`).join(" · ") }})
              </template>
              <template v-else>(설비 데이터가 없음)</template>
            </div>
            <div class="sim-meta">
              <span>
                입력 항목 {{ columns.length }}개<template v-if="changed.size > 0"> · <b class="sim-chg-text">바꾼 칸 {{ changed.size }}개</b></template>
              </span>
              <span>N/A = 값 없음(그 항목은 평가하지 않아 감점 0)</span>
            </div>
            <div v-if="loading && !form" class="sim-empty">불러오는 중…</div>
            <div class="sim-grid">
              <div v-for="col in columns" :key="col.name" class="sim-fld" :class="{ 'sim-span': col.name === 'factory_code' && siteNote }">
                <label class="sim-lab" :for="`sim-${col.name}`">
                  {{ col.label || col.name }} <span class="sim-name">{{ col.name }}</span>
                </label>
                <select
                  v-if="inputKind(col) === 'site'"
                  :id="`sim-${col.name}`"
                  v-model="values[col.name]"
                  class="sim-box"
                  :class="fieldClass(col.name)"
                  :disabled="noSites"
                >
                  <option v-for="s in form?.sites ?? []" :key="s.factory_code" :value="s.factory_code">
                    {{ s.factory_code }} (설비 {{ s.equipment_count }}대)
                  </option>
                </select>
                <input v-else-if="inputKind(col) === 'fixed'" :id="`sim-${col.name}`" class="sim-box" :value="values[col.name]" readonly />
                <select
                  v-else-if="inputKind(col) === 'choice'"
                  :id="`sim-${col.name}`"
                  v-model="values[col.name]"
                  class="sim-box"
                  :class="fieldClass(col.name)"
                >
                  <option v-if="!col.choices?.map(String).includes(values[col.name]) && values[col.name] !== NA && !(col.allow_blank && values[col.name] === '')" :value="values[col.name]">
                    {{ values[col.name] || "(선택)" }}
                  </option>
                  <option v-if="col.allow_blank" value="">(빈칸)</option>
                  <option v-for="c in col.choices ?? []" :key="String(c)" :value="String(c)">{{ c }}</option>
                  <option v-if="col.na_allowed" :value="NA">N/A</option>
                </select>
                <input
                  v-else-if="inputKind(col) === 'date'"
                  :id="`sim-${col.name}`"
                  v-model="values[col.name]"
                  type="date"
                  class="sim-box"
                  :class="fieldClass(col.name)"
                />
                <input
                  v-else
                  :id="`sim-${col.name}`"
                  v-model="values[col.name]"
                  class="sim-box"
                  :class="fieldClass(col.name)"
                  :placeholder="placeholder(col)"
                  :inputmode="col.dtype === 'int' || col.dtype === 'float' ? 'decimal' : undefined"
                />
                <span v-if="errors[col.name]" class="sim-err-text">{{ errors[col.name] }}</span>
                <span v-else-if="changed.has(col.name)" class="sim-hint">원래 {{ start[col.name] || "(빈칸)" }}</span>
                <span v-if="col.name === 'factory_code' && siteNote" class="sim-hint">{{ siteNote }}</span>
              </div>
            </div>
          </div>

          <aside class="sim-side">
            <template v-if="view === 'result'">
              <div class="sim-side-head">
                <b>{{ result ? "계산 결과" : "시작값 결과" }}</b>
                <span v-if="shown?.as_of">기준일 {{ shown.as_of }}</span>
              </div>
              <div v-if="result && !result.ok" class="sim-alert">
                <b>계산하지 못했습니다</b>
                <ul>
                  <li v-for="(e, i) in result.errors" :key="i">{{ columnLabel(e.column) }} — {{ e.reason }}<template v-if="e.raw_value"> ({{ e.raw_value }})</template></li>
                </ul>
              </div>
              <template v-if="shown">
                <div class="sim-total">
                  <div class="sim-total-l">종합점수</div>
                  <div class="sim-total-row">
                    <span class="sim-total-v">{{ formatScore(shown.total_score ?? 0) }}</span>
                    <span v-if="compare" class="sim-total-d">
                      원래 {{ formatScore(compare.total_score ?? 0) }} → <b>{{ deltaLabel(shown.total_score, compare.total_score) }}</b>
                    </span>
                  </div>
                  <div class="sim-status">
                    <template v-if="compare && compare.status && compare.status !== shown.status">
                      <span class="sim-badge" :style="{ background: statusBg(compare.status), color: statusColor(compare.status) }">{{ statusLabel(compare.status) }}</span>
                      <span class="sim-arrow">→</span>
                    </template>
                    <span v-if="shown.status" class="sim-badge" :style="{ background: statusBg(shown.status), color: statusColor(shown.status) }">
                      {{ statusLabel(shown.status) }}
                    </span>
                  </div>
                </div>
                <div class="sim-bars">
                  <div v-for="a in AXES" :key="a.key">
                    <div class="sim-bar-head">
                      <span><b>{{ a.label }}</b>({{ a.full }})</span>
                      <span>
                        {{ formatScore(axisValue(shown, a.key) ?? 0) }}
                        <span v-if="compare" class="sim-muted">{{ deltaLabel(axisValue(shown, a.key), axisValue(compare, a.key)) }}</span>
                      </span>
                    </div>
                    <div class="sim-track"><div class="sim-fill" :style="barStyle(axisValue(shown, a.key))"></div></div>
                  </div>
                </div>
                <div class="sim-sub">감점 큰 항목</div>
                <div v-if="deductions.length === 0" class="sim-muted">감점된 항목이 없습니다.</div>
                <div v-for="d in deductions" :key="`${d.axis}-${d.label}`" class="sim-ded">
                  <span><span class="sim-muted">{{ d.axis }}</span> {{ d.label }}</span>
                  <b>{{ formatScore(d.value) }}</b>
                </div>
                <p class="sim-foot">점수는 원본 계산식대로 0 아래로 내려갈 수 있습니다(막대는 0~100으로 잘라 표시).</p>
              </template>
              <div v-else-if="!result" class="sim-muted">값을 넣고 계산하기를 누르세요.</div>
            </template>

            <template v-else>
              <div class="sim-side-head">
                <b>데이터 양식 · {{ form ? typeLabel(form.ef_name, form.ef_code) : "" }}</b>
              </div>
              <p class="sim-muted">관리자 데이터 입력과 같은 양식입니다. 형식·허용값을 참고해 입력하세요.</p>
              <div class="sim-tpl">
                <table>
                  <thead>
                    <tr>
                      <th>항목</th>
                      <th>형식</th>
                      <th>허용값 · 범위</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="col in columns" :key="col.name">
                      <td><b>{{ col.label || col.name }}</b><br /><span class="sim-name">{{ col.name }}</span></td>
                      <td class="sim-nowrap">{{ dtypeLabel(col.dtype) }}</td>
                      <td>{{ ruleLabel(col) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </aside>
        </div>

        <footer class="sim-footer">
          <div class="sim-footer-l">
            <button type="button" class="sim-btn sim-line sim-small" :disabled="changed.size === 0" @click="resetValues">원래대로</button>
            <span>{{ statusText }}</span>
          </div>
          <div class="sim-footer-r">
            <button type="button" class="sim-btn sim-line" @click="close">닫기</button>
            <button type="button" class="sim-btn sim-main-btn" :disabled="noSites || !form || calculating" @click="calculate">계산하기</button>
          </div>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.sim-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(26, 34, 48, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  color: #1a2230;
  word-break: keep-all;
  overflow-wrap: anywhere;
}
.sim {
  width: min(1200px, 100%);
  height: min(840px, 100%);
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  outline: none;
}
.sim-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 24px 14px;
  border-bottom: 1px solid #eef0f3;
}
.sim-head h2 {
  margin: 0;
  font-size: 18px;
}
.sim-head p {
  margin: 2px 0 0;
  font-size: 12px;
  color: #6b7482;
}
.sim-x {
  width: 36px;
  height: 36px;
  border: 0;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  color: #6b7482;
  flex: 0 0 auto;
}
.sim-x:hover {
  background: #f1f3f6;
}
.sim-bar {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  padding: 14px 24px;
  background: #fafbfc;
  border-bottom: 1px solid #eef0f3;
  flex-wrap: wrap;
}
.sim-grow {
  flex: 1;
}
.sim-type {
  width: 200px;
}
.sim-eq {
  width: 240px;
}
.sim-fld {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.sim-lab {
  font-size: 12px;
  font-weight: 600;
  color: #1a2230;
}
.sim-name {
  font-size: 11px;
  font-weight: 500;
  color: #8891a0;
}
.sim-box {
  height: 34px;
  box-sizing: border-box;
  border: 1px solid #d5d9e0;
  border-radius: 6px;
  background: #fff;
  padding: 0 10px;
  font-family: inherit;
  font-size: 13px;
  color: #1a2230;
  width: 100%;
  min-width: 0;
}
.sim-box:focus {
  outline: 2px solid rgba(15, 138, 138, 0.35);
  border-color: #0f8a8a;
}
.sim-box[readonly],
.sim-box:disabled {
  background: #f4f5f7;
  color: #6b7482;
}
.sim-chg {
  border-color: #3b6fd6;
  background: #eef3fd;
}
.sim-err {
  border-color: #c4392b;
  background: #fcf1ef;
}
.sim-chg-text {
  color: #3b6fd6;
}
.sim-err-text {
  font-size: 11px;
  color: #c4392b;
}
.sim-hint {
  font-size: 11px;
  color: #6b7482;
}
.sim-seg {
  display: inline-flex;
  border: 1px solid #d5d9e0;
  border-radius: 8px;
  overflow: hidden;
}
.sim-seg button {
  border: 0;
  background: #fff;
  font-family: inherit;
  font-size: 13px;
  padding: 0 14px;
  height: 32px;
  color: #4a5361;
  cursor: pointer;
}
.sim-seg button + button {
  border-left: 1px solid #e2e5ea;
}
.sim-seg button.on {
  background: #e8f4f4;
  color: #0b6f6f;
  font-weight: 700;
}
.sim-seg button:disabled {
  color: #b4bac4;
  cursor: not-allowed;
}
.sim-btn {
  height: 36px;
  padding: 0 16px;
  border-radius: 8px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.sim-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.sim-line {
  border: 1px solid #d5d9e0;
  background: #fff;
  color: #1a2230;
}
.sim-line:hover:not(:disabled) {
  border-color: #0f8a8a;
}
.sim-main-btn {
  border: 1px solid #0f8a8a;
  background: #0f8a8a;
  color: #fff;
}
.sim-main-btn:hover:not(:disabled) {
  background: #0b6f6f;
}
.sim-small {
  height: 32px;
}
.sim-main {
  flex: 1;
  display: flex;
  min-height: 0;
}
.sim-inputs {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 16px 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sim-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #6b7482;
}
.sim-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
}
.sim-span {
  grid-column: 1 / -1;
}
.sim-empty {
  font-size: 13px;
  color: #8891a0;
}
.sim-alert {
  font-size: 12px;
  line-height: 1.6;
  color: #9a2d21;
  background: #fcf1ef;
  border: 1px solid #f3d3cd;
  border-radius: 8px;
  padding: 10px 12px;
}
.sim-alert ul {
  margin: 4px 0 0;
  padding-left: 18px;
}
.sim-side {
  width: 400px;
  flex: 0 0 auto;
  border-left: 1px solid #eef0f3;
  background: #fafbfc;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}
.sim-side-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
}
.sim-side-head span {
  font-size: 11px;
  color: #8891a0;
}
.sim-total {
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 16px;
}
.sim-total-l {
  font-size: 12px;
  color: #6b7482;
}
.sim-total-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 2px;
}
.sim-total-v {
  font-size: 34px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.sim-total-d {
  font-size: 13px;
  color: #6b7482;
}
.sim-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
}
.sim-badge {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}
.sim-arrow {
  color: #8891a0;
  font-size: 12px;
}
.sim-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sim-bar-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}
.sim-track {
  height: 8px;
  background: #e9ecf0;
  border-radius: 4px;
  margin-top: 4px;
  overflow: hidden;
}
.sim-fill {
  height: 100%;
  border-radius: 4px;
  background: #0f8a8a;
}
.sim-sub {
  font-size: 12px;
  font-weight: 700;
  margin-top: 2px;
}
.sim-ded {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  padding: 5px 0;
  border-bottom: 1px solid #f0f2f5;
  color: #4a5361;
  font-variant-numeric: tabular-nums;
}
.sim-ded b {
  color: #1a2230;
}
.sim-muted {
  font-size: 12px;
  color: #8891a0;
  margin: 0;
}
.sim-foot {
  margin: 4px 0 0;
  font-size: 11px;
  color: #8891a0;
  line-height: 1.5;
}
.sim-tpl {
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  background: #fff;
  overflow: auto;
}
.sim-tpl table {
  width: 100%;
  border-collapse: collapse;
}
.sim-tpl th {
  position: sticky;
  top: 0;
  background: #f7f8fa;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: #6b7482;
  padding: 7px 8px;
  border-bottom: 1px solid #e2e5ea;
}
.sim-tpl td {
  font-size: 12px;
  padding: 7px 8px;
  border-bottom: 1px solid #eef0f3;
  vertical-align: top;
  line-height: 1.45;
}
.sim-nowrap {
  white-space: nowrap;
}
.sim-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 24px;
  border-top: 1px solid #eef0f3;
  flex-wrap: wrap;
}
.sim-footer-l {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #6b7482;
}
.sim-footer-r {
  display: flex;
  gap: 8px;
}
@media (max-width: 900px) {
  .sim-main {
    flex-direction: column;
    overflow-y: auto;
  }
  .sim-inputs {
    overflow: visible;
  }
  .sim-side {
    width: auto;
    border-left: 0;
    border-top: 1px solid #eef0f3;
    overflow: visible;
  }
  .sim-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
