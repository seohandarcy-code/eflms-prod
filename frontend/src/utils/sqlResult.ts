// SQL 조회 화면 도우미 (Stage 16-5) — 화면 밖에서 테스트할 수 있게 분리한 순수 함수들.

/** 테이블을 눌렀을 때 입력창에 채울 기본 조회문. */
export function defaultTableQuery(table: string, limit = 100): string {
  return `SELECT *\nFROM ${table}\nLIMIT ${limit};`;
}

/**
 * 실행할 SQL — 입력창에서 일부를 선택했으면 그 부분만, 아니면 전체.
 * (DB 관리 프로그램처럼 여러 문장을 써 두고 하나만 골라 실행하는 용도)
 */
export function sqlToRun(text: string, selectionStart: number, selectionEnd: number): string {
  const selected = selectionEnd > selectionStart ? text.slice(selectionStart, selectionEnd) : "";
  return (selected.trim() ? selected : text).trim();
}

export function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "NULL";
  return String(value);
}

function csvEscape(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** 결과 그리드를 CSV로 — 엑셀에서 한글이 깨지지 않게 BOM을 붙인다. */
export function toCsv(columns: string[], rows: unknown[][]): string {
  const lines = [columns.map(csvEscape).join(","), ...rows.map((r) => r.map(csvEscape).join(","))];
  return "﻿" + lines.join("\r\n") + "\r\n";
}

/** 최근 실행 SQL 목록에 추가 — 맨 앞에, 중복 제거, 최대 n개. */
export function pushHistory(history: string[], sql: string, max = 10): string[] {
  const trimmed = sql.trim();
  if (!trimmed) return history;
  return [trimmed, ...history.filter((h) => h !== trimmed)].slice(0, max);
}
