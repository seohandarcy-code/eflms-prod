import { describe, expect, it } from "vitest";
import { badgeView } from "./userBadge";

const none = { token: null, role: null, name: null };

describe("badgeView", () => {
  it("이름이 있으면 '이름님 / 역할', 동그라미는 첫 글자", () => {
    expect(badgeView({ token: "t", role: "general", name: "홍길동" }, "sso", null)).toEqual({
      role: "general",
      title: "홍길동님",
      subtitle: "일반 사용자",
      initial: "홍",
      icon: null,
      preview: false,
    });
    expect(badgeView({ token: "t", role: "user", name: "김철수" }, "sso", null)?.subtitle).toBe("등록 사용자");
    expect(badgeView({ token: "t", role: "admin", name: "이영희" }, "sso", null)?.subtitle).toBe("관리자");
  });

  it("이름 없는 로컬 비밀번호 로그인은 '관리자 / 비밀번호 로그인'(열쇠), 미리보기 설정보다 우선", () => {
    expect(badgeView({ token: "t", role: "admin", name: null }, "local", "홍길동")).toEqual({
      role: "admin",
      title: "관리자",
      subtitle: "비밀번호 로그인",
      initial: null,
      icon: "key",
      preview: false,
    });
    // SSO인데 이름 클레임이 없으면 역할만(사람 아이콘)
    expect(badgeView({ token: "t", role: "user", name: "" }, "sso", null)).toMatchObject({ title: "등록 사용자", subtitle: "", icon: "person" });
  });

  it("로그인 전 로컬 모드면 미리보기(일반 사용자)", () => {
    expect(badgeView(none, "local", " 홍길동 ")).toMatchObject({ title: "홍길동님", subtitle: "일반 사용자", initial: "홍", preview: true });
    expect(badgeView(none, "none", "홍길동")?.preview).toBe(true);
  });

  it("SSO 모드·설정 없음·인증 설정을 못 받았으면 미리보기 없음", () => {
    expect(badgeView(none, "sso", "홍길동")).toBeNull();
    expect(badgeView(none, "local", "")).toBeNull();
    expect(badgeView(none, "local", undefined)).toBeNull();
    expect(badgeView(none, null, "홍길동")).toBeNull();
  });
});
