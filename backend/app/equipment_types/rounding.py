"""점수 지표의 소수 첫째 자리 반올림 (2026-11-06 사용자 결정 — (가) 방식).

- POF·COF·DOF 감점/점수와 종합점수는 소수 첫째 자리로 저장·표시한다(모든 설비유형 공통).
- 반올림은 엑셀 ROUND처럼 5에서 올린다(0에서 먼 쪽): -0.25 → -0.3, 0.25 → 0.3. 파이썬 round()는
  짝수 쪽(-0.25 → -0.2)이라 쓰지 않는다.
- 원본 수식 안의 정수 반올림(round()/int())은 그대로 둔다 — 원본 엑셀 결과와 계속 일치한다.
  원본이 소수를 내는 항목만 이 함수로 소수 첫째 자리가 된다(예: EF5 사고영향성·열화상·외함 감점).

na.evaluate()가 SCORE_FIELDS를 계산 직후 반올림하므로 각 유형 모듈은 따로 신경 쓰지 않는다.
"""
from decimal import ROUND_HALF_UP, Decimal

SCORE_FIELDS = frozenset({"pof_minus", "pof", "cof_minus", "cof", "dof_minus", "dof", "total_score"})


def round1(value: float) -> float:
    # repr로 바꿔 이진 부동소수 오차(0.1+0.2=0.30000000000000004)를 걷어낸 뒤 반올림한다.
    return float(Decimal(repr(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
