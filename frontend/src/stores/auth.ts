import { defineStore } from "pinia";
import { adminLogin, adminLogout } from "../api/admin";

interface State {
  // 메모리에만 보관 — 새로고침하면 로그아웃된다(백엔드 세션도 재기동 시 초기화되는 것과
  // 같은 원칙: 토큰을 브라우저에 영속화하지 않는다).
  token: string | null;
  error: string | null;
  loading: boolean;
}

export const useAuthStore = defineStore("auth", {
  state: (): State => ({
    token: null,
    error: null,
    loading: false,
  }),
  getters: {
    isAuthenticated(state): boolean {
      return state.token !== null;
    },
  },
  actions: {
    async login(password: string): Promise<boolean> {
      this.loading = true;
      this.error = null;
      try {
        const { token } = await adminLogin(password);
        this.token = token;
        return true;
      } catch (err: any) {
        this.error = err?.response?.data?.detail ?? "로그인에 실패했습니다.";
        return false;
      } finally {
        this.loading = false;
      }
    },
    async logout(): Promise<void> {
      if (this.token) {
        try {
          await adminLogout(this.token);
        } catch {
          // 로그아웃 실패는 무시 — 어차피 클라이언트 토큰은 지운다.
        }
      }
      this.token = null;
    },
  },
});
