"""Stage 15-0 — 참고표(설비 밖의 계산용 표) 넣기·교체·검증·리셋 + 재계산.

- 넣기: 같은 행(key)은 갱신, 새 행은 추가 / --replace: 표를 비우고 교체 / --check: DB 미반영
- 형식 오류가 한 행이라도 있으면 파일 전체 미반영(N/A·빈 칸·날짜·범위·파일 안 중복·컬럼 누락)
- 참고표가 바뀌면 그 유형 설비 점수를 같은 트랜잭션에서 다시 계산(계산 기준일은 그대로)
- 리셋: 표를 비우고 재계산(빈 표 = 0, 경고), 다른 유형은 그대로
- 시드는 비어 있는 참고표에만 목업을 넣는다
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.db.models import BatteryDischargeHistory, BatteryScoreDetail, BatteryTempDecayCoef, Equipment, ScoreSnapshot
from app.db.seed import seed_type
from app.equipment_types import ef7_battery
from app.services.ingest import ingest_row
from app.services.reference_data import calc_options, ensure_mock_reference, load_reference
from app.services.reference_service import import_reference_file, reset_reference

DISCH_HEADER = ["disch_date", "factory_code", "volt_change", "disch_index"]


def _write(tmp_path, header, rows, name="ref.dat"):
    path = tmp_path / name
    path.write_text("\n".join(["\t".join(header)] + ["\t".join(str(c) for c in r) for r in rows]) + "\n", encoding="utf-8")
    return str(path)


def _row(eqp_id, factory="H1", start=date(2016, 1, 1), **kw):
    row = ef7_battery.generate_input_row()
    row.update(eqp_id=eqp_id, factory_code=factory, operation_start_time=start, bat_room_temp=25.0, **kw)
    return row


async def _seed_battery(session, rows):
    await ensure_mock_reference(session, ef7_battery)
    options = await calc_options(session, ef7_battery)
    ids = [await ingest_row(ef7_battery.calculate(r, **options), session) for r in rows]
    await session.commit()
    return ids


async def _count(session, model):
    return await session.scalar(select(func.count()).select_from(model))


async def _detail(session, eq_id):
    await session.commit()  # 다른 세션 상태를 읽지 않도록 새 트랜잭션에서 다시 읽는다
    session.expire_all()
    return await session.get(BatteryScoreDetail, eq_id), await session.get(ScoreSnapshot, eq_id)


async def test_import_upserts_by_key_and_recalculates(session_factory, tmp_path):
    async with session_factory() as session:
        h1, p1 = await _seed_battery(session, [_row("bat1"), _row("bat2", factory="P1")])
        before_h1, _ = await _detail(session, h1)
        old_today, old_h1_index = before_h1.today, before_h1.disch_index
        before_p1, p1_score = await _detail(session, p1)
        old_p1_index, old_p1_total = before_p1.disch_index, p1_score.total_score

        path = _write(tmp_path, DISCH_HEADER, [
            ["2016-01-10", "H1", 20.0, 9.179],   # 기존 행(H1+2016-01-10) 갱신: 5.324 → 9.179
            ["2026.10.01", "H1", 10.0, 4.59],    # 새 행 — 날짜 표기 YYYY.MM.DD도 받는다
        ])
        result = await import_reference_file(path, "EF7", "discharge_history", session)
        assert result.ok, (result.file_errors, result.row_errors)
        assert (result.inserted_rows, result.updated_rows, result.table_rows_after) == (1, 1, 41)
        assert result.recalculated == 2 and result.warnings == []

        after_h1, h1_score = await _detail(session, h1)
        assert after_h1.disch_index == pytest.approx(old_h1_index - 5.324 + 9.179 + 4.59)
        assert after_h1.today == old_today  # 계산 기준일은 그대로, 참고표 변화만 반영
        h1_total = h1_score.total_score
        after_p1, p1_after = await _detail(session, p1)
        assert after_p1.disch_index == old_p1_index and p1_after.total_score == old_p1_total
        # 저장된 점수 = 지금 DB 참고표로 다시 계산한 값
        input_row, as_of = await ef7_battery.load_inputs(session, h1)
        expected = ef7_battery.calculate(input_row, as_of=as_of, **(await calc_options(session, ef7_battery)))
        assert h1_total == expected["total_score"]


async def test_replace_swaps_the_whole_table(session_factory, tmp_path):
    async with session_factory() as session:
        (h1,) = await _seed_battery(session, [_row("bat1")])
        path = _write(tmp_path, ["year", "gamma_y"], [[y, 1.0] for y in range(1, 31)])
        result = await import_reference_file(path, "EF7", "temp_decay_coef", session, replace=True)
        assert result.ok
        assert (result.deleted_rows, result.inserted_rows, result.table_rows_after) == (20, 30, 30)
        detail, _ = await _detail(session, h1)
        input_row, _ = await ef7_battery.load_inputs(session, h1)
        years = detail.operation_year
        assert detail.temp_dec_coef == round(int(years) * 1.0 + (years % 1) * 1.0, 1)  # 25℃라 배율 1


async def test_check_validates_without_writing(session_factory, tmp_path):
    async with session_factory() as session:
        (h1,) = await _seed_battery(session, [_row("bat1")])
        before, _ = await _detail(session, h1)
        path = _write(tmp_path, DISCH_HEADER, [["2026-10-01", "H1", 10.0, 4.59]])
        result = await import_reference_file(path, "EF7", "discharge_history", session, replace=True, dry_run=True)
        assert result.ok and result.dry_run and result.table_rows_before == 40
        assert await _count(session, BatteryDischargeHistory) == 40
        after, _ = await _detail(session, h1)
        assert after.disch_index == before.disch_index


@pytest.mark.parametrize(
    ("row", "column", "reason_part"),
    [
        (["N/A", "H1", 10.0, 4.5], "disch_date", "N/A 불가"),
        (["2026-13-01", "H1", 10.0, 4.5], "disch_date", "date 형식이 아님"),
        (["2026-10-01", "", 10.0, 4.5], "factory_code", "빈 값"),
        (["2026-10-01", "H1", 100.5, 4.5], "volt_change", "초과"),
        (["2026-10-01", "H1", "11.6%", 4.5], "volt_change", "float 형식이 아님"),
        (["2026-10-01", "H1", 10.0, -1], "disch_index", "미만"),
        (["2026-10-01", "H1", 10.0, ""], "disch_index", "빈 값"),
    ],
)
async def test_discharge_row_errors_reject_whole_file(session_factory, tmp_path, row, column, reason_part):
    async with session_factory() as session:
        await _seed_battery(session, [])
        path = _write(tmp_path, DISCH_HEADER, [["2026-09-30", "K1", 5.0, 2.295], row])
        result = await import_reference_file(path, "EF7", "discharge_history", session)
        assert not result.ok
        assert [(e.row_number, e.column) for e in result.row_errors] == [(3, column)]
        assert reason_part in result.row_errors[0].reason
        assert await _count(session, BatteryDischargeHistory) == 40  # 앞 행도 반영 안 됨


async def test_duplicate_key_in_file_and_temp_coef_rules(session_factory, tmp_path):
    async with session_factory() as session:
        await _seed_battery(session, [])
        dup = _write(tmp_path, DISCH_HEADER, [["2026-10-01", "H1", 10.0, 4.5], ["2026/10/01", "H1", 12.0, 5.5]], "dup.dat")
        result = await import_reference_file(dup, "EF7", "discharge_history", session)
        assert [(e.row_number, e.reason) for e in result.row_errors] == [(3, "2행과 같은 행 중복")]

        coef = _write(tmp_path, ["year", "gamma_y"], [[0, 1.0], [2, 0], [3, 1.5], [3, 1.6], [4.5, 1.0]], "coef.dat")
        result = await import_reference_file(coef, "EF7", "temp_decay_coef", session)
        reasons = {(e.row_number, e.column): e.reason for e in result.row_errors}
        assert reasons[(2, "year")] == "1 미만"
        assert reasons[(3, "gamma_y")] == "0 이하"
        assert reasons[(5, "year")] == "4행과 같은 행 중복"
        assert reasons[(6, "year")] == "int 형식이 아님"
        assert await _count(session, BatteryTempDecayCoef) == 20


async def test_file_level_errors(session_factory, tmp_path):
    async with session_factory() as session:
        missing = _write(tmp_path, ["disch_date", "factory_code", "disch_index"], [["2026-10-01", "H1", 4.5]], "m.dat")
        result = await import_reference_file(missing, "EF7", "discharge_history", session)
        assert result.file_errors == ["필수 컬럼 없음: volt_change"]

        ok = _write(tmp_path, DISCH_HEADER, [["2026-10-01", "H1", 10.0, 4.5]], "ok.dat")
        assert "없는 참고표" in (await import_reference_file(ok, "EF7", "discharge", session)).file_errors[0]
        assert (await import_reference_file(ok, "EF1", "discharge_history", session)).file_errors == ["EF1에는 참고표가 없음"]
        assert "등록되지 않은 설비유형" in (await import_reference_file(ok, "EF99", "x", session)).file_errors[0]


async def test_unknown_columns_are_reported_but_not_stored(session_factory, tmp_path):
    async with session_factory() as session:
        path = _write(tmp_path, [*DISCH_HEADER, "비고"], [["2026-10-01", "H1", 10.0, 4.5, "정전"]])
        result = await import_reference_file(path, "EF7", "discharge_history", session)
        assert result.ok and result.unknown_columns == ["비고"]
        assert result.recalculated == 0  # 배터리 설비가 없으면 재계산할 것도 없다
        assert len(result.warnings) == 1  # 온도감소계수는 아직 비어 있음


async def test_header_only_replace_empties_table_with_warning(session_factory, tmp_path):
    async with session_factory() as session:
        (h1,) = await _seed_battery(session, [_row("bat1")])
        path = _write(tmp_path, DISCH_HEADER, [])
        check = await import_reference_file(path, "EF7", "discharge_history", session, replace=True, dry_run=True)
        assert check.ok and check.warnings
        result = await import_reference_file(path, "EF7", "discharge_history", session, replace=True)
        assert result.ok and result.table_rows_after == 0
        assert any("방전이력" in w for w in result.warnings)
        detail, _ = await _detail(session, h1)
        assert detail.disch_index == 0


async def test_reset_reference_recalculates_and_keeps_other_types(client, session_factory):
    async with session_factory() as session:
        (h1,) = await _seed_battery(session, [_row("bat1")])
        ef1_before = (await session.execute(
            select(ScoreSnapshot.equipment_id, ScoreSnapshot.total_score).join(Equipment).where(Equipment.ef_code == "EF1")
        )).all()
        result = await reset_reference(session, "EF7", "discharge_history")
        assert result.ok and result.deleted == {"discharge_history": 40} and result.recalculated == 1
        assert len(result.warnings) == 1
        detail, _ = await _detail(session, h1)
        assert detail.disch_index == 0 and detail.temp_dec_coef > 0

        result = await reset_reference(session, "EF7", "all")
        assert result.deleted == {"discharge_history": 0, "temp_decay_coef": 20} and len(result.warnings) == 2
        detail, _ = await _detail(session, h1)
        assert (detail.temp_dec_coef, detail.soh_minus) == (0, 0)
        assert (await session.execute(
            select(ScoreSnapshot.equipment_id, ScoreSnapshot.total_score).join(Equipment).where(Equipment.ef_code == "EF1")
        )).all() == ef1_before

        assert (await reset_reference(session, "EF7", "nothing")).errors
        assert (await reset_reference(session, "EF2", "all")).errors == ["EF2에는 참고표가 없음"]


async def test_seed_fills_only_empty_reference_tables(session_factory, tmp_path):
    async with session_factory() as session:
        path = _write(tmp_path, ["year", "gamma_y"], [[1, 9.9]])
        assert (await import_reference_file(path, "EF7", "temp_decay_coef", session)).ok
        await seed_type(session, "EF7", rows=2, reset=False)
        await session.commit()
        reference = await load_reference(session, ef7_battery)
        assert len(reference["discharge_history"]) == 40  # 비어 있던 표만 목업
        assert reference["temp_decay_coef"] == [{"year": 1, "gamma_y": 9.9}]  # 이미 있던 표는 그대로
        assert await _count(session, BatteryScoreDetail) == 2


async def test_projection_uses_current_reference(client, session_factory, tmp_path):
    async with session_factory() as session:
        (h1,) = await _seed_battery(session, [_row("bat1", start=date.today() - timedelta(days=365 * 3))])
    before = (await client.get(f"/api/equipment/{h1}")).json()["projection"]
    async with session_factory() as session:
        path = _write(tmp_path, ["year", "gamma_y"], [[y, 5.0] for y in range(1, 21)])
        assert (await import_reference_file(path, "EF7", "temp_decay_coef", session, replace=True)).ok
    after = (await client.get(f"/api/equipment/{h1}")).json()
    assert after["projection"][0]["total_score"] == after["score"]["total_score"]
    assert after["projection"][-1]["pof"] < before[-1]["pof"]
