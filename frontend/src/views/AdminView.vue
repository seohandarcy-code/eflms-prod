<script setup lang="ts">
import UserBadge from "../components/UserBadge.vue";
import { onMounted, ref } from "vue";
import AccessUsersPanel from "../components/AccessUsersPanel.vue";
import DataImportPanel from "../components/DataImportPanel.vue";
import SqlQueryPanel from "../components/SqlQueryPanel.vue";
import { fetchAdminTablePage, fetchAdminTables, fetchAuthConfig, ssoLoginUrl, type AuthConfig, type TablePage } from "../api/admin";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();

const authConfig = ref<AuthConfig | null>(null);
const password = ref("");
const tab = ref<"tables" | "data" | "access">("tables");
// SSO 실패 문구(#error=코드)는 앱 시작 때 auth 스토어가 읽어 둔다(main.ts) — auth.ssoError / ssoErrorDetail.
// detail은 예외 타입/메시지라 토큰·자격증명이 아닌 순수 진단 정보 — 화면에 그대로 보여줘도 안전하다.

const tables = ref<string[]>([]);
const selectedTable = ref<string | null>(null);
const tablePage = ref<TablePage | null>(null);
const tableLoading = ref(false);
const tableError = ref<string | null>(null);

async function onLoginSubmit() {
  const ok = await auth.login(password.value);
  password.value = "";
  if (ok) {
    await loadTables();
  }
}

async function loadTables() {
  // 미등록 SSO 사용자(general)는 대시보드 조회만 — 테이블 조회 API는 403이라 부르지 않는다.
  if (!auth.token || !auth.isRegistered) return;
  tables.value = await fetchAdminTables(auth.token).catch(() => []);
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

// 로그아웃 버튼은 UserBadge(공통) — 세션을 지운 뒤 이 화면 상태만 비운다.
function onLoggedOut() {
  tables.value = [];
  selectedTable.value = null;
  tablePage.value = null;
  tab.value = "tables";
}

onMounted(async () => {
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
          <div class="title">관리자</div>
          <div class="subtitle">DB 테이블 조회 · 데이터 입력 · 접근 권한 관리</div>
        </div>
      </div>
      <div class="header-actions">
        <UserBadge @logged-out="onLoggedOut" />
        <RouterLink to="/" class="back-link">← 대시보드로</RouterLink>
      </div>
    </header>

    <main class="body">
      <div v-if="!auth.isAuthenticated" class="login-card">
        <h2>관리자 로그인</h2>

        <a v-if="authConfig?.auth_mode === 'sso'" :href="ssoLoginUrl('/admin')" class="sso-btn">회사 계정으로 로그인</a>

        <template v-if="authConfig?.local_login_available">
          <div v-if="authConfig?.auth_mode === 'sso'" class="local-login-divider">또는 관리자 비밀번호로</div>
          <form @submit.prevent="onLoginSubmit">
            <input v-model="password" type="password" placeholder="비밀번호" autofocus />
            <button type="submit" :disabled="auth.loading">{{ auth.loading ? "확인 중..." : "로그인" }}</button>
          </form>
        </template>

        <div v-if="auth.ssoError" class="login-error">
          {{ auth.ssoError }}
          <div v-if="auth.ssoErrorDetail" class="login-error-detail">{{ auth.ssoErrorDetail }}</div>
        </div>
        <div v-if="auth.error" class="login-error">{{ auth.error }}</div>
      </div>

      <div v-else-if="!auth.isRegistered" class="login-card">
        <h2>조회 전용 계정</h2>
        <p class="general-note">
          회사 계정 인증은 되었지만 관리자 화면 사용자로 등록되어 있지 않습니다. 대시보드는 그대로 볼 수 있습니다.
          관리자 화면이 필요하면 관리자에게 등록을 요청해주세요.
        </p>
        <RouterLink to="/" class="sso-btn">대시보드로 가기</RouterLink>
      </div>

      <div v-else class="admin-body-wrap">
        <div v-if="auth.isAdmin" class="tabs">
          <button type="button" :class="{ active: tab === 'tables' }" @click="tab = 'tables'">테이블 조회</button>
          <button type="button" :class="{ active: tab === 'data' }" @click="tab = 'data'">데이터 입력</button>
          <button type="button" :class="{ active: tab === 'access' }" @click="tab = 'access'">접근 권한 관리</button>
        </div>

        <!-- 데이터 입력은 다른 탭에 다녀와도 행 편집·붙여넣기 내용이 남게 KeepAlive(Stage 18) -->
        <KeepAlive>
          <DataImportPanel v-if="tab === 'data' && auth.isAdmin" />
        </KeepAlive>
        <AccessUsersPanel v-if="tab === 'access' && auth.isAdmin" />
        <!-- 관리자: SQL 조회(Stage 16-5). 등록 사용자: 테이블을 눌러 보는 조회만(아래) -->
        <SqlQueryPanel v-else-if="tab === 'tables' && auth.isAdmin" :tables="tables" />

        <div v-else-if="!auth.isAdmin" class="admin-body">
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
.back-link {
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
.back-link:hover {
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
.general-note {
  font-size: 13px;
  color: #4a5361;
  line-height: 1.6;
  text-align: left;
  margin: 0 0 16px;
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
