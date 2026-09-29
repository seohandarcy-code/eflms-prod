<script setup lang="ts">
import { ref } from "vue";
import { fetchAdminTablePage, fetchAdminTables, type TablePage } from "../api/admin";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();

const password = ref("");
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
}

if (auth.isAuthenticated) {
  loadTables();
}
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
        <button v-if="auth.isAuthenticated" type="button" class="logout-btn" @click="onLogout">로그아웃</button>
        <RouterLink to="/" class="back-link">← 대시보드로</RouterLink>
      </div>
    </header>

    <main class="body">
      <div v-if="!auth.isAuthenticated" class="login-card">
        <h2>관리자 로그인</h2>
        <form @submit.prevent="onLoginSubmit">
          <input v-model="password" type="password" placeholder="비밀번호" autofocus />
          <button type="submit" :disabled="auth.loading">{{ auth.loading ? "확인 중..." : "로그인" }}</button>
        </form>
        <div v-if="auth.error" class="login-error">{{ auth.error }}</div>
      </div>

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
