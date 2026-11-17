<script setup lang="ts">
// 관리자 "데이터 입력" 탭 (Stage 16-2/16-3, 16-6 붙여넣기) —
// 대상·방식 선택 → ① 붙여넣기 → ② 검증 → ③ 입력값 미리보기 → ④ 확정 반영, 그리고 현재 데이터 내려받기.
// 검증·계산 규칙은 명령줄(import_data / import_reference)과 같다 — 백엔드가 같은 서비스를 부른다.
// 리셋(전체 비우기)은 일부러 없다 — 명령줄로만.
import { computed, onMounted, ref, watch } from "vue";
import {
  downloadDataExport,
  downloadFullSqlDump,
  fetchDataTargets,
  fetchDataTemplate,
  importPastedData,
  type DataTarget,
  type DataTemplate,
  type ImportResultBody,
  type TemplateColumn,
} from "../api/admin";
import { useAuthStore } from "../stores/auth";
import { decodeFileBytes, errorKey, parsePasted, type PastedRow, type PastedTable } from "../utils/pasteData";

const auth = useAuthStore();

const targets = ref<DataTarget[]>([]);
const loadError = ref<string | null>(null);

const efCode = ref("");
const table = ref(""); // "" = 설비 데이터, 아니면 참고표 이름
const replace = ref(false);
const text = ref("");
const fileInput = ref<HTMLInputElement | null>(null);
const confirmReplace = ref(false);

const template = ref<DataTemplate | null>(null);
const showTemplate = ref(false);
const copyMessage = ref<string | null>(null);

const busy = ref(false);
const requestError = ref<string | null>(null);
// 검증 결과와, 그 검증에 쓴 내용의 미리보기(검증 시점 스냅샷 — 이후 칸을 고치면 무효)
const checkResult = ref<ImportResultBody | null>(null);
const checkedPreview = ref<PastedTable | null>(null);
const applyResult = ref<ImportResultBody | null>(null);

const exportBusy = ref<string | null>(null);
const exportMessage = ref<string | null>(null);
const dumpBusy = ref(false);
const dumpMessage = ref<string | null>(null);
const dumpError = ref(false);

const PREVIEW_LIMIT = 200;

const target = computed(() => targets.value.find((t) => t.ef_code === efCode.value) ?? null);
const referenceTable = computed(() => target.value?.reference_tables.find((r) => r.name === table.value) ?? null);
const targetLabel = computed(() => {
  if (!target.value) return "";
  const base = `${target.value.ef_code} ${target.value.ef_name}`;
  return referenceTable.value ? `${base} · 참고표 ${referenceTable.value.label}` : `${base} · 설비 데이터`;
});
const unit = computed(() => (table.value ? "행" : "건"));
// 교체하면 지워질 현재 건수
const existingCount = computed(() =>
  referenceTable.value ? referenceTable.value.rows : (target.value?.equipment_count ?? 0)
);

// 붙여넣은 내용의 즉석 요약(서버 검증 전 힌트) — 양식과 헤더 비교
const pasted = computed(() => parsePasted(text.value));
const templateNames = computed(() => template.value?.columns.map((c) => c.name) ?? []);
const missingColumns = computed(() =>
  pasted.value.header.length ? templateNames.value.filter((n) => !pasted.value.header.includes(n)) : []
);
const extraColumns = computed(() =>
  template.value ? pasted.value.header.filter((h) => h && !templateNames.value.includes(h)) : []
);

const errorsByCell = computed(() => {
  const map = new Map<string, string>();
  for (const e of checkResult.value?.row_errors ?? []) {
    const key = errorKey(e.row_number, e.column);
    map.set(key, map.has(key) ? `${map.get(key)} / ${e.reason}` : e.reason);
  }
  return map;
});
const errorRows = computed(() => new Set((checkResult.value?.row_errors ?? []).map((e) => e.row_number)));
const actionByRow = computed(() => new Map((checkResult.value?.row_actions ?? []).map((a) => [a.row_number, a.action])));

// 미리보기 행 — 오류 행을 위로
const previewRows = computed<PastedRow[]>(() => {
  const rows = checkedPreview.value?.rows ?? [];
  if (!errorRows.value.size) return rows;
  return [...rows.filter((r) => errorRows.value.has(r.rowNumber)), ...rows.filter((r) => !errorRows.value.has(r.rowNumber))];
});
const actionCounts = computed(() => {
  let add = 0;
  let update = 0;
  for (const a of checkResult.value?.row_actions ?? []) a.action === "갱신" ? update++ : add++;
  return { add, update };
});
const canApply = computed(
  () => !!checkResult.value?.ok && !busy.value && (!replace.value || confirmReplace.value)
);

async function loadTargets() {
  if (!auth.token) return;
  try {
    targets.value = await fetchDataTargets(auth.token);
    loadError.value = null;
    if (!efCode.value && targets.value.length) efCode.value = targets.value[0].ef_code;
  } catch (err: any) {
    loadError.value = err?.response?.data?.detail ?? "대상 목록을 불러오지 못했습니다.";
  }
}

async function loadTemplate() {
  template.value = null;
  if (!auth.token || !efCode.value) return;
  try {
    template.value = await fetchDataTemplate(auth.token, efCode.value, table.value);
  } catch {
    template.value = null;
  }
}

function resetCheck() {
  checkResult.value = null;
  checkedPreview.value = null;
  confirmReplace.value = false;
  requestError.value = null;
}

// 대상·방식·내용이 바뀌면 이전 검증은 무효 — 같은 조건으로 다시 검증해야 확정할 수 있다.
watch([efCode, table, replace, text], resetCheck);
watch(efCode, () => {
  table.value = "";
});
watch([efCode, table], loadTemplate);

function onPasteInput() {
  applyResult.value = null;
}

async function copyTemplateHeader() {
  if (!template.value) return;
  const header = template.value.header;
  try {
    await navigator.clipboard.writeText(header);
  } catch {
    // http(사내망 IP 접속 등)에서는 clipboard API가 막힐 수 있어 예전 방식으로
    const helper = document.createElement("textarea");
    helper.value = header;
    helper.style.position = "fixed";
    helper.style.opacity = "0";
    document.body.appendChild(helper);
    helper.select();
    document.execCommand("copy");
    helper.remove();
  }
  copyMessage.value = `헤더 ${template.value.columns.length}개 컬럼을 복사했습니다 — 엑셀 첫 행에 붙여넣으세요.`;
  setTimeout(() => (copyMessage.value = null), 4000);
}

function insertTemplateHeader() {
  if (!template.value) return;
  text.value = template.value.header + "\n" + text.value.replace(/^\s+/, "");
}

async function onFileChosen(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  text.value = decodeFileBytes(await file.arrayBuffer());
  applyResult.value = null;
  input.value = "";
}

function clearText() {
  text.value = "";
  applyResult.value = null;
}

async function send(check: boolean) {
  if (!auth.token || !text.value.trim() || !efCode.value) return;
  busy.value = true;
  requestError.value = null;
  const snapshot = text.value;
  try {
    const result = await importPastedData(auth.token, {
      text: snapshot,
      efCode: efCode.value,
      table: table.value,
      replace: replace.value,
      check,
    });
    if (check) {
      checkResult.value = result;
      checkedPreview.value = parsePasted(snapshot);
      applyResult.value = null;
    } else if (result.ok) {
      applyResult.value = result;
      // 반영 끝 — 같은 내용을 실수로 두 번 넣지 않게 비운다
      text.value = "";
      resetCheck();
      await loadTargets();
    } else {
      // 확정 때 다시 검증해서 실패(그 사이 DB가 바뀐 경우 등) — 오류를 보여준다
      checkResult.value = result;
      checkedPreview.value = parsePasted(snapshot);
    }
  } catch (err: any) {
    requestError.value = err?.response?.data?.detail ?? "요청에 실패했습니다.";
  } finally {
    busy.value = false;
  }
}

async function onExport(code: string, tableName: string) {
  if (!auth.token) return;
  exportBusy.value = `${code}:${tableName}`;
  exportMessage.value = null;
  try {
    const rows = await downloadDataExport(auth.token, code, tableName);
    exportMessage.value = `${code} ${tableName ? "참고표 " + tableName : "설비 데이터"} ${rows}건을 내려받았습니다.`;
  } catch {
    exportMessage.value = "내려받기에 실패했습니다.";
  } finally {
    exportBusy.value = null;
  }
}

async function onFullDump() {
  if (!auth.token) return;
  dumpBusy.value = true;
  dumpMessage.value = null;
  dumpError.value = false;
  try {
    const { tables, rows } = await downloadFullSqlDump(auth.token);
    dumpMessage.value = `테이블 ${tables}개 · 전체 ${rows.toLocaleString()}행을 내려받았습니다.`;
  } catch {
    dumpMessage.value = "내려받기에 실패했습니다.";
    dumpError.value = true;
  } finally {
    dumpBusy.value = false;
  }
}

function ruleText(col: TemplateColumn): string {
  const parts: string[] = [];
  if (col.choices) parts.push(col.choices.join(" / "));
  if (col.min !== undefined && col.max !== undefined) parts.push(`${col.min} ~ ${col.max}`);
  else if (col.min !== undefined) parts.push(`${col.min} 이상`);
  else if (col.max !== undefined) parts.push(`${col.max} 이하`);
  if (col.gt !== undefined) parts.push(`${col.gt} 초과`);
  return parts.join(", ");
}

const DTYPE_LABEL: Record<string, string> = { str: "문자", int: "정수", float: "숫자", date: "날짜" };

function applyLines(result: ImportResultBody): string[] {
  if (result.kind === "equipment") {
    const lines = [`${result.imported_rows ?? 0}건 반영 완료`];
    if (result.replace) lines.push(`기존 설비 ${result.replaced_rows ?? 0}건을 지우고 교체했습니다.`);
    return lines;
  }
  return [
    `추가 ${result.inserted_rows ?? 0}행 · 갱신 ${result.updated_rows ?? 0}행` +
      (result.replace ? ` · 삭제 ${result.deleted_rows ?? 0}행` : "") +
      ` → 현재 ${result.table_rows_after ?? 0}행`,
    `설비 ${result.recalculated ?? 0}건의 점수를 다시 계산했습니다.`,
  ];
}

function warningsOf(result: ImportResultBody): string[] {
  return [...(result.reference_warnings ?? []), ...(result.warnings ?? [])];
}

function naSummary(result: ImportResultBody): string {
  return Object.entries(result.na_values ?? {})
    .map(([col, n]) => `${col} ${n}칸`)
    .join(", ");
}

function rowErrorsWithoutCell(rowNumber: number): string[] {
  // 칸에 표시할 수 없는 오류(행 전체·중복·미리보기에 없는 컬럼)
  const header = checkedPreview.value?.header ?? [];
  return (checkResult.value?.row_errors ?? [])
    .filter((e) => e.row_number === rowNumber && !header.includes(e.column))
    .map((e) => `${e.column}: ${e.reason}`);
}

onMounted(async () => {
  await loadTargets();
  await loadTemplate();
});
</script>

<template>
  <div class="data-panel">
    <div v-if="loadError" class="panel-error">{{ loadError }}</div>

    <section class="card">
      <h3>데이터 입력</h3>
      <p class="card-hint">
        엑셀에서 <b>헤더(첫 행) 포함</b> 범위를 복사해 붙여넣고 <b>검증</b> → 미리보기 확인 → <b>확정 반영</b> 순서로 넣습니다.
        오류가 한 행이라도 있으면 아무것도 반영하지 않습니다.
      </p>

      <div class="form-grid">
        <label class="field">
          <span class="field-label">설비유형</span>
          <select v-model="efCode" :disabled="busy">
            <option v-for="t in targets" :key="t.ef_code" :value="t.ef_code">
              {{ t.ef_code }} {{ t.ef_name }} ({{ t.equipment_count }}건)
            </option>
          </select>
        </label>

        <div class="field">
          <span class="field-label">대상</span>
          <div class="choices">
            <label class="choice">
              <input v-model="table" type="radio" value="" :disabled="busy" />
              설비 데이터
            </label>
            <label v-for="r in target?.reference_tables ?? []" :key="r.name" class="choice">
              <input v-model="table" type="radio" :value="r.name" :disabled="busy" />
              참고표 · {{ r.label }} ({{ r.rows }}행)
            </label>
          </div>
        </div>

        <div class="field">
          <span class="field-label">방식</span>
          <div class="choices">
            <label class="choice">
              <input v-model="replace" type="radio" :value="false" :disabled="busy" />
              추가·갱신 <span class="choice-note">같은 {{ table ? "행" : "설비" }}는 갱신, 새 것은 추가</span>
            </label>
            <label class="choice">
              <input v-model="replace" type="radio" :value="true" :disabled="busy" />
              교체 <span class="choice-note">기존 {{ existingCount }}{{ unit }}을 지우고 붙여넣은 내용으로</span>
            </label>
          </div>
        </div>
      </div>

      <!-- ① 붙여넣기 -->
      <div class="step">
        <div class="step-head">
          <span class="step-no">1</span>
          <span class="step-title">붙여넣기</span>
          <span class="target-label">{{ targetLabel }}</span>
          <span class="spacer" />
          <button type="button" class="tool-btn" :disabled="!template" @click="copyTemplateHeader">양식 복사</button>
          <button type="button" class="tool-btn" :disabled="!template" @click="showTemplate = !showTemplate">
            양식 보기 {{ showTemplate ? "▴" : "▾" }}
          </button>
          <button type="button" class="tool-btn" :disabled="busy" @click="fileInput?.click()">파일에서 불러오기</button>
          <input ref="fileInput" type="file" accept=".dat,.txt,.tsv" class="hidden-file" @change="onFileChosen" />
          <button type="button" class="tool-btn" :disabled="!text || busy" @click="clearText">비우기</button>
        </div>
        <div v-if="copyMessage" class="copy-message">{{ copyMessage }}</div>

        <div v-if="showTemplate && template" class="template-box">
          <div class="template-note">
            같은 {{ table ? "행" : "설비" }} 판정: <span class="mono">{{ template.key.join(" + ") }}</span> · 날짜는 YYYY-MM-DD ·
            값이 없으면 <span class="mono">N/A</span>(허용 컬럼만, 감점 0으로 계산)
          </div>
          <div class="template-scroll">
            <table class="template-table">
              <thead>
                <tr><th>컬럼명(헤더)</th><th>설명</th><th>형식</th><th>허용값·범위</th><th>N/A</th></tr>
              </thead>
              <tbody>
                <tr v-for="c in template.columns" :key="c.name">
                  <td class="mono">{{ c.name }}</td>
                  <td>{{ c.label }}</td>
                  <td>{{ DTYPE_LABEL[c.dtype] ?? c.dtype }}</td>
                  <td>{{ ruleText(c) }}</td>
                  <td>{{ c.na_allowed ? "가능" : "불가" }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <button type="button" class="tool-btn small" @click="insertTemplateHeader">붙여넣기 칸 맨 위에 헤더 넣기</button>
        </div>

        <textarea
          v-model="text"
          class="paste-area"
          spellcheck="false"
          wrap="off"
          :disabled="busy"
          aria-label="붙여넣기"
          placeholder="엑셀에서 헤더(첫 행)를 포함한 범위를 복사해 여기에 붙여넣으세요 (Ctrl+V). 탭으로 구분된 내용이면 됩니다."
          @input="onPasteInput"
        ></textarea>
        <div class="paste-stats">
          <template v-if="pasted.header.length">
            헤더 <b>{{ pasted.header.length }}</b>개 컬럼 · 데이터 <b>{{ pasted.rows.length }}</b>행
            <span v-if="missingColumns.length" class="stat-warn">· 양식에 있는데 없는 컬럼: {{ missingColumns.join(", ") }}</span>
            <span v-if="extraColumns.length" class="stat-muted">· 양식에 없는 컬럼(값은 보관, 계산 안 씀): {{ extraColumns.join(", ") }}</span>
          </template>
          <span v-else class="stat-muted">아직 붙여넣은 내용이 없습니다.</span>
        </div>
      </div>

      <!-- ② 검증 -->
      <div class="actions">
        <button type="button" class="btn" :disabled="!pasted.rows.length || !efCode || busy" @click="send(true)">
          {{ busy && !checkResult ? "검증 중..." : "검증" }}
        </button>
        <span class="actions-note">DB에는 아직 반영하지 않습니다.</span>
      </div>
      <div v-if="requestError" class="panel-error">{{ requestError }}</div>

      <!-- ③ 미리보기 · ④ 확정 -->
      <div v-if="checkResult && checkedPreview" class="result" :class="checkResult.ok ? 'ok' : 'fail'">
        <div class="result-title">
          <span class="step-no" :class="checkResult.ok ? '' : 'fail'">{{ checkResult.ok ? "3" : "!" }}</span>
          {{ checkResult.ok ? "검증 통과 — 입력값 미리보기" : checkResult.dry_run ? "검증 실패" : "반영 실패 — 0건 반영" }}
        </div>

        <ul v-if="checkResult.file_errors.length" class="msg-list error">
          <li v-for="(msg, i) in checkResult.file_errors" :key="i">{{ msg }}</li>
        </ul>
        <div v-if="checkResult.row_errors.length" class="sub-title error">
          오류 {{ checkResult.row_errors.length }}건 ({{ errorRows.size }}행) — 빨간 칸에 마우스를 올리면 사유가 보입니다. 내용을 고친 뒤 다시 검증하세요.
        </div>

        <div v-if="checkedPreview.header.length && !checkResult.file_errors.length" class="preview-scroll">
          <table class="preview-table">
            <thead>
              <tr>
                <th class="col-line">줄</th>
                <th class="col-action">구분</th>
                <th v-for="(h, i) in checkedPreview.header" :key="i" class="mono">{{ h }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in previewRows.slice(0, PREVIEW_LIMIT)"
                :key="row.rowNumber"
                :class="{ 'row-error': errorRows.has(row.rowNumber) }"
              >
                <td class="col-line">{{ row.rowNumber }}</td>
                <td class="col-action">
                  <span v-if="errorRows.has(row.rowNumber)" class="tag tag-error" :title="rowErrorsWithoutCell(row.rowNumber).join('\n')">오류</span>
                  <span v-else-if="actionByRow.get(row.rowNumber) === '갱신'" class="tag tag-update">갱신</span>
                  <span v-else-if="actionByRow.get(row.rowNumber)" class="tag tag-add">추가</span>
                </td>
                <td
                  v-for="(h, ci) in checkedPreview.header"
                  :key="ci"
                  :class="{ 'cell-error': errorsByCell.has(errorKey(row.rowNumber, h)) }"
                  :title="errorsByCell.get(errorKey(row.rowNumber, h)) ?? row.cells[ci]"
                >
                  {{ row.cells[ci] ?? "" }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="previewRows.length > PREVIEW_LIMIT" class="more">
          미리보기는 {{ PREVIEW_LIMIT }}행까지만 표시합니다(전체 {{ previewRows.length }}행 모두 검증했습니다).
        </div>

        <ul class="msg-list muted">
          <li v-if="checkResult.unknown_columns.length">
            양식에 없는 컬럼(값은 보관, 계산에는 안 씀): {{ checkResult.unknown_columns.join(", ") }}
          </li>
          <li v-if="checkResult.ignored_columns?.length">건너뛴 컬럼: {{ checkResult.ignored_columns.join(", ") }}</li>
          <li v-if="naSummary(checkResult)">N/A(감점 0으로 계산): {{ naSummary(checkResult) }}</li>
        </ul>
        <ul v-if="warningsOf(checkResult).length" class="msg-list warn">
          <li v-for="(w, i) in warningsOf(checkResult)" :key="i">{{ w }}</li>
        </ul>

        <div v-if="checkResult.ok" class="confirm-box">
          <div class="confirm-summary">
            <span class="step-no">4</span>
            <span v-if="replace">
              기존 <b>{{ existingCount }}{{ unit }}</b>을 지우고 <b>{{ checkResult.total_rows }}{{ unit }}</b>을 넣습니다.
            </span>
            <span v-else>
              추가 <b>{{ actionCounts.add }}{{ unit }}</b> · 갱신 <b>{{ actionCounts.update }}{{ unit }}</b>을 반영합니다.
            </span>
            <span v-if="checkResult.kind === 'reference'" class="choice-note">반영하면 이 유형 설비 점수를 다시 계산합니다.</span>
          </div>
          <div class="apply-row">
            <label v-if="replace" class="confirm">
              <input v-model="confirmReplace" type="checkbox" />
              기존 {{ existingCount }}{{ unit }}을 지우고 교체하는 것을 확인했습니다.
            </label>
            <button type="button" class="btn primary" :disabled="!canApply" @click="send(false)">
              {{ busy ? "반영 중..." : "확정 반영" }}
            </button>
            <button type="button" class="btn" :disabled="busy" @click="resetCheck">취소</button>
          </div>
        </div>
      </div>

      <div v-if="applyResult?.ok" class="result ok">
        <div class="result-title">반영 완료</div>
        <ul class="msg-list">
          <li v-for="(line, i) in applyLines(applyResult)" :key="i">{{ line }}</li>
        </ul>
        <ul v-if="warningsOf(applyResult).length" class="msg-list warn">
          <li v-for="(w, i) in warningsOf(applyResult)" :key="i">{{ w }}</li>
        </ul>
      </div>
    </section>

    <section class="card">
      <h3>내려받기</h3>
      <div class="dump-box">
        <div class="dump-head">
          <div>
            <div class="dump-title">전체 DB (.sql, PostgreSQL용)</div>
            <div class="dump-desc">
              모든 테이블(구조 + 데이터 + 마이그레이션 버전)을 한 파일로 받습니다. 다른 PostgreSQL로 통째로 옮길 때 빈 DB에 psql로 복원합니다.
              접근 권한 명단도 들어 있으니 파일 보관에 주의하세요.
            </div>
          </div>
          <button type="button" class="btn primary" :disabled="dumpBusy" @click="onFullDump">
            {{ dumpBusy ? "만드는 중..." : "전체 DB 내려받기" }}
          </button>
        </div>
        <pre class="dump-cmd">createdb eflms_new
psql -v ON_ERROR_STOP=1 -d eflms_new -f eflms_full_YYYYMMDD_HHMM.sql</pre>
        <div v-if="dumpMessage" class="export-message" :class="{ 'dump-error': dumpError }">{{ dumpMessage }}</div>
      </div>

      <div class="sub-heading">설비유형별 (.dat — 입력파일 형식)</div>
      <p class="card-hint">
        지금 DB 내용을 입력파일과 같은 형식(.dat)으로 받습니다. 백업하거나 다른 서버로 옮길 때 그대로 다시 넣을 수 있습니다.
      </p>
      <table class="export-table">
        <thead>
          <tr><th>설비유형</th><th>설비 데이터</th><th>참고표</th></tr>
        </thead>
        <tbody>
          <tr v-for="t in targets" :key="t.ef_code">
            <td><span class="mono">{{ t.ef_code }}</span> {{ t.ef_name }}</td>
            <td>
              <button
                type="button"
                class="btn small"
                :disabled="exportBusy !== null || t.equipment_count === 0"
                @click="onExport(t.ef_code, '')"
              >
                {{ t.equipment_count }}건 내려받기
              </button>
            </td>
            <td>
              <span v-if="!t.reference_tables.length" class="muted-text">—</span>
              <button
                v-for="r in t.reference_tables"
                :key="r.name"
                type="button"
                class="btn small"
                :disabled="exportBusy !== null || r.rows === 0"
                @click="onExport(t.ef_code, r.name)"
              >
                {{ r.label }} {{ r.rows }}행
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="exportMessage" class="export-message">{{ exportMessage }}</div>
    </section>
  </div>
</template>

<style scoped>
.data-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card {
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 18px 20px;
}
h3 {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 4px;
}
.card-hint {
  font-size: 12px;
  color: #8891a0;
  margin: 0 0 14px;
  line-height: 1.6;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}
.field {
  display: grid;
  grid-template-columns: 80px 1fr;
  align-items: start;
  gap: 10px;
  font-size: 13px;
}
.field-label {
  color: #4a5361;
  font-weight: 600;
  padding-top: 4px;
}
select {
  max-width: 320px;
  padding: 6px 8px;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
}
.choices {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  padding-top: 3px;
}
.choice {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}
.choice-note {
  color: #8891a0;
  font-size: 12px;
}
.step {
  margin-top: 18px;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  overflow: hidden;
}
.step-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 10px;
  background: #f9fafb;
  border-bottom: 1px solid #eef0f3;
  font-size: 12px;
}
.step-no {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #0f8a8a;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  margin-right: 2px;
}
.step-no.fail {
  background: #c4392b;
}
.step-title {
  font-weight: 700;
  font-size: 13px;
}
.target-label {
  color: #8891a0;
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
.tool-btn.small {
  margin: 8px 10px 10px;
}
.tool-btn:disabled {
  opacity: 0.45;
  cursor: default;
}
.hidden-file {
  display: none;
}
.copy-message {
  padding: 6px 10px;
  font-size: 12px;
  color: #0f8a8a;
  background: #f3fafa;
  border-bottom: 1px solid #eef0f3;
}
.template-box {
  border-bottom: 1px solid #eef0f3;
  background: #fcfcfd;
}
.template-note {
  padding: 8px 10px 4px;
  font-size: 12px;
  color: #4a5361;
}
.template-scroll {
  max-height: 260px;
  overflow: auto;
  margin: 0 10px;
}
.template-table {
  border-collapse: collapse;
  font-size: 12px;
  width: 100%;
}
.template-table th,
.template-table td {
  border: 1px solid #eef0f3;
  padding: 4px 8px;
  text-align: left;
  background: #fff;
}
.template-table th {
  background: #f4f5f7;
  position: sticky;
  top: 0;
}
.paste-area {
  display: block;
  width: 100%;
  box-sizing: border-box;
  height: 220px;
  border: none;
  outline: none;
  resize: vertical;
  padding: 10px 12px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12px;
  line-height: 18px;
  tab-size: 12;
  color: #1a2230;
}
.paste-area:focus {
  background: #fcfefe;
}
.paste-stats {
  padding: 6px 10px;
  border-top: 1px solid #eef0f3;
  font-size: 12px;
  color: #4a5361;
  background: #f9fafb;
}
.stat-warn {
  color: #c4392b;
}
.stat-muted {
  color: #8891a0;
}
.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}
.actions-note {
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
.btn.small {
  padding: 4px 10px;
  font-size: 12px;
  margin: 2px 6px 2px 0;
}
.btn:disabled {
  opacity: 0.45;
  cursor: default;
}
.panel-error {
  margin-top: 10px;
  font-size: 12px;
  color: #c4392b;
}
.result {
  margin-top: 14px;
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 13px;
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
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  margin-bottom: 8px;
}
.msg-list {
  margin: 6px 0 0;
  padding-left: 18px;
  line-height: 1.7;
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
.msg-list:empty {
  display: none;
}
.sub-title {
  font-weight: 600;
  font-size: 12px;
  margin: 4px 0 8px;
}
.preview-scroll {
  max-height: 360px;
  overflow: auto;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  background: #fff;
}
.preview-table {
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
  white-space: nowrap;
  min-width: 100%;
}
.preview-table th,
.preview-table td {
  border-right: 1px solid #eef0f3;
  border-bottom: 1px solid #eef0f3;
  padding: 4px 8px;
  text-align: left;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  background: #fff;
}
.preview-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f4f5f7;
}
.preview-table .col-line {
  color: #b4bac4;
  text-align: right;
}
.preview-table tr.row-error td {
  background: #fffafa;
}
.preview-table td.cell-error {
  background: #fde3e0 !important;
  color: #a12e22;
  font-weight: 600;
  outline: 1px solid #f0a69d;
  outline-offset: -1px;
}
.tag {
  display: inline-block;
  padding: 0 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
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
.mono {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.more {
  font-size: 12px;
  color: #8891a0;
  margin-top: 4px;
}
.confirm-box {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #b9dfdf;
}
.confirm-summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.apply-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.confirm {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #c4392b;
}
.export-table {
  border-collapse: collapse;
  font-size: 12px;
  width: 100%;
}
.export-table th,
.export-table td {
  border: 1px solid #eef0f3;
  padding: 5px 8px;
  text-align: left;
}
.export-table th {
  background: #f9fafb;
}
.muted-text {
  color: #b4bac4;
}
.dump-box {
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  padding: 12px 14px;
  margin: 10px 0 18px;
  background: #fcfcfd;
}
.dump-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.dump-title {
  font-size: 13px;
  font-weight: 700;
}
.dump-desc {
  font-size: 12px;
  color: #8891a0;
  margin-top: 4px;
  line-height: 1.6;
  max-width: 640px;
}
.dump-cmd {
  margin: 10px 0 0;
  padding: 8px 10px;
  background: #1a2230;
  color: #e2e5ea;
  border-radius: 6px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
.dump-error {
  color: #c4392b;
}
.sub-heading {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 2px;
}
.export-message {
  margin-top: 10px;
  font-size: 12px;
  color: #4a5361;
}
@media (max-width: 640px) {
  .field {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
</style>
