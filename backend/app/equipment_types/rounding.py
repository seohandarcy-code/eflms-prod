"""점수 지표의 소수 첫째 자리 반올림 (2026-11-06 사용자 결정 — (가) 방식).

- POF·COF·DOF 감점/점수와 종합점수는 소수 첫째 자리로 저장·표시한다(모든 설비유형 공통).
- 반올림은 엑셀 ROUND처럼 5에서 올린다(0에서 먼 쪽): -0.25 → -0.3, 0.25 → 0.3. 파이썬 round()는
  짝수 쪽(-0.25 → -0.2)이라 쓰지 않는다.
- 감점은 소수를 포함해 계산하고 결과만 소수 첫째 자리로 둔다(2026-11-19 사용자 결정). 원본 수식 안에서
  감점을 정수로 만들던 floor()/round()/int()(경과연수, 부품 고장확률 상태, 전기실 온도 등)는 모두 뺐다 —
  이 부분은 원본 엑셀과 소수만큼 다를 수 있다(의도적 차이, docs/DATA_DICTIONARY.md).
- 감점 항목(이름이 `_minus`로 끝나는 모든 계산 컬럼)은 float로 통일하고 항목마다 소수 첫째 자리로 반올림한
  뒤 합친다 — 화면의 항목 감점을 더하면 POF·COF·DOF 감점과 정확히 맞는다.
- 정수가 원래 뜻인 값(EF5·EF6 차단기 교체 횟수, EF7 열화계수 표의 연차 번호)과 원본의 중간값 소수 반올림
  (EF7 방전 인덱스·온도 열화계수)은 그대로다.

na.evaluate()가 감점 항목과 SCORE_FIELDS를 계산 직후 반올림하므로 각 유형 모듈은 따로 신경 쓰지 않는다.
운전년수(operation_year)는 각 모듈이 이 함수로 소수 첫째 자리를 구한다.
"""
from decimal import ROUND_HALF_UP, Decimal

SCORE_FIELDS = frozenset({"pof_minus", "pof", "cof_minus", "cof", "dof_minus", "dof", "total_score"})


def round1(value: float) -> float:
    # repr로 바꿔 이진 부동소수 오차(0.1+0.2=0.30000000000000004)를 걷어낸 뒤 반올림한다.
    return float(Decimal(repr(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def is_deduction(name: str) -> bool:
    """감점 항목 컬럼인지 — 이름이 `_minus`로 끝나는 계산 컬럼(축 감점 pof_minus 등 포함)."""
    return name.endswith("_minus")
