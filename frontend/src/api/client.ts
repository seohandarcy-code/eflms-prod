import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
});

interface SessionHolder {
  token: string | null;
  clearSession(): void;
}

/**
 * 로그인 세션을 모든 API 요청에 싣는다(Stage 16-1 — SSO 모드는 대시보드 API도 로그인 필요).
 * 토큰을 보냈는데 401이 오면(만료·서버 재기동) 세션을 지워 로그인 화면이 다시 뜨게 한다.
 */
export function installAuthInterceptors(session: SessionHolder): void {
  apiClient.interceptors.request.use((config) => {
    if (session.token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${session.token}`;
    }
    return config;
  });
  apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
      const sent = error?.config?.headers?.Authorization;
      if (error?.response?.status === 401 && sent && sent === `Bearer ${session.token}`) {
        session.clearSession();
      }
      return Promise.reject(error);
    }
  );
}
