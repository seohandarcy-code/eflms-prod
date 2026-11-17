import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useAuthStore } from "./auth";

describe("auth store (Stage 16-1)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    setActivePinia(createPinia());
  });

  it("SSO 성공 프래그먼트를 읽어 역할·이름을 채우고 탭 저장소에 보관한다", () => {
    const auth = useAuthStore();
    const handled = auth.consumeCallbackHash("#token=abc&role=general&name=%ED%99%8D%20%EA%B8%B8%EB%8F%99%20%26%20%ED%8C%80");
    expect(handled).toBe(true);
    expect(auth.token).toBe("abc");
    expect(auth.role).toBe("general");
    expect(auth.name).toBe("홍 길동 & 팀");
    expect(auth.isAuthenticated).toBe(true);
    expect(auth.isAdmin).toBe(false);
    expect(auth.isRegistered).toBe(false);

    // 새로고침(새 스토어)해도 같은 탭에서는 유지
    setActivePinia(createPinia());
    const reloaded = useAuthStore();
    expect(reloaded.token).toBe("abc");
    expect(reloaded.role).toBe("general");
  });

  it("오류 프래그먼트는 문구로 바꾸고 세션은 만들지 않는다", () => {
    const auth = useAuthStore();
    expect(auth.consumeCallbackHash("#error=broker_unreachable&detail=RuntimeError%3A+timeout")).toBe(true);
    expect(auth.ssoError).toContain("브로커 통신");
    expect(auth.ssoErrorDetail).toBe("RuntimeError: timeout");
    expect(auth.isAuthenticated).toBe(false);

    expect(auth.consumeCallbackHash("#error=weird")).toBe(true);
    expect(auth.ssoError).toContain("(weird)");
  });

  it("관계없는 해시와 알 수 없는 역할은 무시한다", () => {
    const auth = useAuthStore();
    expect(auth.consumeCallbackHash("")).toBe(false);
    expect(auth.consumeCallbackHash("#section-2")).toBe(false);
    auth.consumeCallbackHash("#token=abc&role=root");
    expect(auth.isAuthenticated).toBe(false);
  });

  it("역할별 권한 getter", () => {
    const auth = useAuthStore();
    auth.setSession("t1", "admin", null);
    expect([auth.isAdmin, auth.isRegistered]).toEqual([true, true]);
    auth.setSession("t2", "user", "김");
    expect([auth.isAdmin, auth.isRegistered]).toEqual([false, true]);
    auth.clearSession();
    expect(auth.isAuthenticated).toBe(false);
    expect(sessionStorage.getItem("eflms.session")).toBeNull();
  });

  it("깨진 저장값은 버린다", () => {
    sessionStorage.setItem("eflms.session", "{not json");
    expect(useAuthStore().isAuthenticated).toBe(false);
    setActivePinia(createPinia());
    sessionStorage.setItem("eflms.session", JSON.stringify({ token: "x", role: "superuser" }));
    expect(useAuthStore().isAuthenticated).toBe(false);
  });
});
