import type { SimulatorColumn, SimulatorItem, SimulatorResult } from "../api/simulator";
import { formatScore } from "./formatValue";

// 점수 시뮬레이터(Stage 19) 화면용 순수 함수 — components/ScoreSimulatorDialog.vue.

export const NA = "N/A";

/** 칸 이름 목록에서 시작값과 다른 칸(앞뒤 공백 무시). */
export function changedFields(values: Record<string, string>, start: Record<string, string>): string[] {
  return Object.keys(values).filter((name) => (values[name] ?? "").trim() !== (start[name] ?? "").trim());
}

/** "모두 비우기" — 사업장·설비유형 코드는 남기고, N/A가 되는 칸은 N/A, 나머지는 빈칸. */
export function blankValues(columns: SimulatorColumn[], keep: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const col of columns) {
    if (col.name === "factory_code" || col.name === "EF_code") out[col.name] = keep[col.name] ?? "";
    else out[col.name] = col.na_allowed ? NA : "";
  }
  return out;
}

/** 데이터 양식 표의 "형식" 칸. */
export function dtypeLabel(dtype: string): string {
  return { int: "정수", float: "숫자", date: "날짜", str: "글자" }[dtype] ?? dtype;
}

/** 데이터 양식 표의 "허용값·범위" 칸. */
export function ruleLabel(col: SimulatorColumn): string {
  const parts: string[] = [];
  if (col.choices && col.choices.length > 0) parts.push(col.choices.join(" / "));
  if (col.min != null) parts.push(`${col.min} 이상`);
  if (col.max != null) parts.push(`${col.max} 이하`);
  if (col.gt != null) parts.push(`${col.gt} 초과`);
  if (col.dtype === "date") parts.push("YYYY-MM-DD");
  if (col.required) parts.push("필수");
  parts.push(col.na_allowed ? "N/A 가능" : "N/A 불가");
  return parts.join(" · ");
}

/** 바뀐 값 − 원래 값을 "+1.5" / "−3.0" / "변화 없음"으로. 둘 중 하나라도 없으면 빈 문자열. */
export function deltaLabel(next: number | null, base: number | null): string {
  if (next == null || base == null) return "";
  const diff = Math.round((next - base) * 10) / 10;
  if (diff === 0) return "변화 없음";
  return `${diff > 0 ? "+" : "−"}${formatScore(Math.abs(diff))}`;
}

export interface Deduction {
  axis: string;
  label: string;
  value: number;
}

/** 축 점수에 합산되는 감점 항목 중 큰 순서(음수가 큰 것)로 limit개. 0점(감점 없음)은 뺀다. */
export function topDeductions(result: SimulatorResult, limit = 8): Deduction[] {
  const items: Deduction[] = [];
  for (const [axis, list] of Object.entries(result.breakdown)) {
    for (const item of list as SimulatorItem[]) {
      if (!item.summed || item.value == null || item.value >= 0) continue;
      items.push({ axis: axis.toUpperCase(), label: item.label, value: item.value });
    }
  }
  return items.sort((a, b) => a.value - b.value).slice(0, limit);
}

/** 칸 이름 → 오류 사유(첫 번째). */
export function errorsByField(result: SimulatorResult | null): Record<string, string> {
  const out: Record<string, string> = {};
  for (const e of result?.errors ?? []) if (!(e.column in out)) out[e.column] = e.reason;
  return out;
}
