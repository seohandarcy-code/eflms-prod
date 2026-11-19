<script setup lang="ts">
import { computed } from "vue";
import { useAuthStore } from "../stores/auth";
import { badgeView } from "../utils/userBadge";

// 화면 위 맨 오른쪽 로그인 카드(메인·관리자 화면 공통, 2026-11-19 시안 D) — 동그라미(이름 첫 글자),
// "홍길동님 / 역할", 로그아웃 아이콘 버튼. 로그인한 사람이 없고 로컬 모드면 VITE_PREVIEW_USER로 미리보기만(세션·권한 없음).
const emit = defineEmits<{ "logged-out": [] }>();
const auth = useAuthStore();

const view = computed(() =>
  badgeView({ token: auth.token, role: auth.role, name: auth.name }, auth.authMode, import.meta.env.VITE_PREVIEW_USER),
);

async function onLogout() {
  if (!view.value || view.value.preview) return;
  await auth.logout();
  emit("logged-out");
}
</script>

<template>
  <div v-if="view" class="ub" :class="`ub-${view.role}`" :title="view.preview ? '로컬 미리보기 — 실제 로그인 아님' : undefined">
    <span class="ub-avatar" aria-hidden="true">
      <template v-if="view.initial">{{ view.initial }}</template>
      <svg v-else-if="view.icon === 'key'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="7.5" cy="15.5" r="4.5" />
        <path d="M10.7 12.3 20 3" />
        <path d="M16 7l3 3" />
      </svg>
      <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
      </svg>
    </span>
    <span class="ub-text">
      <span class="ub-title">{{ view.title }}</span>
      <span v-if="view.subtitle" class="ub-sub">{{ view.subtitle }}</span>
    </span>
    <button
      type="button"
      class="ub-logout"
      aria-label="로그아웃"
      :title="view.preview ? '로그아웃 (로컬 미리보기 — 동작 안 함)' : '로그아웃'"
      @click="onLogout"
    >
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
        <polyline points="16 17 21 12 16 7" />
        <line x1="21" y1="12" x2="9" y2="12" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.ub {
  --ub-accent: #6b7480;
  --ub-soft: #eef1f4;
  flex: 0 0 auto;
  height: 56px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 0 8px;
  background: #fff;
  white-space: nowrap;
}
.ub-admin {
  --ub-accent: #0b7474;
  --ub-soft: #e3f2f2;
}
.ub-user {
  --ub-accent: #2560b0;
  --ub-soft: #e8f0fb;
}
.ub-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--ub-soft);
  color: var(--ub-accent);
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ub-general .ub-avatar {
  color: #4a5361;
}
.ub-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.ub-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a2230;
}
.ub-sub {
  font-size: 11px;
  font-weight: 700;
  color: var(--ub-accent);
}
.ub-logout {
  width: 32px;
  height: 32px;
  margin-left: 4px;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  background: #fff;
  color: #4a5361;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.ub-logout:hover,
.ub-logout:focus-visible {
  background: #f4f5f7;
}
</style>
