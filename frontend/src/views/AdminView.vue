<script setup lang="ts">
import { onMounted, ref } from "vue";
import AccessUsersPanel from "../components/AccessUsersPanel.vue";
import { fetchAdminTablePage, fetchAdminTables, fetchAuthConfig, ssoLoginUrl, type AuthConfig, type TablePage } from "../api/admin";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();

const authConfig = ref<AuthConfig | null>(null);
const password = ref("");
const tab = ref<"tables" | "access">("tables");
const ssoError = ref<string | null>(null);
// 예외 타입/메시지 — 토큰/자격증명이 아니라 순수 진단 정보라 화면에 그대로 보여줘도
// 안전하다. 서버 로그를 직접 열어보지 않아도 실제 SSO 브로커 연동 시 원인을 바로
// 알 수 있게 한다(a-ims-prod가 ADFS 연동 중 겪은 문제를 보고 추가한 패턴).
const ssoErrorDetail = ref<string | null>(null);

const SSO_ERROR_MESSAGES: Record<string, string> = {
  sso_not_configured: "SSO가 설정되지 않았습니다.",
  auth_failed: "SSO 인증에 실패했습니다.",
  broker_unreachable: "SSO 브로커 통신에 실패했습니다. 잠시 후 다시 시도해주세요.",
  missing_claim: "필요한 사용자 식별 정보를 받지 못했습니다.",
  not_registered: "등록되지 않은 계정입니다. 관리자에게 등록을 요청해주세요.",
};

const tables = ref<string[]>([]);
const selectedTable = ref<string | null>(null);
const tablePage = ref<TablePage | null>(null);
const tableLoading = ref(false);
const tableError = ref<string | null>(null);

// SSO 콜백은 /admin#token=...&role=...&name=... (성공) 또는 /admin#error=코드 (실패)로
// 돌아온다(쿼리스트링이 아닌 URL 프래그먼트라 서버 로그/리퍼러에 안 남음). 페이지 로드
// 시 1회만 읽고 지운다.
function consumeSsoCallbackHash() {
  const hash = window.location.hash;
  if (hash.startsWith("#error=")) {
    const params = new URLSearchParams(hash.slice(1));
    const code = params.get("error") ?? "";
    ssoError.value = SSO_ERROR_MESSAGES[code] ?? `SSO 로그인에 실패했습니다. (${code})`;
    ssoErrorDetail.value = params.get("detail");
    history.replaceState(null, "", window.location.pathname);
    return;
  }
  if (!hash.startsWith("#token=")) return;
  const params = new URLSearchParams(hash.slice(1));
  const token = params.get("token");
  const role = params.get("role") ?? "user";
  const name = params.get("name");
  if (token) {
    auth.setSessionFromCallback(token, role, name);
  }
  history.replaceState(null, "", window.location.pathname);
}

async function onLoginSubmit() {
  const ok = await auth.login(password.value);
  password.value = "";
  if (ok) {
    await loadTables();
  }
}

async function loadTables() {
  if (!auth.token) return;
  tables.value = await fetchAdminTables(auth.token);
}

async function selectTable(name: string, page = 1) {
  if (!auth.token) return;
  selectedTable.value = name;
  tableLoading.value = true;
  tableError.value = null;
  try {
    tablePage.value = await fetchAdminTablePage(auth.token, name, page);
  } catch (err: any) {
    tableError.value = err?.response?.data?.detail ?? "조회에 실패했습니다.";
    tablePage.value = null;
  } finally {
    tableLoading.value = false;
  }
}

function goToPage(page: number) {
  if (selectedTable.value) selectTable(selectedTable.value, page);
}

async function onLogout() {
  await auth.logout();
  tables.value = [];
  selectedTable.value = null;
  tablePage.value = null;
  tab.value = "tables";
}

onMounted(async () => {
  consumeSsoCallbackHash();
  authConfig.value = await fetchAuthConfig().catch(() => null);
  if (auth.isAuthenticated) {
    await loadTables();
  }
});
</script>

<template>
  <div class="admin">
    <header class="topbar">
      <div class="brand">
        <div class="brand-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
          </svg>
        </div>
        <div>
          <div class="title">관리자 · DB 테이블 조회</div>
          <div class="subtitle">시스템이 사용하는 테이블을 조회 전용으로 확인합니다.</div>
        </div>
      </div>
      <div class="header-actions">
        <span v-if="auth.isAuthenticated && auth.name" class="user-badge">{{ auth.name }}<span v-if="auth.isAdmin" class="admin-tag">admin</span></span>
        <button v-if="auth.isAuthenticated" type="button" class="logout-btn" @click="onLogout">로그아웃</button>
        <RouterLink to="/" class="back-link">← 대시보드로</RouterLink>
      </div>
    </header>

    <main class="body">
      <div v-if="!auth.isAuthenticated" class="login-card">
        <h2>관리자 로그인</h2>

        <a v-if="authConfig?.auth_mode === 'sso'" :href="ssoLoginUrl()" class="sso-btn">회사 계정으로 로그인</a>

        <template v-if="authConfig?.local_login_available">
          <div v-if="authConfig?.auth_mode === 'sso'" class="local-login-divider">또는 관리자 비밀번호로</div>
          <form @submit.prevent="onLoginSubmit">
            <input v-model="password" type="password" placeholder="비밀번호" autofocus />
            <button type="submit" :disabled="auth.loading">{{ auth.loading ? "확인 중..." : "로그인" }}</button>
          </form>
        </template>

        <div v-if="ssoError" class="login-error">
          {{ ssoError }}
          <div v-if="ssoErrorDetail" class="login-error-detail">{{ ssoErrorDetail }}</div>
        </div>
        <div v-if="auth.error" class="login-error">{{ auth.error }}</div>
      </div>

      <div v-else class="admin-body-wrap">
        <div v-if="auth.isAdmin" class="tabs">
          <button type="button" :class="{ active: tab === 'tables' }" @click="tab = 'tables'">테이블 조회</button>
          <button type="button" :class="{ active: tab === 'access' }" @click="tab = 'access'">접근 권한 관리</button>
        </div>

        <AccessUsersPanel v-if="tab === 'access' && auth.isAdmin" />

        <div v-else class="admin-body">
          <aside class="table-list">
            <div class="table-list-label">테이블</div>
            <button
              v-for="name in tables"
              :key="name"
              type="button"
              class="table-item"
              :class="{ active: name === selectedTable }"
              @click="selectTable(name)"
            >
              {{ name }}
            </button>
          </aside>

          <section class="table-view">
            <div v-if="!selectedTable" class="empty">왼쪽에서 조회할 테이블을 선택하세요.</div>
            <div v-else-if="tableLoading" class="empty">불러오는 중...</div>
            <div v-else-if="tableError" class="empty error">{{ tableError }}</div>
            <template v-else-if="tablePage">
              <div class="table-view-header">
                <span class="table-name">{{ tablePage.table_name }}</span>
                <span class="table-total">총 {{ tablePage.total }}건</span>
              </div>
              <div class="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th v-for="col in tablePage.columns" :key="col">{{ col }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, i) in tablePage.rows" :key="i">
                      <td v-for="col in tablePage.columns" :key="col">{{ row[col] }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="pagination">
                <button type="button" :disabled="tablePage.page <= 1" @click="goToPage(tablePage.page - 1)">이전</button>
                <span>{{ tablePage.page }} / {{ Math.max(1, Math.ceil(tablePage.total / tablePage.page_size)) }}</span>
                <button
                  type="button"
                  :disabled="tablePage.page * tablePage.page_size >= tablePage.total"
                  @click="goToPage(tablePage.page + 1)"
                >
                  다음
                </button>
              </div>
            </template>
          </section>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.admin {
  min-height: 100vh;
  background: #f4f5f7;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  color: #1a2230;
}
.topbar {
  background: #fff;
  border-bottom: 1px solid #e2e5ea;
  padding: 24px 32px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
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
.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-badge {
  font-size: 13px;
  color: #4a5361;
  display: flex;
  align-items: center;
  gap: 6px;
}
.admin-tag {
  font-size: 10px;
  font-weight: 700;
  color: #0f8a8a;
  border: 1px solid #0f8a8a;
  border-radius: 4px;
  padding: 1px 6px;
}
.back-link,
.logout-btn {
  font-size: 13px;
  font-weight: 600;
  color: #4a5361;
  text-decoration: none;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  padding: 7px 14px;
  white-space: nowrap;
  background: #fff;
  cursor: pointer;
}
.back-link:hover,
.logout-btn:hover {
  background: #f4f5f7;
}
.body {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px 60px;
}
.login-card {
  max-width: 320px;
  margin: 60px auto 0;
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 24px 28px;
  text-align: center;
}
.login-card h2 {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 16px;
}
.sso-btn {
  display: block;
  padding: 9px 12px;
  border-radius: 6px;
  background: #0f8a8a;
  color: #fff;
  font-weight: 600;
  font-size: 13px;
  text-decoration: none;
}
.local-login-divider {
  font-size: 11px;
  color: #b4bac4;
  margin: 14px 0 10px;
}
.login-card form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.login-card input {
  padding: 9px 12px;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  font-size: 13px;
}
.login-card button {
  padding: 9px 12px;
  border: none;
  border-radius: 6px;
  background: #0f8a8a;
  color: #fff;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}
.login-card button:disabled {
  opacity: 0.6;
  cursor: default;
}
.login-error {
  margin-top: 12px;
  font-size: 12px;
  color: #c4392b;
}
.login-error-detail {
  margin-top: 4px;
  font-size: 11px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  color: #96382f;
  opacity: 0.85;
  word-break: break-all;
}
.admin-body-wrap {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.tabs {
  display: flex;
  gap: 6px;
}
.tabs button {
  padding: 8px 16px;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  background: #fff;
  font-size: 13px;
  font-weight: 600;
  color: #4a5361;
  cursor: pointer;
}
.tabs button.active {
  background: #0f8a8a;
  border-color: #0f8a8a;
  color: #fff;
}
.admin-body {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.table-list {
  width: 220px;
  flex: 0 0 auto;
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.table-list-label {
  font-size: 11px;
  color: #b4bac4;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.table-item {
  text-align: left;
  padding: 8px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  font-size: 13px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  color: #4a5361;
  cursor: pointer;
}
.table-item:hover {
  background: #f4f5f7;
}
.table-item.active {
  background: #0f8a8a;
  color: #fff;
}
.table-view {
  flex: 1;
  min-width: 0;
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 16px;
}
.empty {
  color: #8891a0;
  font-size: 13px;
  padding: 40px 0;
  text-align: center;
}
.empty.error {
  color: #c4392b;
}
.table-view-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 10px;
}
.table-name {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 700;
  font-size: 14px;
}
.table-total {
  font-size: 12px;
  color: #8891a0;
}
.table-scroll {
  overflow-x: auto;
  max-height: 560px;
  overflow-y: auto;
}
table {
  border-collapse: collapse;
  font-size: 12px;
  white-space: nowrap;
}
th,
td {
  border: 1px solid #eef0f3;
  padding: 6px 10px;
  text-align: left;
}
th {
  background: #f9fafb;
  position: sticky;
  top: 0;
}
.pagination {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: center;
  margin-top: 14px;
  font-size: 12px;
}
.pagination button {
  padding: 5px 12px;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}
.pagination button:disabled {
  opacity: 0.4;
  cursor: default;
}
</style>
