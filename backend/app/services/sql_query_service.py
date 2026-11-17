"""관리자 화면 SQL 조회 (Stage 16-5) — 조회(SELECT)만, 허용 목록 테이블만, 행·시간 제한.

글자 검사(SELECT/WITH로 시작하는 한 문장)는 친절한 오류 문구용이고, **실제 안전장치는 DB 쪽**이다:

- SQLite: 같은 DB 파일을 **읽기 전용 모드(`mode=ro`)로 새로 연 별도 연결**에서 실행하고, `set_authorizer`로
  SELECT·허용 목록 테이블 읽기·함수 호출 외의 모든 동작(쓰기·PRAGMA·ATTACH·허용 목록 밖 테이블 읽기 등)을
  거부한다. 컬럼을 안 읽는 조회(`SELECT 1 FROM t`, `count(*)`)는 authorizer에 안 잡혀서, 실행 전에 EXPLAIN으로
  실제로 여는 테이블이 허용 목록 것인지 한 번 더 본다. `set_progress_handler`로 시간 제한을 넘기면 중단한다. 앱의 세션·트랜잭션과 완전히 분리된다.
- PostgreSQL(운영): `SET TRANSACTION READ ONLY` + `statement_timeout`으로 실행 후 항상 rollback. 허용 목록
  테이블 제한은 DB 계정 권한으로 걸어야 한다 — 읽기 전용 계정 분리는 `docs/DEPLOY_PDEP.md` 참고.
"""
from __future__ import annotations

import asyncio
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin_service import ALLOWED_TABLES

MAX_ROWS = 1000
TIMEOUT_SECONDS = 5.0
MAX_SQL_LENGTH = 10_000

_ALLOWED_SET = frozenset(ALLOWED_TABLES)
_LEADING_COMMENTS = re.compile(r"^(\s+|--[^\n]*(\n|$)|/\*.*?\*/)*", re.S)


class SqlQueryError(ValueError):
    """사용자에게 그대로 보여줄 조회 오류(문법·권한·시간 초과 등)."""


@dataclass
class SqlQueryResult:
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    elapsed_ms: int = 0


def normalize_sql(sql: str) -> str:
    """앞뒤 공백·끝 세미콜론을 정리하고, 조회 한 문장인지 1차로 확인한다."""
    if not isinstance(sql, str) or not sql.strip():
        raise SqlQueryError("SQL을 입력하세요.")
    if len(sql) > MAX_SQL_LENGTH:
        raise SqlQueryError(f"SQL이 너무 깁니다(최대 {MAX_SQL_LENGTH:,}자).")
    body = sql.strip()
    while body.endswith(";"):
        body = body[:-1].rstrip()
    head = _LEADING_COMMENTS.sub("", body, count=1)
    keyword = head.split(None, 1)[0].lower() if head else ""
    if keyword not in ("select", "with"):
        raise SqlQueryError("조회(SELECT / WITH) 문장만 실행할 수 있습니다.")
    return body


def _cell(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<BLOB {len(bytes(value))} bytes>"
    if value is None or isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


# --- SQLite ---


def _authorizer(action: int, arg1: str | None, arg2: str | None, db: str | None, _trigger: str | None) -> int:
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        # 실제 테이블 읽기는 db="main" — 허용 목록만. db=None은 WITH(재귀 포함)로 만든 임시 결과라 통과.
        # 그 밖(temp 등)은 거부.
        if db == "main":
            return sqlite3.SQLITE_OK if arg1 in _ALLOWED_SET else sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK if db is None else sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION:
        return sqlite3.SQLITE_OK
    if action == getattr(sqlite3, "SQLITE_RECURSIVE", -1):  # WITH RECURSIVE
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


_DENIED_MESSAGE = "허용되지 않은 동작입니다 — 조회만 가능하고, 관리자 화면 테이블 목록에 있는 테이블만 읽을 수 있습니다."


def _check_opened_tables(conn: sqlite3.Connection, sql: str, allowed_roots: set[int]) -> None:
    """실행 계획(EXPLAIN)에서 실제로 여는 테이블·인덱스가 허용 목록 것인지 확인한다.

    authorizer는 컬럼을 읽을 때만 불려서 `SELECT 1 FROM allowed_users`·`count(*)`처럼 컬럼을 안 읽는 조회는
    못 막는다 — 테이블을 여는 명령(OpenRead 등)의 루트 페이지로 한 번 더 막는다. 가상 테이블(VOpen)도 거부.
    """
    for row in conn.execute("EXPLAIN " + sql):
        opcode, p2, p3 = row[1], row[3], row[4]
        if opcode in ("OpenRead", "OpenWrite", "ReopenIdx"):
            if p3 != 0 or p2 not in allowed_roots:
                raise SqlQueryError(_DENIED_MESSAGE)
        elif opcode == "VOpen":
            raise SqlQueryError(_DENIED_MESSAGE)


def _run_sqlite(db_path: str, sql: str, max_rows: int, timeout: float) -> SqlQueryResult:
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    started = time.monotonic()
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=timeout)
    except sqlite3.Error as exc:
        raise SqlQueryError(f"DB를 열 수 없습니다: {exc}") from exc
    try:
        # 허용 목록 테이블(과 그 인덱스)의 루트 페이지 — authorizer 설정 전에 읽는다.
        allowed_roots = {
            root
            for root, tbl in conn.execute("SELECT rootpage, tbl_name FROM sqlite_master WHERE rootpage > 0")
            if tbl in _ALLOWED_SET
        }
        conn.set_authorizer(_authorizer)
        deadline = started + timeout
        conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 1000)
        try:
            _check_opened_tables(conn, sql, allowed_roots)
            cursor = conn.execute(sql)
            columns = [d[0] for d in cursor.description or []]
            fetched = cursor.fetchmany(max_rows + 1)
        except sqlite3.DatabaseError as exc:
            message = str(exc)
            if "interrupted" in message:
                raise SqlQueryError(f"실행 시간이 {timeout:g}초를 넘어 중단했습니다.") from exc
            if "not authorized" in message or "prohibited" in message:
                raise SqlQueryError(_DENIED_MESSAGE) from exc
            if "one statement" in message:
                raise SqlQueryError("한 번에 한 문장만 실행할 수 있습니다.") from exc
            raise SqlQueryError(message) from exc
    finally:
        conn.close()
    truncated = len(fetched) > max_rows
    rows = [[_cell(v) for v in row] for row in fetched[:max_rows]]
    return SqlQueryResult(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        truncated=truncated,
        elapsed_ms=int((time.monotonic() - started) * 1000),
    )


# --- PostgreSQL ---


async def _run_postgres(session: AsyncSession, sql: str, max_rows: int, timeout: float) -> SqlQueryResult:
    started = time.monotonic()
    try:
        await session.rollback()  # 이 요청 세션에 열린 트랜잭션이 있으면 정리하고 새로 시작
        await session.execute(text("SET TRANSACTION READ ONLY"))
        await session.execute(text(f"SET LOCAL statement_timeout = {int(timeout * 1000)}"))
        result = await session.execute(text(sql))
        columns = list(result.keys())
        fetched = result.fetchmany(max_rows + 1)
    except Exception as exc:  # DB 오류 메시지를 그대로 보여준다
        message = str(getattr(exc, "orig", exc))
        if "statement timeout" in message or "canceling statement" in message:
            raise SqlQueryError(f"실행 시간이 {timeout:g}초를 넘어 중단했습니다.") from exc
        raise SqlQueryError(message) from exc
    finally:
        await session.rollback()
    truncated = len(fetched) > max_rows
    rows = [[_cell(v) for v in row] for row in fetched[:max_rows]]
    return SqlQueryResult(columns, rows, len(rows), truncated, int((time.monotonic() - started) * 1000))


async def run_select_sql(
    session: AsyncSession, sql: str, max_rows: int = MAX_ROWS, timeout: float = TIMEOUT_SECONDS
) -> SqlQueryResult:
    body = normalize_sql(sql)
    url = session.bind.url
    if url.get_backend_name() == "sqlite":
        if not url.database or url.database == ":memory:":
            raise SqlQueryError("이 DB에서는 SQL 조회를 쓸 수 없습니다(메모리 DB).")
        return await asyncio.to_thread(_run_sqlite, url.database, body, max_rows, timeout)
    if url.get_backend_name() == "postgresql":
        return await _run_postgres(session, body, max_rows, timeout)
    raise SqlQueryError(f"지원하지 않는 DB: {url.get_backend_name()}")
