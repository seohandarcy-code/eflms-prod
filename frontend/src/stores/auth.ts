import { defineStore } from "pinia";
import { adminLogin, adminLogout } from "../api/admin";

export type Role = "admin" | "user" | "general";

interface State {
  token: string | null;
  // admin: 관리자 / user: 등록 사용자(테이블 조회) / general: SSO 인증만 된 미등록 사용자(대시보드 조회만)
  role: Role | null;
  name: string | null;
  error: string | null;
  loading: boolean;
  // SSO 콜백이 #error=코드로 돌아왔을 때 — 대시보드 로그인 화면·관리자 화면이 같이 읽는다.
  ssoError: string | null;
  ssoErrorDetail: string | null;
  // 서버 인증 방식(/api/admin/auth-config의 auth_mode, App.vue가 앱 시작 때 채움) — 로컬 미리보기 판단용. 못 받았으면 null.
  authMode: string | null;
}

// 탭 단위 보관(sessionStorage) — 대시보드도 로그인해야 하는 SSO 모드에서 새로고침마다 다시 로그인하지
// 않게 한다(Stage 16-1). 탭을 닫으면 사라지고, 서버 재기동으로 세션이 없어지면 401을 받아 지운다.
const STORAGE_KEY = "eflms.session";

const SSO_ERROR_MESSAGES: Record<string, string> = {
  sso_not_configured: "SSO가 설정되지 않았습니다.",
  auth_failed: "SSO 인증에 실패했습니다.",
  broker_unreachable: "SSO 브로커 통신에 실패했습니다. 잠시 후 다시 시도해주세요.",
  missing_claim: "필요한 사용자 식별 정보를 받지 못했습니다.",
  not_registered: "등록되지 않은 계정입니다. 관리자에게 등록을 요청해주세요.",
};

function isRole(value: unknown): value is Role {
  return value === "admin" || value === "user" || value === "general";
}

function loadStored(): Pick<State, "token" | "role" | "name"> {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (typeof parsed?.token === "string" && isRole(parsed?.role)) {
        return { token: parsed.token, role: parsed.role, name: typeof parsed.name === "string" ? parsed.name : null };
      }
    }
  } catch {
    // 저장소를 못 쓰는 환경(사생활 보호 모드 등) — 메모리에만 둔다
  }
  return { token: null, role: null, name: null };
}

function saveStored(token: string | null, role: Role | null, name: string | null): void {
  try {
    if (token && role) sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ token, role, name }));
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // 무시 — 메모리 상태만으로도 동작한다
  }
}

export const useAuthStore = defineStore("auth", {
  state: (): State => ({
    ...loadStored(),
    error: null,
    loading: false,
    ssoError: null,
    ssoErrorDetail: null,
    authMode: null,
  }),
  getters: {
    isAuthenticated(state): boolean {
      return state.token !== null;
    },
    isAdmin(state): boolean {
      return state.role === "admin";
    },
    // 관리자 화면의 테이블 조회까지 쓸 수 있는 사람(allowed_users 등록자)
    isRegistered(state): boolean {
      return state.role === "admin" || state.role === "user";
    },
  },
  actions: {
    setSession(token: string, role: Role, name: string | null): void {
      this.token = token;
      this.role = role;
      this.name = name;
      this.error = null;
      saveStored(token, role, name);
    },
    clearSession(): void {
      this.token = null;
      this.role = null;
      this.name = null;
      saveStored(null, null, null);
    },
    async login(password: string): Promise<boolean> {
      this.loading = true;
      this.error = null;
      try {
        const { token } = await adminLogin(password);
        this.setSession(token, "admin", null);
        return true;
      } catch (err: any) {
        this.error = err?.response?.data?.detail ?? "로그인에 실패했습니다.";
        return false;
      } finally {
        this.loading = false;
      }
    },
    /**
     * SSO 콜백이 돌려보낸 URL 프래그먼트를 읽고 지운다 — 성공 `#token=..&role=..&name=..`,
     * 실패 `#error=코드&detail=..`. 앱 시작 때 한 번(main.ts) 부른다. 처리했으면 true.
     */
    consumeCallbackHash(hash: string): boolean {
      if (!hash.startsWith("#token=") && !hash.startsWith("#error=")) return false;
      const params = new URLSearchParams(hash.slice(1));
      const code = params.get("error");
      if (code !== null) {
        this.ssoError = SSO_ERROR_MESSAGES[code] ?? `SSO 로그인에 실패했습니다. (${code})`;
        this.ssoErrorDetail = params.get("detail");
        return true;
      }
      const token = params.get("token");
      const role = params.get("role");
      if (token && isRole(role)) {
        this.setSession(token, role, params.get("name"));
        this.ssoError = null;
        this.ssoErrorDetail = null;
      }
      return true;
    },
    async logout(): Promise<void> {
      if (this.token) {
        try {
          await adminLogout(this.token);
        } catch {
          // 로그아웃 실패는 무시 — 어차피 클라이언트 토큰은 지운다.
        }
      }
      this.clearSession();
    },
  },
});
