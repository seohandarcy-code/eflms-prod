"""5개년 POF 예측 (Stage 21-2, 2026-11-19).

저장된 입력으로 기준일만 1~5년 늦춰 다시 계산한 값 — 해마다 판정과 직전 해 대비 바뀐 POF 감점 항목을 준다.
진단값은 그대로라는 가정이라 EF1 Furan(총량 ÷ 사용년수)처럼 감점이 사라져 POF가 오르는 해도 그대로 보여 준다.
"""
from datetime import date, timedelta

from app.equipment_types import ef1_transformer, ef4_switchgear
from app.equipment_types.rounding import round1
from app.services.equipment_service import _projection, classify_status
from app.services.ingest import ingest_row

BASE = date(2026, 11, 19)


async def test_projection_reports_status_and_changed_pof_items(session_factory):
    row = ef4_switchgear.generate_input_row()
    row["operation_start_time"] = BASE - timedelta(days=int(10.0 * 365))
    async with session_factory() as session:
        eq_id = await ingest_row(ef4_switchgear.calculate(row, as_of=BASE), session)
        await session.commit()
        points = await _projection(session, ef4_switchgear, eq_id)

    assert [p.years_ahead for p in points] == [0, 1, 2, 3, 4, 5]
    assert points[0].pof_changes == []
    for prev, p in zip(points, points[1:]):
        assert p.status == classify_status(p.pof, p.cof, p.dof)
        age = next(c for c in p.pof_changes if c.field == "age_minus")
        assert age.delta == -1.0 and age.label
        assert round1(prev.pof + sum(c.delta for c in p.pof_changes)) == p.pof  # 바뀐 항목만으로 POF 변화가 설명된다
        assert p.cof == points[0].cof and p.dof == points[0].dof  # 날짜는 POF에만 영향


async def test_projection_keeps_furan_deduction_constant(session_factory):
    """Furan 연평균은 진단 시점 사용년수로 나눠(2026-11-19) 예측해도 바뀌지 않는다 — 예전엔 1년 뒤 -24가 풀려 POF가 올랐다."""
    row = ef1_transformer.generate_input_row()
    row["operation_start_time"] = BASE - timedelta(days=int(3.5 * 365))
    row["furan_diag_time"] = BASE - timedelta(days=int(0.5 * 365))  # 진단 시점 사용 3.0년
    for name in ("furan_5H2F", "furan_2FOL", "furan_2ACF", "furan_5M2F"):
        row[name] = 0
    row["furan_2FAL"] = 20  # 20 ÷ 3.0 = 6.7 → 이상(-24), 기준일이 늦어져도 그대로
    async with session_factory() as session:
        eq_id = await ingest_row(ef1_transformer.calculate(row, as_of=BASE), session)
        await session.commit()
        points = await _projection(session, ef1_transformer, eq_id)

    assert not any(c.field == "furan_minus" for p in points for c in p.pof_changes)
    assert all(b.pof <= a.pof for a, b in zip(points, points[1:]))  # 이 설비는 해마다 내려가기만 한다
