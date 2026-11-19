<script setup lang="ts">
// 관리자 "변경 이력" 탭(Stage 21-4) — 임포트·교체·행 편집·참고표 넣기/리셋·되돌리기 기록과 되돌리기.
// 목록에서 변경을 고르면 행별 바뀌기 전후 값을 보여 주고, 되돌릴 수 있으면 "되돌리기" → 확인 → 실행(브라우저 대화상자 없이).
// 되돌리면 이전 값·이전 반영일로 복원되고 점수는 오늘 기준으로 다시 계산된다. 최근 변경부터만 되돌릴 수 있다.
import { computed, onMounted, ref } from "vue";
import { fetchChange, fetchChanges, undoChange, type DataChangeDetail, type DataChangeItem } from "../api/admin";
import { useAuthStore } from "../stores/auth";
import { ACTION_LABEL, ACTOR_LABEL, fieldDiffs, rowKeyLabel } from "../utils/changeHistory";
import { formatStamp } from "../utils/scoreRefresh";

const auth = useAuthStore();
const changes = ref<DataChangeItem[]>([]);
const selected = ref<DataChangeDetail | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const confirming = ref(false);
const undoing = ref(false);
const message = ref<string | null>(null);

const ROW_LIMIT = 50;
const shownRows = computed(() => selected.value?.rows.slice(0, ROW_LIMIT) ?? []);

function errorText(e: unknown): string {
  const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" ? detail : "요청을 처리하지 못했습니다";
}

async function load() {
  if (!auth.token) return;
  loading.value = true;
  try {
    changes.value = await fetchChanges(auth.token);
    error.value = null;
  } catch (e) {
    error.value = errorText(e);
  } finally {
    loading.value = false;
  }
}

async function select(id: number) {
  if (!auth.token) return;
  confirming.value = false;
  message.value = null;
  try {
    selected.value = await fetchChange(auth.token, id);
  } catch (e) {
    error.value = errorText(e);
  }
}

async function runUndo() {
  if (!auth.token || !selected.value) return;
  undoing.value = true;
  try {
    const id = selected.value.change_id;
    const result = await undoChange(auth.token, id, false);
    confirming.value = false;
    await load();
    await select(id); // 상세를 다시 읽으면 문구가 지워지므로 그 뒤에 표시
    message.value = `#${id}을 되돌렸습니다(되돌리기 기록 #${result.undo_change_id}) — 이전 값·반영일로 복원, 점수는 오늘 기준으로 다시 계산했습니다.`;
  } catch (e) {
    error.value = errorText(e);
  } finally {
    undoing.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="ch-panel">
    <section class="card">
      <h3>변경 이력</h3>
      <p class="card-hint">
        데이터 입력(붙여넣기·행 편집·교체)과 참고표 넣기·리셋이 바뀌기 전후 값과 함께 남습니다. 값이 지금과 같은 행은 반영하지 않아 기록도 없습니다.
        되돌리면 이전 값과 이전 반영일로 복원되고 점수는 오늘 기준으로 다시 계산됩니다 — 같은 데이터를 그 뒤에 바꾼 변경이 있으면 그것부터 되돌려야 합니다.
      </p>
      <div v-if="error" class="ch-error">{{ error }}</div>
      <table class="ch-table">
        <thead>
          <tr><th>#</th><th>시각</th><th>구분</th><th>대상</th><th>행</th><th>요청</th><th>상태</th></tr>
        </thead>
        <tbody>
          <tr
            v-for="c in changes"
            :key="c.change_id"
            :class="{ active: selected?.change_id === c.change_id, undone: c.status === 'undone' }"
            @click="select(c.change_id)"
          >
            <td>{{ c.change_id }}</td>
            <td>{{ formatStamp(c.created_at) }}</td>
            <td>{{ c.kind_label }}<span v-if="c.undo_of" class="muted"> (#{{ c.undo_of }})</span></td>
            <td>{{ c.ef_code }}<span v-if="c.target_table" class="muted"> · {{ c.target_table }}</span></td>
            <td>{{ c.row_count }}<span v-if="c.unchanged_count" class="muted"> (같음 {{ c.unchanged_count }})</span></td>
            <td>{{ ACTOR_LABEL[c.actor] ?? c.actor }}<span v-if="c.source" class="muted"> · {{ c.source }}</span></td>
            <td>{{ c.status === "undone" ? "되돌림" : "반영" }}</td>
          </tr>
          <tr v-if="!loading && changes.length === 0"><td colspan="7" class="muted">아직 기록이 없습니다.</td></tr>
        </tbody>
      </table>
    </section>

    <section v-if="selected" class="card">
      <div class="ch-head">
        <div>
          <h3>#{{ selected.change_id }} {{ selected.kind_label }} · {{ selected.ef_code }}<template v-if="selected.target_table"> · {{ selected.target_table }}</template></h3>
          <p class="card-hint">
            {{ formatStamp(selected.created_at) }} · {{ ACTOR_LABEL[selected.actor] ?? selected.actor }}
            <template v-if="selected.source"> · {{ selected.source }}</template>
            · 바뀐 행 {{ selected.row_count }}<template v-if="selected.unchanged_count"> · 같아서 건너뛴 행 {{ selected.unchanged_count }}</template>
            <template v-if="selected.status === 'undone'"> · {{ formatStamp(selected.undone_at) }}에 되돌림</template>
          </p>
        </div>
        <div class="ch-actions">
          <template v-if="selected.undo_check.possible">
            <button v-if="!confirming" type="button" class="ch-btn" @click="confirming = true">되돌리기</button>
            <template v-else>
              <span class="ch-confirm">이 변경을 되돌릴까요?</span>
              <button type="button" class="ch-btn danger" :disabled="undoing" @click="runUndo">{{ undoing ? "되돌리는 중…" : "되돌리기 실행" }}</button>
              <button type="button" class="ch-btn ghost" :disabled="undoing" @click="confirming = false">취소</button>
            </template>
          </template>
          <span v-else class="ch-why">{{ selected.undo_check.reason }}</span>
        </div>
      </div>
      <div v-if="message" class="ch-ok">{{ message }}</div>

      <div v-for="(r, i) in shownRows" :key="i" class="ch-row">
        <div class="ch-row-head">
          <span class="ch-tag" :class="`ch-${r.action}`">{{ ACTION_LABEL[r.action] ?? r.action }}</span>
          <b>{{ rowKeyLabel(r.row_key) }}</b>
        </div>
        <table class="ch-diff">
          <tr v-for="d in fieldDiffs(r)" :key="d.name">
            <td class="name">{{ d.name }}</td>
            <td class="before">{{ d.before }}</td>
            <td class="arrow">→</td>
            <td class="after">{{ d.after }}</td>
          </tr>
        </table>
      </div>
      <div v-if="selected.rows.length > ROW_LIMIT" class="muted">외 {{ selected.rows.length - ROW_LIMIT }}행 — 전체는 테이블 조회(data_change_row)에서</div>
    </section>
  </div>
</template>

<style scoped>
.ch-panel {
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
  margin: 0 0 12px;
  line-height: 1.6;
}
.muted {
  color: #8891a0;
}
.ch-error {
  color: #c0392b;
  font-size: 12px;
  margin-bottom: 8px;
}
.ch-ok {
  color: #0b7474;
  font-size: 12px;
  margin-bottom: 8px;
}
.ch-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.ch-table th,
.ch-table td {
  text-align: left;
  padding: 6px 8px;
  border-bottom: 1px solid #eef0f3;
}
.ch-table th {
  color: #8891a0;
  font-weight: 600;
}
.ch-table tbody tr {
  cursor: pointer;
}
.ch-table tbody tr:hover,
.ch-table tbody tr.active {
  background: #f4f8f8;
}
.ch-table tr.undone td {
  color: #a0a7b2;
}
.ch-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}
.ch-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}
.ch-btn {
  height: 32px;
  padding: 0 12px;
  border: 1px solid #0b7474;
  border-radius: 8px;
  background: #fff;
  color: #0b7474;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.ch-btn.danger {
  background: #c0392b;
  border-color: #c0392b;
  color: #fff;
}
.ch-btn.ghost {
  border-color: #e2e5ea;
  color: #4a5361;
}
.ch-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
.ch-confirm {
  font-size: 12px;
  color: #c0392b;
  font-weight: 600;
}
.ch-why {
  font-size: 12px;
  color: #8891a0;
  max-width: 360px;
}
.ch-row {
  border-top: 1px solid #eef0f3;
  padding: 10px 0;
}
.ch-row-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 4px;
}
.ch-tag {
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  padding: 1px 8px;
}
.ch-insert {
  background: #e3f2f2;
  color: #0b7474;
}
.ch-update {
  background: #e8f0fb;
  color: #2560b0;
}
.ch-delete {
  background: #fbe7e7;
  color: #c0392b;
}
.ch-diff {
  font-size: 12px;
  border-collapse: collapse;
}
.ch-diff td {
  padding: 2px 8px 2px 0;
  vertical-align: top;
}
.ch-diff .name {
  color: #8891a0;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.ch-diff .before {
  color: #c0392b;
}
.ch-diff .after {
  color: #0b7474;
}
.ch-diff .arrow {
  color: #b4bac4;
}
</style>
