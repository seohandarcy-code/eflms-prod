import type { ImportResultBody, TemplateColumn } from "../api/admin";

// 관리자 데이터 입력 화면(붙여넣기 · 행 편집)이 같이 쓰는 표시 도우미.

export const DTYPE_LABEL: Record<string, string> = { str: "문자", int: "정수", float: "숫자", date: "날짜" };

/** 컬럼의 허용값·범위 설명(예: "A / B", "0 ~ 100"). */
export function ruleText(col: TemplateColumn): string {
  const parts: string[] = [];
  if (col.choices) parts.push(col.choices.join(" / "));
  if (col.min !== undefined && col.max !== undefined) parts.push(`${col.min} ~ ${col.max}`);
  else if (col.min !== undefined) parts.push(`${col.min} 이상`);
  else if (col.max !== undefined) parts.push(`${col.max} 이하`);
  if (col.gt !== undefined) parts.push(`${col.gt} 초과`);
  return parts.join(", ");
}

/** 반영 완료 요약 줄. */
export function applyLines(result: ImportResultBody): string[] {
  if (result.kind === "equipment") {
    const lines = [`${result.imported_rows ?? 0}건 반영 완료`];
    if (result.replace) lines.push(`기존 설비 ${result.replaced_rows ?? 0}건을 지우고 교체했습니다.`);
    return lines;
  }
  return [
    `추가 ${result.inserted_rows ?? 0}행 · 갱신 ${result.updated_rows ?? 0}행` +
      (result.replace ? ` · 삭제 ${result.deleted_rows ?? 0}행` : "") +
      ` → 현재 ${result.table_rows_after ?? 0}행`,
    `설비 ${result.recalculated ?? 0}건의 점수를 다시 계산했습니다.`,
  ];
}

export function warningsOf(result: ImportResultBody): string[] {
  return [...(result.reference_warnings ?? []), ...(result.warnings ?? [])];
}

export function naSummary(result: ImportResultBody): string {
  return Object.entries(result.na_values ?? {})
    .map(([col, n]) => `${col} ${n}칸`)
    .join(", ");
}

/** 검증 결과의 행별 추가/갱신 개수. */
export function actionCountsOf(result: ImportResultBody | null): { add: number; update: number } {
  let add = 0;
  let update = 0;
  for (const a of result?.row_actions ?? []) {
    if (a.action === "갱신") update++;
    else add++;
  }
  return { add, update };
}
