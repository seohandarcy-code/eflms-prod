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
