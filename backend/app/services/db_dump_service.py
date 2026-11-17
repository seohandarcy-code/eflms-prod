"""전체 DB를 psql로 복원할 수 있는 PostgreSQL용 .sql 파일로 만들기 (Stage 16-8).

다른 PostgreSQL에 DB를 통째로 옮기는 용도 — 원본이 SQLite(개발)든 PostgreSQL(운영)이든 같은 파일이 나온다.
pg_dump의 일반 텍스트 형식을 따른다:

    createdb eflms_new
    psql -v ON_ERROR_STOP=1 -d eflms_new -f eflms_full_YYYYMMDD_HHMM.sql

- 스키마: 앱 모델(`Base.metadata`)을 PostgreSQL 문법으로 컴파일 — `alembic check`가 모델 = 마이그레이션 결과임을
  보장한다. 의존 순서대로 CREATE TABLE → 인덱스.
- 데이터: 테이블마다 `COPY … FROM stdin` (psql 기본, null `\\N`, 탭·줄바꿈·역슬래시 이스케이프). SQLAlchemy 타입을
  거쳐 읽으므로 SQLite의 0/1 불리언·문자열 날짜도 PostgreSQL 값(t/f, ISO 날짜)으로 나간다.
- 자동 번호(SERIAL) 시퀀스를 최댓값으로 맞추고, `alembic_version`도 넣어 새 DB에서 `alembic upgrade head`를 이어 쓴다.
- 전체를 BEGIN … COMMIT으로 묶는다 — 중간에 실패하면 아무것도 남지 않는다. 빈 DB에 복원하는 것이 전제(DROP 없음).

모든 테이블(접근 권한 명단 `allowed_users` 포함)을 넣는다 — 관리자만 내려받을 수 있다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.schema import CreateIndex, CreateTable

from app.db import models  # noqa: F401  (Base.metadata에 전체 테이블 등록)
from app.db.base import Base

_PG = postgresql.dialect()
_quote = _PG.identifier_preparer.quote


@dataclass
class DumpResult:
    sql: str
    table_rows: dict[str, int] = field(default_factory=dict)
    alembic_version: str | None = None

    @property
    def total_rows(self) -> int:
        return sum(self.table_rows.values())


def copy_value(value: Any) -> str:
    """COPY 텍스트 형식의 한 칸."""
    if value is None:
        return r"\N"
    if isinstance(value, bool):
        return "t" if value else "f"
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return repr(value)
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "\\\\x" + bytes(value).hex()  # bytea hex — COPY 안에서 역슬래시를 한 번 더 이스케이프
    text_value = str(value)
    return (
        text_value.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _ddl(element) -> str:
    return str(element.compile(dialect=_PG)).strip() + ";"


async def _alembic_version(session: AsyncSession) -> str | None:
    try:
        return (await session.execute(text("SELECT version_num FROM alembic_version"))).scalar_one_or_none()
    except Exception:  # 테스트 DB처럼 마이그레이션 없이 만든 DB
        await session.rollback()
        return None


async def build_dump(session: AsyncSession, *, generated_at: datetime | None = None) -> DumpResult:
    generated_at = generated_at or datetime.now()
    backend = session.bind.url.get_backend_name()
    if backend == "postgresql":
        # 한 시점 기준으로 읽는다(읽는 도중 바뀐 데이터가 섞이지 않게)
        await session.rollback()
        await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))

    version = await _alembic_version(session)
    tables = Base.metadata.sorted_tables  # 외래키 의존 순서

    data_blocks: list[str] = []
    table_rows: dict[str, int] = {}
    for table in tables:
        cols = list(table.columns)
        rows = (await session.execute(select(*cols))).all()
        table_rows[table.name] = len(rows)
        col_list = ", ".join(_quote(c.name) for c in cols)
        lines = [f"COPY {_quote(table.name)} ({col_list}) FROM stdin;"]
        lines += ["\t".join(copy_value(v) for v in row) for row in rows]
        lines.append("\\.")
        data_blocks.append("\n".join(lines))
    if backend == "postgresql":
        await session.rollback()

    out: list[str] = []
    out.append("--")
    out.append("-- EFLMS 전체 DB 덤프 — PostgreSQL용 (psql로 복원)")
    out.append(f"-- 만든 시각: {generated_at:%Y-%m-%d %H:%M:%S}")
    out.append(f"-- 원본 DB: {backend}")
    out.append(f"-- 마이그레이션 버전(alembic): {version or '(없음)'}")
    out.append(f"-- 테이블 {len(tables)}개 · 전체 {sum(table_rows.values()):,}행")
    out.append("--")
    out.append("-- 복원(빈 DB에):")
    out.append("--   createdb eflms_new")
    out.append("--   psql -v ON_ERROR_STOP=1 -d eflms_new -f <이 파일>")
    out.append("-- 전체가 한 트랜잭션이라 실패하면 아무것도 남지 않는다. 기존 테이블을 지우는 문장은 없다.")
    out.append("--")
    out.append("-- 테이블별 행 수:")
    out += [f"--   {name}: {count}" for name, count in table_rows.items()]
    out.append("--")
    out.append("")
    out.append("\\set ON_ERROR_STOP on")
    out.append("SET client_encoding = 'UTF8';")
    out.append("SET standard_conforming_strings = on;")
    out.append("BEGIN;")
    out.append("")
    out.append("-- 스키마")
    for table in tables:
        out.append(_ddl(CreateTable(table)))
        out.append("")
        for index in sorted(table.indexes, key=lambda i: i.name or ""):
            out.append(_ddl(CreateIndex(index)))
        if table.indexes:
            out.append("")
    out.append(
        "CREATE TABLE alembic_version (\n\tversion_num VARCHAR(32) NOT NULL,\n"
        "\tCONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)\n);"
    )
    out.append("")
    out.append("-- 데이터")
    out += [block + "\n" for block in data_blocks]
    if version:
        out.append(f"INSERT INTO alembic_version (version_num) VALUES ('{version}');")
        out.append("")
    out.append("-- 자동 번호(SERIAL) 시퀀스를 지금 최댓값으로")
    for table in tables:
        col = table.autoincrement_column
        if col is None:
            continue
        t, c = _quote(table.name), _quote(col.name)
        out.append(
            f"SELECT pg_catalog.setval(pg_catalog.pg_get_serial_sequence('{t}', '{col.name}'), "
            f"COALESCE(MAX({c}), 1), MAX({c}) IS NOT NULL) FROM {t};"
        )
    out.append("")
    out.append("COMMIT;")
    out.append("")
    return DumpResult(sql="\n".join(out), table_rows=table_rows, alembic_version=version)
