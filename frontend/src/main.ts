import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import "./style.css";
import App from "./App.vue";
import router from "./router";
import { installAuthInterceptors } from "./api/client";
import { useAuthStore } from "./stores/auth";

const app = createApp(App);
const pinia = createPinia();
app.use(pinia);

// SSO 로그인 결과(#token=… / #error=…)는 어느 화면으로 돌아오든 여기서 한 번 읽고 주소창에서 지운다.
const auth = useAuthStore(pinia);
const consumed = auth.consumeCallbackHash(window.location.hash);
installAuthInterceptors(auth);

app.use(router).use(ElementPlus).mount("#app");

// 프래그먼트(토큰 포함)를 주소창·방문 기록에서 지운다. vue-router는 만들어질 때 읽어 둔 주소(해시 포함)로
// 첫 이동을 다시 기록하므로, 그 첫 이동이 끝난 뒤에 router로 지워야 남지 않는다.
if (consumed) {
  router.isReady().then(() => router.replace({ ...router.currentRoute.value, hash: "" }));
}
