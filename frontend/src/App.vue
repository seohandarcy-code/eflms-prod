<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchAuthConfig, type AuthConfig } from "./api/admin";
import LoginGate from "./components/LoginGate.vue";
import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

// 인증 설정을 받기 전에는 아무것도 그리지 않는다 — SSO 모드에서 대시보드가 잠깐 401로 깨져 보이지 않게.
const authConfig = ref<AuthConfig | null>(null);
const configLoaded = ref(false);

// SSO 모드면 대시보드·지표설명도 로그인 뒤에만(Stage 16-1). 관리자 화면은 자체 로그인 카드를 쓴다.
const showGate = computed(
  () => !!authConfig.value?.dashboard_login_required && !auth.isAuthenticated && route.name !== "admin"
);

onMounted(async () => {
  // 설정을 못 받으면(백엔드 다운 등) 화면을 그대로 보여준다 — 각 화면이 자체 오류를 보여준다.
  // 첫 경로가 정해진 뒤에 판단한다(그 전엔 route.name이 비어 /admin에서도 로그인 화면이 잠깐 뜰 수 있음).
  const [config] = await Promise.all([fetchAuthConfig().catch(() => null), router.isReady()]);
  authConfig.value = config;
  configLoaded.value = true;
});
</script>

<template>
  <template v-if="configLoaded">
    <LoginGate v-if="showGate" :local-login-available="!!authConfig?.local_login_available" />
    <router-view v-else />
  </template>
</template>
