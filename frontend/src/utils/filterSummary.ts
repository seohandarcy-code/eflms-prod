// 메인 화면 위 오른쪽 "사업장 / 설비유형" 2단 요약(components/FilterSummaryBox.vue, 2026-11-19 시안 D).
// 행마다 한 줄로 고정하고, 넘치는 항목은 "외 N"으로 줄인다 — 전체 목록은 마우스를 올리면(title) 보인다.

export interface SummaryRow<T> {
  /** 비었으면 "전체"(필터 없음) */
  all: boolean;
  shown: T[];
  rest: number;
}

export function summarizeRow<T>(items: T[], max: number): SummaryRow<T> {
  if (items.length === 0) return { all: true, shown: [], rest: 0 };
  const limit = Math.max(1, max);
  return { all: false, shown: items.slice(0, limit), rest: Math.max(0, items.length - limit) };
}
