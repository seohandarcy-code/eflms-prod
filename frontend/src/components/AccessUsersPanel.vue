<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import {
  createAccessUser,
  deleteAccessUser,
  fetchAccessUsers,
  updateAccessUser,
  type AllowedUser,
} from "../api/admin";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();

const users = ref<AllowedUser[]>([]);
const loading = ref(false);
const errorMsg = ref<string | null>(null);

const newUser = reactive({ sso_id: "", name: "", team: "", is_admin: false });
const editingId = ref<string | null>(null);
const editDraft = reactive({ name: "", team: "", is_admin: false });

async function load() {
  if (!auth.token) return;
  loading.value = true;
  errorMsg.value = null;
  try {
    users.value = await fetchAccessUsers(auth.token);
  } catch (err: any) {
    errorMsg.value = err?.response?.data?.detail ?? "목록을 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
}

async function onCreate() {
  if (!auth.token || !newUser.sso_id || !newUser.name) return;
  errorMsg.value = null;
  try {
    await createAccessUser(auth.token, {
      sso_id: newUser.sso_id,
      name: newUser.name,
      team: newUser.team || null,
      is_admin: newUser.is_admin,
    });
    newUser.sso_id = "";
    newUser.name = "";
    newUser.team = "";
    newUser.is_admin = false;
    await load();
  } catch (err: any) {
    errorMsg.value = err?.response?.data?.detail ?? "등록에 실패했습니다.";
  }
}

function startEdit(user: AllowedUser) {
  editingId.value = user.sso_id;
  editDraft.name = user.name;
  editDraft.team = user.team ?? "";
  editDraft.is_admin = user.is_admin;
}

function cancelEdit() {
  editingId.value = null;
}

async function saveEdit(ssoId: string) {
  if (!auth.token) return;
  errorMsg.value = null;
  try {
    await updateAccessUser(auth.token, ssoId, {
      name: editDraft.name,
      team: editDraft.team || null,
      is_admin: editDraft.is_admin,
    });
    editingId.value = null;
    await load();
  } catch (err: any) {
    errorMsg.value = err?.response?.data?.detail ?? "수정에 실패했습니다.";
  }
}

async function onDelete(ssoId: string) {
  if (!auth.token) return;
  errorMsg.value = null;
  try {
    await deleteAccessUser(auth.token, ssoId);
    await load();
  } catch (err: any) {
    errorMsg.value = err?.response?.data?.detail ?? "삭제에 실패했습니다.";
  }
}

onMounted(load);
</script>

<template>
  <div class="access-panel">
    <form class="new-user-form" @submit.prevent="onCreate">
      <input v-model="newUser.sso_id" placeholder="sso_id (예: user@company.com)" />
      <input v-model="newUser.name" placeholder="이름" />
      <input v-model="newUser.team" placeholder="팀 (선택)" />
      <label class="admin-check"><input v-model="newUser.is_admin" type="checkbox" /> admin</label>
      <button type="submit">등록</button>
    </form>

    <div v-if="errorMsg" class="error">{{ errorMsg }}</div>
    <div v-if="loading" class="empty">불러오는 중...</div>

    <table v-else class="access-table">
      <thead>
        <tr>
          <th>sso_id</th>
          <th>이름</th>
          <th>팀</th>
          <th>admin</th>
          <th>등록일</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.sso_id">
          <td class="mono">{{ user.sso_id }}</td>
          <template v-if="editingId === user.sso_id">
            <td><input v-model="editDraft.name" /></td>
            <td><input v-model="editDraft.team" /></td>
            <td><input v-model="editDraft.is_admin" type="checkbox" /></td>
            <td class="mono">{{ user.created_at }}</td>
            <td class="actions">
              <button type="button" @click="saveEdit(user.sso_id)">저장</button>
              <button type="button" @click="cancelEdit">취소</button>
            </td>
          </template>
          <template v-else>
            <td>{{ user.name }}</td>
            <td>{{ user.team ?? "-" }}</td>
            <td>{{ user.is_admin ? "✓" : "" }}</td>
            <td class="mono">{{ user.created_at }}</td>
            <td class="actions">
              <button type="button" @click="startEdit(user)">수정</button>
              <button type="button" class="danger" @click="onDelete(user.sso_id)">삭제</button>
            </td>
          </template>
        </tr>
        <tr v-if="users.length === 0">
          <td colspan="6" class="empty">등록된 계정이 없습니다.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.access-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.new-user-form {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.new-user-form input {
  padding: 7px 10px;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  font-size: 12px;
}
.admin-check {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #4a5361;
}
.new-user-form button {
  padding: 7px 14px;
  border: none;
  border-radius: 6px;
  background: #0f8a8a;
  color: #fff;
  font-weight: 600;
  font-size: 12px;
  cursor: pointer;
}
.error {
  font-size: 12px;
  color: #c4392b;
}
.empty {
  color: #8891a0;
  font-size: 13px;
  padding: 20px 0;
  text-align: center;
}
.access-table {
  border-collapse: collapse;
  font-size: 12px;
  width: 100%;
}
.access-table th,
.access-table td {
  border: 1px solid #eef0f3;
  padding: 6px 10px;
  text-align: left;
}
.access-table th {
  background: #f9fafb;
}
.access-table input {
  width: 100%;
  padding: 4px 6px;
  border: 1px solid #e2e5ea;
  border-radius: 4px;
  font-size: 12px;
}
.mono {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.actions {
  display: flex;
  gap: 6px;
  white-space: nowrap;
}
.actions button {
  padding: 4px 10px;
  border: 1px solid #e2e5ea;
  border-radius: 5px;
  background: #fff;
  font-size: 11px;
  cursor: pointer;
}
.actions button.danger {
  color: #c4392b;
  border-color: #f0cfc9;
}
</style>
