// 관리자 "행 편집"(Stage 18)의 순수 함수 — 지금 데이터를 표로 고치고, 고친·추가한 행만 탭 구분 텍스트로 만들어
// 붙여넣기와 같은 검증·반영 API(추가·갱신)로 보낸다. 서버 오류의 줄 번호를 다시 표의 행에 연결한다.

export interface EditorRow {
  /** 화면 안에서만 쓰는 고유 번호 */
  id: number;
  /** 기존 행의 순번(1부터), 새 행은 null */
  no: number | null;
  cells: string[];
  /** 불러온 원래 값 — 새 행은 null */
  original: string[] | null;
}

export function rowsFromServer(rows: string[][]): EditorRow[] {
  return rows.map((cells, i) => ({ id: i + 1, no: i + 1, cells: [...cells], original: [...cells] }));
}

/** 새 행 — source가 있으면 그 값을 복사(복제). */
export function makeNewRow(id: number, width: number, source?: string[]): EditorRow {
  const cells = source ? [...source] : Array.from({ length: width }, () => "");
  return { id, no: null, cells, original: null };
}

export function isNewRow(row: EditorRow): boolean {
  return row.original === null;
}

export function isCellChanged(row: EditorRow, index: number): boolean {
  return row.original !== null && row.cells[index] !== row.original[index];
}

export function isRowChanged(row: EditorRow): boolean {
  return row.original === null || row.cells.some((cell, i) => cell !== row.original![i]);
}

export function isBlankRow(row: EditorRow): boolean {
  return row.cells.every((cell) => cell.trim() === "");
}

/** 보낼 행 — 고친 기존 행 + 비어 있지 않은 새 행(완전히 빈 새 행은 무시). */
export function pendingRows(rows: EditorRow[]): EditorRow[] {
  return rows.filter((row) => (isNewRow(row) ? !isBlankRow(row) : isRowChanged(row)));
}

/** 칸 값 안의 탭·줄바꿈은 칸을 깨뜨리므로 공백으로(내려받기 규칙과 같다). */
export function cleanCell(value: string): string {
  return value.replace(/[\t\r\n]/g, " ");
}

/** 헤더 + 보낼 행 → 탭 구분 텍스트. lineToId: 서버가 알려주는 줄 번호(1행은 헤더) → 표의 행 id. */
export function buildEditText(header: string[], rows: EditorRow[]): { text: string; lineToId: Map<number, number> } {
  const lineToId = new Map<number, number>();
  const lines = [header.join("\t")];
  rows.forEach((row, i) => {
    lineToId.set(i + 2, row.id);
    lines.push(row.cells.map(cleanCell).join("\t"));
  });
  return { text: lines.join("\n") + "\n", lineToId };
}

/** 키 칸을 앞으로 — 표에서 왼쪽에 고정해 가로로 스크롤해도 어느 행인지 보이게. */
export function displayOrder(header: string[], key: string[]): number[] {
  const keyIdx = key.map((k) => header.indexOf(k)).filter((i) => i >= 0);
  return [...keyIdx, ...header.map((_, i) => i).filter((i) => !keyIdx.includes(i))];
}
