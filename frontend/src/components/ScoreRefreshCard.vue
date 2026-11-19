<script setup lang="ts">
// 관리자 "데이터 입력" 탭 맨 위 — 점수 갱신(Stage 21-1).
// 저장된 입력값으로 오늘(한국 시간) 기준 점수를 다시 계산해 점수만 덮어쓴다(진단 데이터·최근 진단일은 그대로).
// 매일 정기 실행(PDEP CronJob, `python -m app.db.recalculate --as-of today --trigger schedule`)과 같은 서비스.
import { computed, onMounted, ref } from "vue";
import { fetchScoreRefresh, runScoreRefresh, type ScoreRefreshRun, type ScoreRefreshStatus } from "../api/admin";
import { useAuthStore } from "../stores/auth";
import { formatStamp, REFRESH_STATUS_LABEL, REFRESH_TRIGGER_LABEL } from "../utils/scoreRefresh";

const emit = defineEmits<{ refreshed: [] }>();
const auth = useAuthStore();

const status = ref<ScoreRefreshStatus | null>(null);
const loading = ref(false);
const running = ref(false);
const error = ref<string | null>(null);
const showHistory = ref(false);

const last = computed<ScoreRefreshRun | null>(() => status.value?.runs[0] ?? null);
const failedTypes = computed(() => last.value?.types.filter((t) => t.error) ?? []);
const schemaOutdated = computed(() => status.value?.schema && !status.value.schema.ok);
const busy = computed(() => running.value || !!status.value?.running || !!schemaOutdated.value);

function errorText(e: unknown): string {
  const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" ? detail : "요청을 처리하지 못했습니다";
}

async function load() {
  if (!auth.token) return;
  loading.value = true;
  try {
    status.value = await fetchScoreRefresh(auth.token);
    error.value = null;
  } catch (e) {
    error.value = errorText(e);
  } finally {
    loading.value = false;
  }
}

async function refreshNow() {
  if (!auth.token || busy.value) return;
  running.value = true;
  error.value = null;
  try {
    await runScoreRefresh(auth.token);
    emit("refreshed");
  } catch (e) {
    error.value = errorText(e);
  } finally {
    running.value = false;
    await load();
  }
}

onMounted(load);
</script>

<template>
  <section class="card refresh-card">
    <div class="rc-head">
      <div>
        <h3>점수 갱신</h3>
        <p class="card-hint">
          저장된 진단 데이터로 <b>오늘 기준 점수</b>를 다시 계산합니다 — 경과연수·부품 노화처럼 날짜에 따라 바뀌는 감점이 맞춰지고,
          진단 데이터와 최근 진단일은 바뀌지 않습니다.
        </p>
      </div>
      <button type="button" class="rc-btn" :disabled="busy || loading" @click="refreshNow">
        {{ running ? "갱신 중…" : "지금 갱신" }}
      </button>
    </div>

    <div v-if="status" class="rc-auto">
      자동 갱신:
      <template v-if="status.auto.enabled"><b>켜짐</b> — 서버가 시작될 때와 날짜가 바뀌면(점수가 오늘 기준이 아닐 때만, {{ status.auto.check_minutes }}분마다 확인)</template>
      <template v-else><b>꺼짐</b> — "지금 갱신" 또는 명령으로만 갱신됩니다(SCORE_REFRESH_AUTO=false)</template>
    </div>
    <div v-if="schemaOutdated" class="rc-error rc-schema">
      DB 업그레이드 필요(현재 {{ status?.schema.current }} / 최신 {{ status?.schema.head }}) — backend에서
      <code>python -m alembic upgrade head</code> 실행 후 서버를 다시 시작하면 자동으로 오늘 기준 점수가 계산됩니다.
    </div>
    <div v-if="status?.running && !running" class="rc-note">
      다른 데이터 작업({{ status.running.holder }})이 진행 중입니다 — {{ formatStamp(status.running.acquired_at) }} 시작
    </div>
    <div v-if="error" class="rc-error">{{ error }}</div>

    <div v-if="last" class="rc-last" :class="`rc-st-${last.status}`">
      <span class="rc-badge">{{ REFRESH_STATUS_LABEL[last.status] ?? last.status }}</span>
      <span>마지막 갱신 <b>{{ formatStamp(last.finished_at ?? last.started_at) }}</b></span>
      <span>· 기준일 {{ last.as_of ?? "저장된 기준일" }}</span>
      <span>· 설비 {{ last.equipment_count }}대</span>
      <span class="rc-muted">· {{ REFRESH_TRIGGER_LABEL[last.trigger] ?? last.trigger }}</span>
    </div>
    <div v-else-if="!loading && !schemaOutdated" class="rc-muted">아직 갱신 기록이 없습니다.</div>

    <ul v-if="failedTypes.length" class="rc-failed">
      <li v-for="t in failedTypes" :key="t.ef_code"><b>{{ t.ef_code }}</b> 반영 안 됨(이전 점수 유지) — {{ t.error }}</li>
    </ul>

    <button v-if="(status?.runs.length ?? 0) > 1" type="button" class="rc-toggle" @click="showHistory = !showHistory">
      최근 기록 {{ showHistory ? "접기" : "보기" }}
    </button>
    <table v-if="showHistory" class="rc-table">
      <thead>
        <tr><th>#</th><th>시작</th><th>결과</th><th>기준일</th><th>설비</th><th>구분</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in status?.runs ?? []" :key="r.run_id">
          <td>{{ r.run_id }}</td>
          <td>{{ formatStamp(r.started_at) }}</td>
          <td :class="`rc-text-${r.status}`">{{ REFRESH_STATUS_LABEL[r.status] ?? r.status }}</td>
          <td>{{ r.as_of ?? "저장된 기준일" }}</td>
          <td>{{ r.equipment_count }}</td>
          <td>{{ REFRESH_TRIGGER_LABEL[r.trigger] ?? r.trigger }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
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
.rc-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
.rc-btn {
  flex: 0 0 auto;
  height: 34px;
  padding: 0 14px;
  border: 1px solid #0b7474;
  border-radius: 8px;
  background: #0b7474;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.rc-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
.rc-last {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #4a5361;
}
.rc-badge {
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  padding: 2px 8px;
  background: #e3f2f2;
  color: #0b7474;
}
.rc-st-partial .rc-badge,
.rc-st-running .rc-badge {
  background: #fdf3dc;
  color: #a86b00;
}
.rc-st-failed .rc-badge {
  background: #fbe7e7;
  color: #c0392b;
}
.rc-muted {
  color: #8891a0;
  font-size: 12px;
}
.rc-auto {
  font-size: 12px;
  color: #4a5361;
  margin-bottom: 8px;
}
.rc-schema {
  font-weight: 600;
}
.rc-note {
  font-size: 12px;
  color: #a86b00;
  margin-bottom: 8px;
}
.rc-error {
  font-size: 12px;
  color: #c0392b;
  margin-bottom: 8px;
}
ul.rc-failed {
  margin: 8px 0 0;
  padding-left: 18px;
  font-size: 12px;
  color: #c0392b;
}
.rc-toggle {
  margin-top: 10px;
  border: none;
  background: none;
  color: #0b7474;
  font-size: 12px;
  font-weight: 600;
  padding: 0;
  cursor: pointer;
}
.rc-table {
  margin-top: 8px;
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.rc-table th,
.rc-table td {
  text-align: left;
  padding: 5px 8px;
  border-bottom: 1px solid #eef0f3;
}
.rc-table th {
  color: #8891a0;
  font-weight: 600;
}
.rc-text-partial {
  color: #a86b00;
}
.rc-text-failed {
  color: #c0392b;
}
</style>
