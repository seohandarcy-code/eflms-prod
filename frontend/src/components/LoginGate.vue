<script setup lang="ts">
// SSO 모드(AUTH_MODE=sso)에서 대시보드·지표설명을 열기 전에 보여주는 로그인 화면(Stage 16-1).
// 관리자 화면(/admin)은 자체 로그인 카드가 있어 이 화면을 거치지 않는다.
import { computed } from "vue";
import { useRoute } from "vue-router";
import { ssoLoginUrl } from "../api/admin";
import { useAuthStore } from "../stores/auth";

defineProps<{ localLoginAvailable: boolean }>();

const auth = useAuthStore();
const route = useRoute();
const loginHref = computed(() => ssoLoginUrl(route.fullPath));
</script>

<template>
  <div class="gate">
    <div class="gate-card">
      <div class="brand-icon" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>
      </div>
      <h1>전기설비 수명관리 시스템</h1>
      <p class="hint">회사 계정으로 로그인하면 대시보드를 볼 수 있습니다.</p>

      <a :href="loginHref" class="sso-btn">회사 계정으로 로그인</a>

      <div v-if="auth.ssoError" class="gate-error" role="alert">
        {{ auth.ssoError }}
        <div v-if="auth.ssoErrorDetail" class="gate-error-detail">{{ auth.ssoErrorDetail }}</div>
      </div>

      <RouterLink v-if="localLoginAvailable" to="/admin" class="admin-link">관리자 비밀번호로 로그인</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.gate {
  min-height: 100vh;
  background: #f4f5f7;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 96px 16px 40px;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  color: #1a2230;
}
.gate-card {
  width: 100%;
  max-width: 360px;
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 28px 28px 24px;
  text-align: center;
}
.brand-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #0f8a8a;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 14px;
}
h1 {
  font-size: 17px;
  font-weight: 700;
  margin: 0 0 6px;
}
.hint {
  font-size: 13px;
  color: #8891a0;
  margin: 0 0 20px;
}
.sso-btn {
  display: block;
  padding: 10px 12px;
  border-radius: 6px;
  background: #0f8a8a;
  color: #fff;
  font-weight: 600;
  font-size: 14px;
  text-decoration: none;
}
.sso-btn:hover {
  background: #0c7575;
}
.gate-error {
  margin-top: 14px;
  font-size: 12px;
  color: #c4392b;
  text-align: left;
}
.gate-error-detail {
  margin-top: 4px;
  font-size: 11px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  color: #96382f;
  word-break: break-all;
}
.admin-link {
  display: inline-block;
  margin-top: 16px;
  font-size: 12px;
  color: #8891a0;
}
</style>
