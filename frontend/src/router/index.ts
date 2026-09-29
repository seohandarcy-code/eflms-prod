import { createRouter, createWebHistory } from "vue-router";
import AdminView from "../views/AdminView.vue";
import DashboardView from "../views/DashboardView.vue";
import GuideView from "../views/GuideView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "dashboard", component: DashboardView },
    { path: "/guide", name: "guide", component: GuideView },
    { path: "/admin", name: "admin", component: AdminView },
  ],
});

export default router;
