import type { FormulaItem, FormulaMapItem, FormulaStepsItem } from "../types/equipment";

// 지표설명 상세 페이지(/guide/formulas, Stage 22-11)의 표 문구. 계산식 데이터는 백엔드 FORMULA_DOCS.

export const KIND_LABELS: Record<FormulaItem["kind"], string> = {
  steps: "구간표",
  map: "등급표",
  worse: "1·2 중 나쁜 값",
  expr: "수식",
};

/** 감점 표기 — 음수는 유니코드 마이너스(−), 0은 0. */
export function formatMinus(value: number): string {
  if (value === 0) return "0";
  const text = Number.isInteger(value) ? String(Math.abs(value)) : Math.abs(value).toFixed(1);
  return value < 0 ? `−${text}` : `+${text}`;
}

function num(value: number, unit: string): string {
  return `${value.toLocaleString("ko-KR")}${unit}`;
}

/** 구간표 행 — 큰 기준부터 "100% 초과", "90% 초과 ~ 100% 이하", …, 마지막 "80% 이하". 기준이 '이상'이면 "이상 ~ 미만". */
export function stepRows(item: FormulaStepsItem): { cond: string; minus: number }[] {
  const lower = (b: FormulaStepsItem["bands"][number]) => `${num(b.value, item.unit)} ${b.op === "ge" ? "이상" : "초과"}`;
  const below = (b: FormulaStepsItem["bands"][number]) => `${num(b.value, item.unit)} ${b.op === "ge" ? "미만" : "이하"}`;
  const rows = item.bands.map((band, i) => ({
    cond: i === 0 ? lower(band) : `${lower(band)} ~ ${below(item.bands[i - 1])}`,
    minus: band.minus,
  }));
  const lowest = item.bands[item.bands.length - 1];
  if (lowest) rows.push({ cond: below(lowest), minus: item.otherwise });
  return rows;
}

/** 등급표 행 — 표의 값 + 표에 없는 값(default_label이 있으면 그 이름으로). */
export function mapRows(item: FormulaMapItem): { value: string; minus: number }[] {
  const rows = item.table.map((row) => ({ value: row.value === "" ? "(빈칸)" : row.value, minus: row.minus }));
  if (item.default_label) rows.push({ value: `그 밖(${item.default_label})`, minus: item.default });
  return rows;
}

/** 축 점수 식 — POF = 100 + Σ 감점. */
export function axisTex(axis: string): string {
  return `\\text{${axis.toUpperCase()}} = 100 + \\sum \\text{감점}`;
}
