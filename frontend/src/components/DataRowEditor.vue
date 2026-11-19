<script setup lang="ts">
// 관리자 "데이터 입력 > 행 편집"(Stage 18) — 고른 설비유형·대상의 지금 데이터를 표로 불러와 칸을 고치거나 행을 추가하고,
// 고친·추가한 행만 붙여넣기와 같은 검증 → 확정 반영(추가·갱신)으로 보낸다. 저장 API가 따로 없어 규칙이 붙여넣기와 같다.
// 같은 행 판정 칸(🔒)은 기존 행에서 잠근다 — 바꾸면 이름 변경이 아니라 새 행 추가가 되기 때문(이름은 복제해서 새 행으로).
// 행 삭제는 일부러 없다(교체 방식·명령줄로만).
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { onBeforeRouteLeave } from "vue-router";
import { fetchDataRows, importPastedData, type DataRows, type ImportResultBody, type TemplateColumn } from "../api/admin";
import { useAuthStore } from "../stores/auth";
import { actionCountsOf, applyLines, DTYPE_LABEL, naSummary, ruleText, warningsOf } from "../utils/dataAdmin";
import {
  buildEditText,
  displayOrder,
  isCellChanged,
  isNewRow,
  isRowChanged,
  makeNewRow,
  pendingRows,
  rowsFromServer,
  type EditorRow,
} from "../utils/rowEditor";

const props = defineProps<{ efCode: string; table: string }>();
const emit = defineEmits<{ dirty: [count: number]; applied: [] }>();

const auth = useAuthStore();
const NA = "N/A";
// 왼쪽 고정 칸 폭(px) — sticky left 위치 계산에 쓴다
const NO_W = 52;
const STATE_W = 92;
const KEY_W = 150;

const data = ref<DataRows | null>(null);
const rows = ref<EditorRow[]>([]);
const loading = ref(false);
const loadError = ref<string | null>(null);
let nextId = 1;

const search = ref("");
const view = ref<"all" | "pending" | "error">("all");
const selectedId = ref<number | null>(null);

const busy = ref(false);
const requestError = ref<string | null>(null);
const checkResult = ref<ImportResultBody | null>(null);
const checkedText = ref("");
const lineToId = ref(new Map<number, number>());
const applyResult = ref<ImportResultBody | null>(null);

const header = computed(() => data.value?.header ?? []);
const keyIdx = computed(() => (data.value?.key ?? []).map((k) => header.value.indexOf(k)).filter((i) => i >= 0));
const order = computed(() => displayOrder(header.value, data.value?.key ?? []));
const columnByName = computed(() => new Map((data.value?.columns ?? []).map((c) => [c.name, c])));
const extraSet = computed(() => new Set(data.value?.extra_columns ?? []));

const pending = computed(() => pendingRows(rows.value));
const changedCount = computed(() => pending.value.filter((r) => !isNewRow(r)).length);
const addedCount = computed(() => pending.value.filter(isNewRow).length);
const edit = computed(() => buildEditText(header.value, pending.value));

watch(
  () => pending.value.length,
  (n) => emit("dirty", n),
  { immediate: true },
);

// 서버 오류 → 표의 행·칸
const errorsByCell = computed(() => {
  const map = new Map<string, string>();
  for (const e of checkResult.value?.row_errors ?? []) {
    const id = lineToId.value.get(e.row_number);
    if (id === undefined) continue;
    const key = `${id}|${e.column}`;
    map.set(key, map.has(key) ? `${map.get(key)} / ${e.reason}` : e.reason);
  }
  return map;
});
const errorRowIds = computed(
  () =>
    new Set(
      (checkResult.value?.row_errors ?? []).map((e) => lineToId.value.get(e.row_number)).filter((id): id is number => id !== undefined),
    ),
);
const actionById = computed(() => {
  const map = new Map<number, string>();
  for (const a of checkResult.value?.row_actions ?? []) {
    const id = lineToId.value.get(a.row_number);
    if (id !== undefined) map.set(id, a.action);
  }
  return map;
});
// 칸에 표시할 수 없는 오류(행 전체·없는 컬럼)
const errorsWithoutCell = computed(() =>
  (checkResult.value?.row_errors ?? [])
    .filter((e) => !header.value.includes(e.column))
    .map((e) => {
      const row = rows.value.find((r) => r.id === lineToId.value.get(e.row_number));
      return `${row ? rowLabel(row) : `${e.row_number}줄`} · ${e.column}: ${e.reason}`;
    }),
);
const actionCounts = computed(() => actionCountsOf(checkResult.value));
const canApply = computed(() => !!checkResult.value?.ok && checkedText.value === edit.value.text && !busy.value);

const visibleRows = computed(() => {
  let list = rows.value;
  if (view.value === "pending") list = list.filter((r) => isNewRow(r) || isRowChanged(r));
  else if (view.value === "error") list = list.filter((r) => errorRowIds.value.has(r.id));
  const q = search.value.trim().toLowerCase();
  if (q) list = list.filter((r) => isNewRow(r) || keyIdx.value.some((i) => (r.cells[i] ?? "").toLowerCase().includes(q)));
  return list;
});

function resetCheck() {
  checkResult.value = null;
  checkedText.value = "";
  lineToId.value = new Map();
  requestError.value = null;
}

// 검증한 뒤 칸을 고치면 그 검증은 무효 — 다시 검증해야 확정할 수 있다.
watch(
  () => edit.value.text,
  (text) => {
    if (checkResult.value && text !== checkedText.value) resetCheck();
  },
);

async function load() {
  if (!auth.token || !props.efCode) return;
  loading.value = true;
  loadError.value = null;
  resetCheck();
  selectedId.value = null;
  try {
    data.value = await fetchDataRows(auth.token, props.efCode, props.table);
    rows.value = rowsFromServer(data.value.rows);
    nextId = rows.value.length + 1;
  } catch (err: any) {
    data.value = null;
    rows.value = [];
    loadError.value = err?.response?.data?.detail ?? "데이터를 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
}

watch(() => [props.efCode, props.table], () => {
  applyResult.value = null;
  view.value = "all";
  search.value = "";
  load();
});

function addRow() {
  const row = makeNewRow(nextId++, header.value.length);
  rows.value.push(row);
  selectedId.value = row.id;
  view.value = view.value === "error" ? "all" : view.value;
  search.value = "";
}

function duplicateSelected() {
  const source = rows.value.find((r) => r.id === selectedId.value);
  if (!source) return;
  const row = makeNewRow(nextId++, header.value.length, source.cells);
  rows.value.push(row);
  selectedId.value = row.id;
  search.value = "";
}

function undoRow(row: EditorRow) {
  if (row.original) row.cells = [...row.original];
  else rows.value = rows.value.filter((r) => r.id !== row.id);
}

function discardAll() {
  if (!window.confirm(`고친·추가한 ${pending.value.length}행을 모두 원래대로 되돌릴까요?`)) return;
  rows.value = rows.value.filter((r) => !isNewRow(r)).map((r) => ({ ...r, cells: [...r.original!] }));
  selectedId.value = null;
}

function reload() {
  if (pending.value.length && !window.confirm(`저장하지 않은 변경 ${pending.value.length}행을 버리고 다시 불러올까요?`)) return;
  applyResult.value = null;
  load();
}

async function send(check: boolean) {
  if (!auth.token || !pending.value.length) return;
  busy.value = true;
  requestError.value = null;
  const snapshot = edit.value;
  try {
    const result = await importPastedData(auth.token, {
      text: snapshot.text,
      efCode: props.efCode,
      table: props.table,
      replace: false,
      check,
      source: "row_edit",
    });
    if (check || !result.ok) {
      // 검증 결과(또는 확정 때 다시 검증해서 실패한 경우 — 그 사이 DB가 바뀐 경우 등)
      checkResult.value = result;
      checkedText.value = snapshot.text;
      lineToId.value = snapshot.lineToId;
      applyResult.value = null;
      if (!result.ok && errorRowIds.value.size) view.value = "error";
    } else {
      applyResult.value = result;
      await load();
      view.value = "all";
      emit("applied");
    }
  } catch (err: any) {
    requestError.value = err?.response?.data?.detail ?? "요청에 실패했습니다.";
  } finally {
    busy.value = false;
  }
}

// --- 칸 표시 ---

function colOf(ci: number): TemplateColumn | undefined {
  return columnByName.value.get(header.value[ci]);
}

function isLocked(row: EditorRow, ci: number): boolean {
  return !isNewRow(row) && keyIdx.value.includes(ci);
}

function choicesFor(row: EditorRow, ci: number): string[] | null {
  const col = colOf(ci);
  if (!col?.choices) return null;
  const options = col.choices.map(String);
  if (col.na_allowed) options.push(NA);
  const current = row.cells[ci] ?? "";
  if (current !== "" && !options.includes(current)) options.unshift(current);
  return options;
}

function placeholderFor(ci: number): string {
  const col = colOf(ci);
  if (!col) return "";
  if (col.dtype === "date") return col.na_allowed ? "YYYY-MM-DD 또는 N/A" : "YYYY-MM-DD";
  return col.na_allowed ? "N/A 가능" : "";
}

function headerTitle(ci: number): string {
  const name = header.value[ci];
  if (extraSet.value.has(name)) return `${name} — 양식에 없는 칸(값만 보관, 계산에는 안 씀)`;
  const col = colOf(ci);
  if (!col) return name;
  const parts = [col.label, DTYPE_LABEL[col.dtype] ?? col.dtype, ruleText(col), col.na_allowed ? "N/A 가능" : "N/A 불가"];
  return `${name} — ${parts.filter(Boolean).join(" · ")}`;
}

function stickyStyle(position: number): Record<string, string> | undefined {
  if (position >= keyIdx.value.length) return undefined;
  return { left: `${NO_W + STATE_W + position * KEY_W}px` };
}

function cellError(row: EditorRow, ci: number): string | undefined {
  return errorsByCell.value.get(`${row.id}|${header.value[ci]}`);
}

function rowLabel(row: EditorRow): string {
  return row.no === null ? `새 행` : `${row.no}행`;
}

function rowState(row: EditorRow): { text: string; cls: string } | null {
  if (errorRowIds.value.has(row.id)) return { text: "오류", cls: "tag-error" };
  const action = actionById.value.get(row.id);
  if (action === "변경 없음") return { text: "변경 없음", cls: "tag-same" };
  if (action) return action === "갱신" ? { text: "갱신", cls: "tag-update" } : { text: "추가", cls: "tag-add" };
  if (isNewRow(row)) return { text: "새 행", cls: "tag-add" };
  if (isRowChanged(row)) return { text: "수정", cls: "tag-update" };
  return null;
}

// --- 저장 안 한 변경 보호(다른 화면으로 이동 · 창 닫기) ---

onBeforeRouteLeave(() => {
  if (!pending.value.length) return true;
  return window.confirm(`저장하지 않은 변경 ${pending.value.length}행이 있습니다. 이 화면을 떠날까요?`);
});

function onBeforeUnload(event: BeforeUnloadEvent) {
  if (!pending.value.length) return;
  event.preventDefault();
  event.returnValue = "";
}

onMounted(() => {
  window.addEventListener("beforeunload", onBeforeUnload);
  load();
});
onBeforeUnmount(() => window.removeEventListener("beforeunload", onBeforeUnload));
</script>

<template>
  <div class="row-editor">
    <div class="re-toolbar">
      <span class="re-summary">
        <b>{{ rows.filter((r) => !isNewRow(r)).length }}</b>행
        <template v-if="changedCount || addedCount">
          · <span class="re-changed">수정 {{ changedCount }}</span> · <span class="re-added">추가 {{ addedCount }}</span>
        </template>
      </span>
      <div class="re-views" role="group" aria-label="보기">
        <button type="button" :class="{ active: view === 'all' }" @click="view = 'all'">전체</button>
        <button type="button" :class="{ active: view === 'pending' }" @click="view = 'pending'">고친 행</button>
        <button type="button" :class="{ active: view === 'error' }" :disabled="!errorRowIds.size" @click="view = 'error'">
          오류 {{ errorRowIds.size || "" }}
        </button>
      </div>
      <input v-model="search" class="re-search" type="search" placeholder="🔒 칸 검색 (예: 설비명)" aria-label="행 검색" />
      <span class="spacer" />
      <button type="button" class="tool-btn" :disabled="loading || busy || !data" @click="addRow">+ 행 추가</button>
      <button type="button" class="tool-btn" :disabled="selectedId === null || busy" @click="duplicateSelected">선택 행 복제</button>
      <button type="button" class="tool-btn" :disabled="!pending.length || busy" @click="discardAll">변경 모두 취소</button>
      <button type="button" class="tool-btn" :disabled="loading || busy" @click="reload">다시 불러오기</button>
    </div>
    <div class="re-hint">
      행 번호를 눌러 선택(복제할 행) · <b>🔒 칸</b>(같은 행 판정 — {{ (data?.key ?? []).join(" + ") }})은 기존 행에서 바꿀 수 없습니다. 이름을 바꾸려면 복제해서
      새 행으로 넣으세요 · 값이 없으면 <span class="mono">N/A</span> · 머리글에 마우스를 올리면 설명·허용값이 보입니다 · 행 삭제는 교체 방식으로만
    </div>

    <div v-if="loading" class="re-state">불러오는 중...</div>
    <div v-else-if="loadError" class="re-state error">{{ loadError }}</div>
    <div v-else-if="data" class="re-scroll">
      <table class="re-table">
        <thead>
          <tr>
            <th class="sticky c-no" :style="{ left: '0px' }">#</th>
            <th class="sticky c-state" :class="{ 'state-last': !keyIdx.length }" :style="{ left: `${NO_W}px` }">상태</th>
            <th
              v-for="(ci, pos) in order"
              :key="ci"
              :class="{
                sticky: pos < keyIdx.length,
                'c-key': pos < keyIdx.length,
                'key-last': pos === keyIdx.length - 1,
                'c-extra': extraSet.has(header[ci]),
              }"
              :style="stickyStyle(pos)"
              :title="headerTitle(ci)"
            >
              <div class="h-name mono"><span v-if="pos < keyIdx.length" aria-label="잠김">🔒 </span>{{ header[ci] }}</div>
              <div class="h-label">{{ extraSet.has(header[ci]) ? "양식 외" : (colOf(ci)?.label ?? "") }}</div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in visibleRows"
            :key="row.id"
            :class="{ 'is-new': isNewRow(row), 'is-error': errorRowIds.has(row.id), 'is-selected': row.id === selectedId }"
          >
            <td class="sticky c-no" :style="{ left: '0px' }">
              <button type="button" class="no-btn" :aria-pressed="row.id === selectedId" @click="selectedId = row.id">
                {{ row.no ?? "+" }}
              </button>
            </td>
            <td class="sticky c-state" :class="{ 'state-last': !keyIdx.length }" :style="{ left: `${NO_W}px` }">
              <span v-if="rowState(row)" class="tag" :class="rowState(row)!.cls">{{ rowState(row)!.text }}</span>
              <button
                v-if="isNewRow(row) || isRowChanged(row)"
                type="button"
                class="undo-btn"
                :title="isNewRow(row) ? '이 새 행 지우기' : '이 행 되돌리기'"
                :aria-label="isNewRow(row) ? '새 행 지우기' : `${rowLabel(row)} 되돌리기`"
                @click="undoRow(row)"
              >
                {{ isNewRow(row) ? "✕" : "↺" }}
              </button>
            </td>
            <td
              v-for="(ci, pos) in order"
              :key="ci"
              :class="{
                sticky: pos < keyIdx.length,
                'c-key': pos < keyIdx.length,
                'key-last': pos === keyIdx.length - 1,
                changed: isCellChanged(row, ci),
                'cell-error': !!cellError(row, ci),
              }"
              :style="stickyStyle(pos)"
              :title="cellError(row, ci) ?? (isLocked(row, ci) ? '같은 행 판정 칸 — 기존 행에서는 바꿀 수 없습니다' : undefined)"
            >
              <span v-if="isLocked(row, ci)" class="locked">{{ row.cells[ci] }}</span>
              <select
                v-else-if="choicesFor(row, ci)"
                v-model="row.cells[ci]"
                :disabled="busy"
                :aria-label="`${rowLabel(row)} ${header[ci]}`"
              >
                <option value="">(선택)</option>
                <option v-for="opt in choicesFor(row, ci)!" :key="opt" :value="opt">{{ opt }}</option>
              </select>
              <input
                v-else
                v-model="row.cells[ci]"
                type="text"
                spellcheck="false"
                :disabled="busy"
                :placeholder="placeholderFor(ci)"
                :aria-label="`${rowLabel(row)} ${header[ci]}`"
              />
            </td>
          </tr>
          <tr v-if="!visibleRows.length">
            <td :colspan="header.length + 2" class="re-empty">
              {{ view === "pending" ? "고친 행이 없습니다." : view === "error" ? "오류 행이 없습니다." : "표시할 행이 없습니다." }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 검증 → 확정 -->
    <div class="re-actions">
      <button type="button" class="btn" :disabled="!pending.length || busy" @click="send(true)">
        {{ busy && !checkResult ? "검증 중..." : `변경 검증 (${pending.length}행)` }}
      </button>
      <span class="re-note">고친 행과 새 행만 보냅니다(추가·갱신). DB에는 아직 반영하지 않습니다.</span>
    </div>
    <div v-if="requestError" class="re-error">{{ requestError }}</div>

    <div v-if="checkResult" class="result" :class="checkResult.ok ? 'ok' : 'fail'">
      <div class="result-title">
        {{ checkResult.ok ? "검증 통과" : checkResult.dry_run ? "검증 실패" : "반영 실패 — 0건 반영" }}
      </div>
      <ul v-if="checkResult.file_errors.length" class="msg-list error">
        <li v-for="(msg, i) in checkResult.file_errors" :key="i">{{ msg }}</li>
      </ul>
      <div v-if="checkResult.row_errors.length" class="sub-title error">
        오류 {{ checkResult.row_errors.length }}건 ({{ errorRowIds.size }}행) — 표의 빨간 칸에 마우스를 올리면 사유가 보입니다. 고친 뒤 다시 검증하세요.
      </div>
      <ul v-if="errorsWithoutCell.length" class="msg-list error">
        <li v-for="(msg, i) in errorsWithoutCell" :key="i">{{ msg }}</li>
      </ul>
      <ul class="msg-list muted">
        <li v-if="naSummary(checkResult)">N/A(감점 0으로 계산): {{ naSummary(checkResult) }}</li>
      </ul>
      <ul v-if="warningsOf(checkResult).length" class="msg-list warn">
        <li v-for="(w, i) in warningsOf(checkResult)" :key="i">{{ w }}</li>
      </ul>
      <div v-if="checkResult.ok" class="confirm-box">
        <div>
          추가 <b>{{ actionCounts.add }}{{ table ? "행" : "건" }}</b> · 갱신 <b>{{ actionCounts.update }}{{ table ? "행" : "건" }}</b>을 반영합니다.
          <template v-if="actionCounts.same">(지금과 같은 <b>{{ actionCounts.same }}{{ table ? "행" : "건" }}</b>은 반영하지 않습니다)</template>
          <span v-if="checkResult.kind === 'reference'" class="re-note">반영하면 이 유형 설비 점수를 다시 계산합니다.</span>
        </div>
        <div class="apply-row">
          <button type="button" class="btn primary" :disabled="!canApply" @click="send(false)">
            {{ busy ? "반영 중..." : "확정 반영" }}
          </button>
          <button type="button" class="btn" :disabled="busy" @click="resetCheck">취소</button>
        </div>
      </div>
    </div>

    <div v-if="applyResult?.ok" class="result ok">
      <div class="result-title">반영 완료 — 표를 다시 불러왔습니다</div>
      <ul class="msg-list">
        <li v-for="(line, i) in applyLines(applyResult)" :key="i">{{ line }}</li>
      </ul>
      <ul v-if="warningsOf(applyResult).length" class="msg-list warn">
        <li v-for="(w, i) in warningsOf(applyResult)" :key="i">{{ w }}</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.row-editor {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
}
.re-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.re-summary {
  color: #4a5361;
}
.re-changed {
  color: #4a5bb5;
  font-weight: 600;
}
.re-added {
  color: #0f8a8a;
  font-weight: 600;
}
.re-views {
  display: inline-flex;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  overflow: hidden;
}
.re-views button {
  border: none;
  background: #fff;
  padding: 4px 10px;
  font-size: 12px;
  color: #4a5361;
  cursor: pointer;
}
.re-views button + button {
  border-left: 1px solid #e2e5ea;
}
.re-views button.active {
  background: #e6f3f3;
  color: #0b6f6f;
  font-weight: 600;
}
.re-views button:disabled {
  opacity: 0.45;
  cursor: default;
}
.re-search {
  width: 180px;
  padding: 4px 8px;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  font-size: 12px;
}
.spacer {
  flex: 1;
}
.tool-btn {
  padding: 4px 10px;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  background: #fff;
  font-size: 12px;
  color: #4a5361;
  cursor: pointer;
}
.tool-btn:disabled {
  opacity: 0.45;
  cursor: default;
}
.re-hint {
  font-size: 12px;
  color: #8891a0;
  line-height: 1.6;
}
.re-state {
  padding: 24px;
  text-align: center;
  color: #8891a0;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
}
.re-state.error,
.re-error {
  color: #c4392b;
}
.re-error {
  font-size: 12px;
}
/* 가로·세로 스크롤은 이 영역 안에서만 — 머리글은 위, 행 번호·상태·🔒 칸은 왼쪽에 고정 */
.re-scroll {
  max-height: clamp(320px, 60vh, 640px);
  overflow: auto;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  background: #fff;
}
.re-table {
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
}
.re-table th,
.re-table td {
  border-right: 1px solid #eef0f3;
  border-bottom: 1px solid #eef0f3;
  background: #fff;
  white-space: nowrap;
}
.re-table th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #f7f8fa;
  padding: 6px 8px;
  text-align: left;
  vertical-align: bottom;
  min-width: 120px;
  cursor: help;
}
.re-table th.sticky {
  z-index: 4;
}
.re-table td.sticky {
  position: sticky;
  z-index: 1;
}
.h-name {
  font-weight: 600;
  color: #1a2230;
}
.h-label {
  font-weight: 400;
  color: #8891a0;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}
th.c-extra .h-label {
  color: #9a6400;
}
.c-no {
  width: 52px;
  min-width: 52px !important;
  max-width: 52px;
  text-align: center !important;
}
.c-state {
  width: 92px;
  min-width: 92px !important;
  max-width: 92px;
  padding: 0 6px;
}
.c-key {
  width: 150px;
  min-width: 150px !important;
  max-width: 150px;
}
.c-key .h-name {
  overflow: hidden;
  text-overflow: ellipsis;
}
/* 고정 칸의 오른쪽 경계 — 가로 스크롤 때 고정 영역이 구분되게 */
.re-table .key-last,
.re-table .state-last {
  box-shadow: 2px 0 0 #d5d9e0;
}
.re-table td {
  padding: 0;
  height: 30px;
}
.re-table td input,
.re-table td select {
  width: 100%;
  min-width: 120px;
  height: 29px;
  border: none;
  background: transparent;
  padding: 0 8px;
  font: inherit;
  color: #1a2230;
}
.re-table td input:focus,
.re-table td select:focus {
  outline: 2px solid #0f8a8a;
  outline-offset: -2px;
  background: #fff;
}
.re-table td input::placeholder {
  color: #c2c7cf;
}
.locked {
  display: block;
  padding: 0 8px;
  line-height: 29px;
  color: #4a5361;
  overflow: hidden;
  text-overflow: ellipsis;
}
.no-btn {
  width: 100%;
  height: 29px;
  border: none;
  background: transparent;
  color: #8891a0;
  font: inherit;
  cursor: pointer;
}
.no-btn:hover {
  color: #0b6f6f;
}
tr.is-selected .c-no,
tr.is-selected .no-btn {
  background: #0f8a8a;
  color: #fff;
}
tr.is-new td {
  background: #f1faf6;
}
tr.is-error td.c-no,
tr.is-error td.c-state {
  background: #fdf5f4;
}
.re-table td.changed {
  background: #eef1fc;
}
.re-table td.changed input,
.re-table td.changed select {
  font-weight: 600;
  color: #33449e;
}
.re-table td.cell-error {
  background: #fde3e0;
  box-shadow: inset 0 0 0 1px #e8a39b;
}
.undo-btn {
  margin-left: 4px;
  border: 1px solid #e2e5ea;
  border-radius: 4px;
  background: #fff;
  color: #4a5361;
  font-size: 11px;
  line-height: 16px;
  padding: 0 5px;
  cursor: pointer;
}
.undo-btn:hover {
  border-color: #0f8a8a;
  color: #0f8a8a;
}
.tag {
  display: inline-block;
  padding: 0 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
}
.tag-same {
  background: #f1f2f4;
  color: #8891a0;
}
.tag-add {
  color: #0f8a8a;
  background: #e3f4f4;
}
.tag-update {
  color: #4a5bb5;
  background: #e8ebfa;
}
.tag-error {
  color: #c4392b;
  background: #fde3e0;
}
.re-empty {
  padding: 20px !important;
  text-align: left;
  color: #8891a0;
}
.mono {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.re-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 6px;
}
.re-note {
  font-size: 12px;
  color: #8891a0;
}
.btn {
  padding: 7px 16px;
  border: 1px solid #0f8a8a;
  border-radius: 6px;
  background: #fff;
  color: #0f8a8a;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn.primary {
  background: #0f8a8a;
  color: #fff;
}
.btn:disabled {
  opacity: 0.45;
  cursor: default;
}
.result {
  margin-top: 6px;
  border-radius: 8px;
  padding: 12px 14px;
  border: 1px solid;
}
.result.ok {
  border-color: #b9dfdf;
  background: #f3fafa;
}
.result.fail {
  border-color: #f0c7c2;
  background: #fdf5f4;
}
.result-title {
  font-weight: 700;
  margin-bottom: 6px;
}
.sub-title {
  font-weight: 600;
  font-size: 12px;
}
.msg-list {
  margin: 6px 0 0;
  padding-left: 18px;
  line-height: 1.7;
}
.msg-list:empty {
  display: none;
}
.msg-list.error,
.sub-title.error {
  color: #c4392b;
}
.msg-list.warn {
  color: #9a6400;
}
.msg-list.muted {
  color: #8891a0;
  font-size: 12px;
}
.confirm-box {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #b9dfdf;
}
.apply-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}
</style>
