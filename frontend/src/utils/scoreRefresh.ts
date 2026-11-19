// 점수 갱신(Stage 21-1) 표시 규칙 — 관리자 "점수 갱신" 카드와 메인 화면 KPI 칸.

export const REFRESH_STATUS_LABEL: Record<string, string> = {
  running: "진행 중",
  success: "성공",
  partial: "일부 실패",
  failed: "실패",
};

export const REFRESH_TRIGGER_LABEL: Record<string, string> = {
  schedule: "정기",
  cli: "명령",
  admin: "관리자",
  startup: "서버 시작",
  daily: "자동",
};

/** "2026-11-19T01:30:12.123" → "2026-11-19 01:30" */
export function formatStamp(value: string | null | undefined): string {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 16);
}

/** 점수 기준일 — 설비마다 같으면 한 날짜, 다르면 "가장 이른 날 ~ 가장 늦은 날". */
export function scoreDateText(earliest: string | null | undefined, latest: string | null | undefined): string {
  if (!earliest && !latest) return "-";
  if (!earliest || !latest || earliest === latest) return (earliest || latest) as string;
  return `${earliest} ~ ${latest}`;
}

const AUTO_TRIGGERS = new Set(["startup", "daily", "schedule"]);

/** 메인 KPI 캡션 — "자동 갱신 11-19 00:05" / "수동 갱신 11-19 14:20" / 기록이 없으면 null(Stage 21-1c). */
export function refreshCaption(at: string | null | undefined, trigger: string | null | undefined): string | null {
  if (!at) return null;
  const kind = trigger && AUTO_TRIGGERS.has(trigger) ? "자동 갱신" : "수동 갱신";
  return `${kind} ${at.slice(5, 10)} ${at.slice(11, 16)}`;
}

/** KPI 칸에 마우스를 올리면 보이는 설명. */
export function refreshTooltip(autoEnabled: boolean): string {
  return autoEnabled
    ? "점수는 서버가 날짜가 바뀐 뒤(자정 이후 10분 안)와 서버가 시작될 때 저장된 진단 데이터로 오늘 기준으로 다시 계산합니다. 진단 데이터 최근 반영일은 데이터를 입력·수정할 때만 바뀝니다."
    : "서버 자동 갱신이 꺼져 있습니다 — 관리자 화면의 '지금 갱신' 또는 명령으로만 점수가 다시 계산됩니다.";
}
