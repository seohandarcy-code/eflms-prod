"""값 없음(N/A → null) 입력을 계산에서 다루는 공통 규칙 (Stage 11, 2026-10-29 사용자 결정).

사내 입력파일의 `N/A`·`n/a`·`#N/A`는 임포트가 null(None)로 저장한다(app/services/import_service.py).
원본 계산식은 null을 모르므로(비교에서 TypeError, `== '양호'` 판정에선 엉뚱한 감점), 계산을 이렇게 감싼다:

- 공식이 null인 값을 **읽는 순간** 그 공식은 멈춘다.
  - 감점 컬럼(이름이 `_minus`로 끝남) → 0. "데이터가 없어 평가하지 않음"이며 화면엔 입력값이 N/A로 보인다.
  - 그 밖의 파생값(예: EF1 TCG 합계, EF3 부하율) → null. 이 값을 쓰는 감점도 같은 규칙으로 0이 된다.
- null을 읽지 않고 끝나는 공식은 원래대로 계산한다 — null이 없는 행의 결과는 원본과 완전히 같다
  (각 유형의 원본 대조 테스트가 그대로 통과).

각 설비유형 모듈의 calculate()가 evaluate()로 CALCULATED_COLUMNS를 돌린다.
"""
from datetime import date
from typing import Any

# 임포트가 null로 저장하는 표기(앞뒤 공백 제거·대소문자 무시 후 비교)
NA_TOKENS = frozenset({"N/A", "#N/A"})


def is_na_token(raw: str) -> bool:
    return raw.strip().upper() in NA_TOKENS


class _MissingValue(Exception):
    pass


class _NullAwareRow(dict):
    """null인 값을 꺼내면 _MissingValue를 던지는 dict — 공식 쪽은 평소처럼 row["컬럼"]으로 읽는다."""

    def __getitem__(self, key):
        value = super().__getitem__(key)
        if value is None:
            raise _MissingValue(key)
        return value


def evaluate(input_row: dict, columns: list[dict[str, Any]], as_of: date | None) -> dict:
    """CALCULATED_COLUMNS를 위에서부터 계산해 입력+계산 전체 dict를 돌려준다(입력 dict는 바꾸지 않음)."""
    row = _NullAwareRow(input_row)
    row["_as_of"] = as_of or date.today()
    for col in columns:
        try:
            row[col["name"]] = col["formula"](row)
        except _MissingValue:
            row[col["name"]] = 0 if col["name"].endswith("_minus") else None
    del row["_as_of"]
    return dict(row)
