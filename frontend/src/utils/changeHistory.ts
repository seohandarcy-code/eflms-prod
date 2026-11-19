// 관리자 "변경 이력" 탭(Stage 21-4) — 행별 바뀌기 전후 값 비교와 표시 문구.
import type { DataChangeRowItem } from "../api/admin";

export const ACTION_LABEL: Record<string, string> = { insert: "추가", update: "갱신", delete: "삭제" };
export const ACTOR_LABEL: Record<string, string> = { admin: "관리자(웹)", cli: "명령" };

export interface FieldDiff {
  name: string;
  before: string;
  after: string;
}

function show(value: unknown): string {
  if (value === null || value === undefined) return "N/A";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/** 갱신 행에서 값이 바뀐 칸만(내부 칸 `_as_of`·`_extras`는 빼고). 추가·삭제는 모든 칸. */
export function fieldDiffs(row: DataChangeRowItem): FieldDiff[] {
  const before = row.before ?? {};
  const after = row.after ?? {};
  const names = [...new Set([...Object.keys(before), ...Object.keys(after)])].filter((n) => !n.startsWith("_"));
  return names
    .filter((n) => row.action !== "update" || show(before[n]) !== show(after[n]))
    .map((n) => ({ name: n, before: row.action === "insert" ? "" : show(before[n]), after: row.action === "delete" ? "" : show(after[n]) }));
}

/** "H1|eqp14" → "H1 · eqp14", 참고표 "discharge_history|H1|2026-11-01" → "discharge_history · H1 · 2026-11-01" */
export function rowKeyLabel(key: string): string {
  return key.split("|").join(" · ");
}
