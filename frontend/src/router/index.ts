import { createRouter, createWebHistory } from "vue-router";
import AdminView from "../views/AdminView.vue";
import DashboardView from "../views/DashboardView.vue";
import FacilityGuideView from "../views/FacilityGuideView.vue";
import FormulaGuideView from "../views/FormulaGuideView.vue";
import GuideView from "../views/GuideView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "dashboard", component: DashboardView },
    { path: "/guide", name: "guide", component: GuideView },
    { path: "/guide/facilities", name: "guide-facilities", component: FacilityGuideView },
    { path: "/guide/formulas", name: "guide-formulas", component: FormulaGuideView },
    { path: "/admin", name: "admin", component: AdminView },
  ],
  // 설비 안내 페이지의 #ef7 같은 앵커로 이동(Stage 17). SSO 콜백 해시(#token=…)는 앵커가 아니므로 무시한다.
  // 앵커 대상이 아직 안 그려졌으면(첫 진입 때 데이터 받기 전) 화면 쪽(FacilityGuideView)이 나중에 스크롤한다.
  // 같은 화면 안의 쿼리 변경(대시보드 필터 → ?type=)은 스크롤을 건드리지 않는다.
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition;
    if (/^#[\w-]+$/.test(to.hash) && document.querySelector(to.hash)) {
      const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      return { el: to.hash, top: 16, behavior: reduceMotion ? "auto" : "smooth" };
    }
    if (to.path !== from.path) return { top: 0 };
    return false;
  },
});

export default router;
