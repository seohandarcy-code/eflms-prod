import { describe, expect, it } from "vitest";
import type { AxiosAdapter } from "axios";
import { apiClient, installAuthInterceptors } from "./client";

describe("installAuthInterceptors (Stage 16-1)", () => {
  const session = {
    token: "tok-1" as string | null,
    cleared: 0,
    clearSession() {
      this.cleared += 1;
      this.token = null;
    },
  };
  installAuthInterceptors(session);

  function respondWith(status: number): AxiosAdapter {
    return async (config) => {
      const response = { data: { auth: config.headers.Authorization ?? null }, status, statusText: "", headers: {}, config };
      if (status >= 400) {
        throw Object.assign(new Error(`status ${status}`), { config, response, isAxiosError: true });
      }
      return response;
    };
  }

  it("세션 토큰을 모든 요청에 싣는다", async () => {
    session.token = "tok-1";
    const { data } = await apiClient.get("/api/summary", { adapter: respondWith(200) });
    expect(data.auth).toBe("Bearer tok-1");
  });

  it("이미 Authorization을 지정한 요청은 건드리지 않는다", async () => {
    session.token = "tok-1";
    const { data } = await apiClient.get("/x", { adapter: respondWith(200), headers: { Authorization: "Bearer other" } });
    expect(data.auth).toBe("Bearer other");
  });

  it("보낸 토큰이 401이면 세션을 지운다", async () => {
    session.token = "tok-2";
    session.cleared = 0;
    await expect(apiClient.get("/api/equipment", { adapter: respondWith(401) })).rejects.toThrow();
    expect(session.cleared).toBe(1);
    expect(session.token).toBeNull();
  });

  it("토큰 없이 받은 401(비밀번호 오류 등)이나 403은 세션을 지우지 않는다", async () => {
    session.token = null;
    session.cleared = 0;
    await expect(apiClient.post("/api/admin/login", {}, { adapter: respondWith(401) })).rejects.toThrow();
    session.token = "tok-3";
    await expect(apiClient.get("/api/admin/tables", { adapter: respondWith(403) })).rejects.toThrow();
    expect(session.cleared).toBe(0);
    expect(session.token).toBe("tok-3");
  });
});
