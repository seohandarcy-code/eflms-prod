<script setup lang="ts">
// 관리자 "테이블 조회" 탭의 SQL 조회 화면 (Stage 16-5, admin 전용) — DB 관리 프로그램처럼
// 왼쪽 테이블 목록 · 오른쪽 위 SQL 입력창 · 아래 결과 그리드.
// 조회(SELECT/WITH)만, 허용 목록 테이블만, 최대 1,000행·5초 — 백엔드가 DB 쪽에서 강제한다.
import { computed, nextTick, onMounted, ref } from "vue";
import { runSqlQuery, type SqlQueryResult } from "../api/admin";
import { useAuthStore } from "../stores/auth";
import { defaultTableQuery, formatCell, pushHistory, sqlToRun, toCsv } from "../utils/sqlResult";

const props = defineProps<{ tables: string[] }>();

const auth = useAuthStore();

const HISTORY_KEY = "eflms.sqlHistory";

const sql = ref("");
const editor = ref<HTMLTextAreaElement | null>(null);
const gutter = ref<HTMLDivElement | null>(null);
const activeTable = ref<string | null>(null);
const tableFilter = ref("");

const running = ref(false);
const result = ref<SqlQueryResult | null>(null);
const error = ref<string | null>(null);
const lastSql = ref<string | null>(null);

const history = ref<string[]>(loadHistory());
const showHistory = ref(false);

const lineCount = computed(() => Math.max(1, sql.value.split("\n").length));
const filteredTables = computed(() => {
  const q = tableFilter.value.trim().toLowerCase();
  return q ? props.tables.filter((t) => t.toLowerCase().includes(q)) : props.tables;
});

function loadHistory(): string[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === "string").slice(0, 10) : [];
  } catch {
    return [];
  }
}

function saveHistory() {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value));
  } catch {
    // 저장소를 못 쓰면 이번 화면에서만 기억
  }
}

function syncScroll() {
  if (gutter.value && editor.value) gutter.value.scrollTop = editor.value.scrollTop;
}

async function execute(text?: string) {
  if (!auth.token || running.value) return;
  const el = editor.value;
  const query = text ?? sqlToRun(sql.value, el?.selectionStart ?? 0, el?.selectionEnd ?? 0);
  if (!query) {
    error.value = "SQL을 입력하세요.";
    result.value = null;
    return;
  }
  running.value = true;
  error.value = null;
  lastSql.value = query;
  try {
    result.value = await runSqlQuery(auth.token, query);
    history.value = pushHistory(history.value, query);
    saveHistory();
  } catch (err: any) {
    result.value = null;
    error.value = err?.response?.data?.detail ?? "조회에 실패했습니다.";
  } finally {
    running.value = false;
  }
}

async function selectTable(name: string) {
  activeTable.value = name;
  sql.value = defaultTableQuery(name);
  await nextTick();
  syncScroll();
  await execute(sql.value);
}

function useHistory(item: string) {
  sql.value = item;
  showHistory.value = false;
  editor.value?.focus();
}

function onKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    execute();
    return;
  }
  // Tab은 포커스 이동 대신 들여쓰기(공백 2칸)
  if (event.key === "Tab" && !event.shiftKey && editor.value) {
    event.preventDefault();
    const el = editor.value;
    const start = el.selectionStart;
    sql.value = sql.value.slice(0, start) + "  " + sql.value.slice(el.selectionEnd);
    nextTick(() => el.setSelectionRange(start + 2, start + 2));
  }
}

function clearEditor() {
  sql.value = "";
  editor.value?.focus();
}

function downloadCsv() {
  if (!result.value) return;
  const blob = new Blob([toCsv(result.value.columns, result.value.rows)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${activeTable.value ?? "query"}_result.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

onMounted(() => editor.value?.focus());
</script>

<template>
  <div class="sql-layout">
    <aside class="table-list">
      <div class="table-list-label">테이블 {{ tables.length }}</div>
      <input v-model="tableFilter" class="table-filter" type="search" placeholder="테이블 찾기" />
      <div class="table-items">
        <button
          v-for="name in filteredTables"
          :key="name"
          type="button"
          class="table-item"
          :class="{ active: name === activeTable }"
          :title="`SELECT * FROM ${name} LIMIT 100`"
          @click="selectTable(name)"
        >
          {{ name }}
        </button>
      </div>
    </aside>

    <section class="work">
      <div class="editor-card">
        <div class="toolbar">
          <button type="button" class="run-btn" :disabled="running" @click="execute()">
            <span aria-hidden="true">▶</span> {{ running ? "실행 중..." : "실행" }}
          </button>
          <span class="shortcut">Ctrl+Enter · 선택한 부분만 실행</span>
          <span class="spacer" />
          <div class="history-wrap">
            <button type="button" class="tool-btn" :disabled="!history.length" @click="showHistory = !showHistory">
              최근 실행 {{ history.length }}
            </button>
            <ul v-if="showHistory && history.length" class="history-menu">
              <li v-for="(item, i) in history" :key="i">
                <button type="button" :title="item" @click="useHistory(item)">{{ item }}</button>
              </li>
            </ul>
          </div>
          <button type="button" class="tool-btn" @click="clearEditor">지우기</button>
        </div>
        <div class="editor">
          <div ref="gutter" class="gutter" aria-hidden="true">
            <div v-for="n in lineCount" :key="n">{{ n }}</div>
          </div>
          <textarea
            ref="editor"
            v-model="sql"
            class="code"
            spellcheck="false"
            autocomplete="off"
            aria-label="SQL 입력"
            placeholder="SELECT * FROM equipment LIMIT 100;  — 왼쪽 테이블을 누르면 자동으로 채워집니다"
            @keydown="onKeydown"
            @scroll="syncScroll"
          ></textarea>
        </div>
        <div class="editor-note">조회(SELECT / WITH)만 · 목록의 테이블만 · 최대 1,000행 · 5초</div>
      </div>

      <div class="result-card">
        <div class="result-bar">
          <template v-if="result">
            <span class="ok-dot" aria-hidden="true" />
            <span class="result-meta"><b>{{ result.row_count.toLocaleString() }}행</b> · {{ result.elapsed_ms }}ms</span>
            <span v-if="result.truncated" class="truncated">최대 {{ result.max_rows.toLocaleString() }}행까지만 표시 — LIMIT/OFFSET으로 나눠 보세요</span>
            <span class="spacer" />
            <button type="button" class="tool-btn" :disabled="!result.rows.length" @click="downloadCsv">CSV 내려받기</button>
          </template>
          <template v-else-if="error">
            <span class="err-dot" aria-hidden="true" />
            <span class="result-meta">오류</span>
          </template>
          <span v-else class="result-meta muted">결과</span>
        </div>

        <div v-if="running && !result" class="placeholder">실행 중...</div>
        <div v-else-if="error" class="sql-error" role="alert">
          <pre>{{ error }}</pre>
          <div v-if="lastSql" class="sql-error-query">{{ lastSql }}</div>
        </div>
        <div v-else-if="!result" class="placeholder">왼쪽에서 테이블을 누르거나 SQL을 입력하고 실행하세요.</div>
        <div v-else-if="!result.columns.length" class="placeholder">반환된 컬럼이 없습니다.</div>
        <div v-else class="grid-scroll">
          <table class="grid">
            <thead>
              <tr>
                <th class="rownum">#</th>
                <th v-for="(col, ci) in result.columns" :key="ci">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in result.rows" :key="ri">
                <td class="rownum">{{ ri + 1 }}</td>
                <td
                  v-for="(cell, ci) in row"
                  :key="ci"
                  :class="{ null: cell === null, num: typeof cell === 'number' }"
                  :title="formatCell(cell)"
                >
                  {{ formatCell(cell) }}
                </td>
              </tr>
              <tr v-if="!result.rows.length">
                <td :colspan="result.columns.length + 1" class="empty-row">0행</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.sql-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.table-list {
  width: 230px;
  flex: 0 0 auto;
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: sticky;
  top: 12px;
  /* 화면 높이에 맞추되, 확대·작은 창에서도 목록이 쓸 만한 크기는 남긴다 */
  max-height: max(240px, calc(100vh - 40px));
  box-sizing: border-box;
}
.table-list-label {
  font-size: 11px;
  color: #b4bac4;
  font-weight: 700;
  text-transform: uppercase;
}
.table-filter {
  flex: 0 0 auto;
  padding: 6px 8px;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  font-size: 12px;
}
.table-items {
  /* 남은 높이를 채우고 그 안에서만 스크롤 — min-height: 0이 없으면 넘칠 때 스크롤 대신 항목이 눌린다 */
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.table-item {
  /* 세로 flex 안의 항목은 기본이 줄어들기(flex-shrink: 1)라, 테이블이 많으면 글자가 위아래로 겹쳤다(Stage 16-7) */
  flex: 0 0 auto;
  line-height: 18px;
  text-align: left;
  padding: 6px 8px;
  border: none;
  border-radius: 6px;
  background: transparent;
  font-size: 12px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  color: #4a5361;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.table-item:hover {
  background: #f4f5f7;
}
.table-item.active {
  background: #0f8a8a;
  color: #fff;
}
.work {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.editor-card,
.result-card {
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  overflow: hidden;
}
.toolbar,
.result-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-bottom: 1px solid #eef0f3;
  background: #f9fafb;
  font-size: 12px;
}
.spacer {
  flex: 1;
}
.run-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  background: #0f8a8a;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
.run-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.shortcut {
  color: #8891a0;
}
.tool-btn {
  padding: 5px 10px;
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
.history-wrap {
  position: relative;
}
.history-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 4px);
  z-index: 5;
  width: 420px;
  max-width: 70vw;
  margin: 0;
  padding: 4px;
  list-style: none;
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(26, 34, 48, 0.12);
}
.history-menu button {
  width: 100%;
  text-align: left;
  padding: 6px 8px;
  border: none;
  background: transparent;
  border-radius: 4px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px;
  color: #1a2230;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
}
.history-menu button:hover {
  background: #f4f5f7;
}
.editor {
  display: flex;
  height: 170px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 13px;
  line-height: 20px;
}
.gutter {
  flex: 0 0 auto;
  min-width: 38px;
  padding: 8px 8px 8px 0;
  text-align: right;
  color: #b4bac4;
  background: #f9fafb;
  border-right: 1px solid #eef0f3;
  overflow: hidden;
  user-select: none;
}
.code {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  padding: 8px 10px;
  font: inherit;
  line-height: inherit;
  color: #1a2230;
  white-space: pre;
  overflow: auto;
}
.editor-note {
  padding: 5px 10px;
  border-top: 1px solid #eef0f3;
  font-size: 11px;
  color: #8891a0;
}
.result-meta {
  color: #4a5361;
}
.result-meta.muted {
  color: #8891a0;
}
.ok-dot,
.err-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #0f8a8a;
}
.err-dot {
  background: #c4392b;
}
.truncated {
  color: #9a6400;
}
.placeholder {
  padding: 48px 16px;
  text-align: center;
  font-size: 13px;
  color: #8891a0;
}
.sql-error {
  padding: 14px 16px;
}
.sql-error pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12px;
  color: #c4392b;
}
.sql-error-query {
  margin-top: 8px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px;
  color: #8891a0;
  white-space: pre-wrap;
}
.grid-scroll {
  overflow: auto;
  max-height: 520px;
}
.grid {
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
  white-space: nowrap;
  min-width: 100%;
}
.grid th,
.grid td {
  border-right: 1px solid #eef0f3;
  border-bottom: 1px solid #eef0f3;
  padding: 5px 10px;
  text-align: left;
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.grid th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f4f5f7;
  font-weight: 700;
  color: #1a2230;
}
.grid td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.grid td.null {
  color: #b4bac4;
  font-style: italic;
}
.grid .rownum {
  position: sticky;
  left: 0;
  background: #f9fafb;
  color: #b4bac4;
  text-align: right;
  min-width: 36px;
}
.grid th.rownum {
  z-index: 2;
  background: #f4f5f7;
}
.grid tbody tr:hover td:not(.rownum) {
  background: #f3fafa;
}
.empty-row {
  text-align: center !important;
  color: #8891a0;
}
@media (max-width: 760px) {
  .sql-layout {
    flex-direction: column;
  }
  .table-list {
    width: 100%;
    position: static;
    max-height: 220px;
  }
}
</style>
