// 붙여넣기 데이터 입력 도우미 (Stage 16-6) — 백엔드 임포트와 같은 규칙으로 탭 구분 텍스트를 나눈다.
// (빈 줄은 건너뛰되 줄 번호는 실제 줄 기준 — 서버 오류의 row_number와 미리보기 행이 맞아야 한다)

export interface PastedRow {
  rowNumber: number;
  cells: string[];
}

export interface PastedTable {
  header: string[];
  rows: PastedRow[];
}

function unquote(cell: string): string {
  const c = cell.trim();
  if (c.length >= 2 && c[0] === '"' && c[c.length - 1] === '"') return c.slice(1, -1).replace(/""/g, '"');
  return c;
}

export function parsePasted(text: string): PastedTable {
  const lines = text.replace(/^﻿/, "").split(/\r\n|\r|\n/);
  const numbered: [number, string][] = [];
  lines.forEach((line, i) => {
    if (line.trim() !== "") numbered.push([i + 1, line]);
  });
  if (!numbered.length) return { header: [], rows: [] };
  const header = numbered[0][1].split("\t").map(unquote);
  const rows = numbered.slice(1).map(([rowNumber, line]) => ({ rowNumber, cells: line.split("\t").map(unquote) }));
  return { header, rows };
}

/**
 * 파일을 붙여넣기 칸에 채울 텍스트로 읽는다 — UTF-8(BOM 포함)을 먼저 시도하고, 아니면 CP949(EUC-KR).
 * 사내 dat가 엑셀/메모장에서 CP949로 저장되는 경우가 있다(백엔드 임포트도 같은 순서).
 */
export function decodeFileBytes(bytes: ArrayBuffer): string {
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes).replace(/^﻿/, "");
  } catch {
    return new TextDecoder("euc-kr").decode(bytes);
  }
}

/** 오류 칸 찾기용 키: `${행}|${컬럼}` — 행 전체 오류는 컬럼 "(행 전체)". */
export function errorKey(rowNumber: number, column: string): string {
  return `${rowNumber}|${column}`;
}
