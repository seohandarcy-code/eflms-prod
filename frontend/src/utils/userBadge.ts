import type { Role } from "../stores/auth";

// 화면 위 오른쪽 로그인 카드(components/UserBadge.vue, 2026-11-19 시안 D) — 역할 표시와 로컬 미리보기 규칙.

export const ROLE_LABEL: Record<Role, string> = {
  admin: "관리자",
  user: "등록 사용자",
  general: "일반 사용자",
};

export interface BadgeView {
  role: Role;
  /** 카드 첫 줄: "홍길동님", 이름이 없으면 역할 이름 */
  title: string;
  /** 카드 둘째 줄: 역할, 이름 없는 로컬 비밀번호 로그인이면 "비밀번호 로그인" */
  subtitle: string;
  /** 동그라미 안: 이름 첫 글자. 없으면 아이콘(key = 로컬 비밀번호 로그인, person = 그 외) */
  initial: string | null;
  icon: "key" | "person" | null;
  /** 로컬 미리보기면 true — 세션도 권한도 없는 그림일 뿐이라 로그아웃은 아무 일도 하지 않는다. */
  preview: boolean;
}

function view(role: Role, name: string | null, authMode: string | null, preview: boolean): BadgeView {
  const label = ROLE_LABEL[role];
  if (name) return { role, title: `${name}님`, subtitle: label, initial: Array.from(name)[0], icon: null, preview };
  const passwordLogin = role === "admin" && authMode !== "sso";
  return {
    role,
    title: label,
    subtitle: passwordLogin ? "비밀번호 로그인" : "",
    initial: null,
    icon: passwordLogin ? "key" : "person",
    preview,
  };
}

/**
 * 실제 로그인 정보가 있으면 그것을, 없으면 로컬 미리보기(SSO 로그인한 미등록 일반 사용자로 가정)를 보여 준다.
 * 미리보기는 VITE_PREVIEW_USER에 이름이 있고, 서버가 SSO 모드가 아니라고 확인됐을 때만 — 운영(SSO)에서는 절대 안 나온다.
 */
export function badgeView(
  session: { token: string | null; role: Role | null; name: string | null },
  authMode: string | null,
  previewName: string | null | undefined,
): BadgeView | null {
  if (session.token && session.role) return view(session.role, session.name?.trim() || null, authMode, false);
  const name = (previewName ?? "").trim();
  if (name && authMode !== null && authMode !== "sso") return view("general", name, authMode, true);
  return null;
}
