// 공통 날짜 표시. 가동년월은 "YYYY-MM"으로 보여준다 — 설비목록·점검필요 순위·상세 패널 공통(Stage 10-0).
export function formatMonth(isoDate: string): string {
  return isoDate.slice(0, 7);
}
