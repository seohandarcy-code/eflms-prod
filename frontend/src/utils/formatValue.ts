// 상세 화면 값 표시. 사내 입력파일의 N/A는 null로 저장된다(Stage 11) — null이면 "N/A"를 보여주고,
// 숫자 서식(toFixed 등)은 값이 있을 때만 적용한다(null에 서식을 걸면 화면이 깨진다).
export interface NaOptions {
  digits?: number; // toFixed 자릿수
  locale?: boolean; // 천 단위 구분
  scale?: number; // 표시 전에 곱할 값(예: 비율 → % 는 100)
  unit?: string; // 값 뒤에 붙일 단위(N/A일 때는 붙이지 않음)
}

export const NA_TEXT = "N/A";

export function na(value: number | string | null | undefined, opts: NaOptions = {}): string {
  if (value === null || value === undefined) return NA_TEXT;
  if (typeof value === "number") {
    const v = opts.scale !== undefined ? value * opts.scale : value;
    const text = opts.digits !== undefined ? v.toFixed(opts.digits) : opts.locale ? v.toLocaleString() : String(v);
    return text + (opts.unit ?? "");
  }
  return value + (opts.unit ?? "");
}
