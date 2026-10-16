"""Stage 8-2 — 설비유형 단위 운영(리셋·교체 임포트·트랜잭션)이 다른 유형을 건드리지 않는지 확인.

EF2는 아직 없으므로 테스트 전용 가짜 유형(EF99)을 레지스트리에 끼워 넣는다. 전용 테이블 없이
공통 테이블(equipment/score_snapshot/extra)만 쓰는 최소 모듈이다.
"""
import types
from datetime import date

import pytest
from sqlalchemy import func, select

from app.db.models import Equipment, EquipmentExtraAttribute, ScoreSnapshot, TransformerSpec
from app.equipment_types import registry
from app.services.dataset_service import count_type, reset_type
from app.services.import_service import import_file
from app.services.ingest import ingest_row


def _fake_calculate(row: dict) -> dict:
    if row.get("fake_name") == "BOOM":  # 반영 도중 실패 시나리오용
        raise RuntimeError("계산 실패 시뮬레이션")
    return {**row, "pof_minus": -10, "pof": 90, "cof_minus": -20, "cof": 80, "dof_minus": -30, "dof": 70, "total_score": 83.0}


async def _noop_ingest_domain(row, equipment_id, session):
    return None


_counter = iter(range(1, 10_000))
FAKE = types.SimpleNamespace(
    EF_CODE="EF99",
    EF_NAME="테스트설비",
    NAME_FIELD="fake_name",
    INPUT_COLUMNS=[
        {"name": "factory_code", "dtype": "str"},
        {"name": "EF_code", "dtype": "str"},
        {"name": "fake_name", "dtype": "str"},
        {"name": "voltage", "dtype": "int"},
        {"name": "operation_start_time", "dtype": "date"},
    ],
    DOMAIN_TABLES=[],
    generate_input_row=lambda: {
        "factory_code": "H1",
        "EF_code": "EF99",
        "fake_name": f"FK{next(_counter)}",
        "voltage": 154000,
        "operation_start_time": date(2010, 1, 1),
    },
    calculate=_fake_calculate,
    ingest_domain=_noop_ingest_domain,
)


@pytest.fixture(autouse=True)
def register_fake(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, "EF99", FAKE)


async def _seed_fake(session, n=3):
    for _ in range(n):
        await ingest_row(FAKE.calculate(FAKE.generate_input_row()), session)
    await session.commit()


def _write_dat(tmp_path, names, ef_code="EF99", extra_col=False):
    header = ["factory_code", "EF_code", "fake_name", "voltage", "operation_start_time"] + (["비고"] if extra_col else [])
    lines = ["\t".join(header)]
    for n in names:
        cells = ["H1", ef_code, n, "154000", "2012-03-01"] + (["메모"] if extra_col else [])
        lines.append("\t".join(cells))
    path = tmp_path / "fake.dat"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


async def _ef1_fingerprint(session):
    """EF1 데이터가 그대로인지 판단할 지문 — 설비 수, 이름, 점수, 전용 테이블 행 수."""
    rows = (
        await session.execute(
            select(Equipment.equipment_id, Equipment.equipment_name, ScoreSnapshot.total_score)
            .join(ScoreSnapshot, ScoreSnapshot.equipment_id == Equipment.equipment_id)
            .where(Equipment.ef_code == "EF1")
            .order_by(Equipment.equipment_id)
        )
    ).all()
    spec_count = await session.scalar(select(func.count()).select_from(TransformerSpec))
    return rows, spec_count


async def test_reset_other_type_keeps_ef1(client, session_factory):
    async with session_factory() as session:
        await _seed_fake(session)
        before = await _ef1_fingerprint(session)
        assert await count_type(session, "EF99") == 3

        removed = await reset_type(session, "EF99")
        await session.commit()

        assert removed == 3
        assert await count_type(session, "EF99") == 0
        assert await _ef1_fingerprint(session) == before
        assert len(before[0]) == 3  # conftest가 넣은 EF1 3건


async def test_reset_ef1_keeps_other_type_and_clears_ef1_domain_tables(client, session_factory):
    async with session_factory() as session:
        await _seed_fake(session, n=2)
        await reset_type(session, "EF1")
        await session.commit()

        assert await count_type(session, "EF1") == 0
        assert await session.scalar(select(func.count()).select_from(TransformerSpec)) == 0
        assert await count_type(session, "EF99") == 2


async def test_import_replace_swaps_only_that_type(client, session_factory, tmp_path):
    async with session_factory() as session:
        await _seed_fake(session, n=4)
        before = await _ef1_fingerprint(session)

        result = await import_file(_write_dat(tmp_path, ["REAL1", "REAL2"], extra_col=True), "EF99", session, replace=True)

        assert result.ok, result.file_errors
        assert result.replaced_rows == 4 and result.imported_rows == 2
        names = (await session.execute(select(Equipment.equipment_name).where(Equipment.ef_code == "EF99"))).scalars().all()
        assert sorted(names) == ["REAL1", "REAL2"]
        assert await session.scalar(select(func.count()).select_from(EquipmentExtraAttribute)) == 2
        assert await _ef1_fingerprint(session) == before


async def test_import_failure_mid_way_rolls_back_everything(client, session_factory, tmp_path):
    async with session_factory() as session:
        await _seed_fake(session, n=2)
        before_names = sorted(
            (await session.execute(select(Equipment.equipment_name).where(Equipment.ef_code == "EF99"))).scalars().all()
        )

        # 검증은 통과하지만 두 번째 행 계산에서 실패 — replace로 지운 것까지 되돌아와야 한다.
        result = await import_file(_write_dat(tmp_path, ["NEW1", "BOOM"]), "EF99", session, replace=True)

        assert not result.ok
        assert result.imported_rows == 0 and result.replaced_rows == 0
        assert "rollback" in result.file_errors[0]
        after_names = sorted(
            (await session.execute(select(Equipment.equipment_name).where(Equipment.ef_code == "EF99"))).scalars().all()
        )
        assert after_names == before_names


async def test_import_rejects_rows_of_another_type(client, session_factory, tmp_path):
    async with session_factory() as session:
        result = await import_file(_write_dat(tmp_path, ["X1"], ef_code="EF1"), "EF99", session)
        assert not result.ok
        assert result.row_errors[0].column == "EF_code"
        assert await count_type(session, "EF99") == 0


async def test_import_rejects_unregistered_type(session_factory, tmp_path):
    async with session_factory() as session:
        result = await import_file(_write_dat(tmp_path, ["X1"], ef_code="EF42"), "EF42", session)
        assert not result.ok
        assert "등록되지 않은 설비유형" in result.file_errors[0]
