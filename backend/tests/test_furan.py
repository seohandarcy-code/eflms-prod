"""EF1 Furan 연평균 = 합계 ÷ 진단 시점 사용년수 (2026-11-19 사용자 결정).

- (Furan 진단일 - 가동년월)로 나눠 계산 기준일과 무관 — 5개년 예측·매일 점수 갱신에도 Furan 판정이 바뀌지 않는다.
- 진단일 ≤ 가동년월이면 평가 불가(사용년수·연평균·판정 null, 감점 0) + 임포트 경고. 설치 직후 설비도 계산 오류가 없다.
- 목업 진단일은 가동년월과 오늘 사이. 새 계산 칸 furan_diag_year 마이그레이션 왕복.
"""
import random
import sqlite3
from datetime import date, timedelta

import pytest
from alembic import command
from alembic.config import Config

from app.core.config import BACKEND_DIR, get_settings
from app.equipment_types import ef1_transformer
from app.services.import_service import import_file

BASE = date(2026, 11, 19)


def _row(start, diag, fal=20):
    row = ef1_transformer.generate_input_row()
    row["operation_start_time"], row["furan_diag_time"] = start, diag
    for name in ("furan_5H2F", "furan_2FOL", "furan_2ACF", "furan_5M2F"):
        row[name] = 0
    row["furan_2FAL"] = fal
    return row


def test_furan_uses_years_at_diagnosis_and_ignores_calculation_date():
    row = _row(date(2020, 1, 1), date(2024, 1, 1))  # 진단 시점 4.0년 → 20 ÷ 4.0 = 5.0(5 초과 아님 → 정상)
    outs = [ef1_transformer.calculate(row, as_of=BASE + timedelta(days=365 * y)) for y in range(6)]
    assert {o["furan_diag_year"] for o in outs} == {4.0}
    assert {o["furan_total_per_year"] for o in outs} == {20 / (1461 / 365)}
    assert {(o["furan_desc"], o["furan_minus"]) for o in outs} == {("정상", 0.0)}
    hot = ef1_transformer.calculate(_row(date(2020, 1, 1), date(2023, 1, 1)), as_of=BASE)  # 3.0년 → 6.7
    assert (hot["furan_diag_year"], hot["furan_desc"], hot["furan_minus"]) == (3.0, "이상", -24.0)


@pytest.mark.parametrize("diag_offset", [0, -30])
def test_diagnosis_not_after_install_is_not_evaluated(diag_offset):
    start = date(2022, 5, 1)
    out = ef1_transformer.calculate(_row(start, start + timedelta(days=diag_offset)), as_of=BASE)
    assert (out["furan_diag_year"], out["furan_total_per_year"], out["furan_desc"], out["furan_minus"]) == (None, None, None, 0.0)
    assert out["pof"] == round(100 + out["pof_minus"], 1)


def test_freshly_installed_transformer_calculates_without_error():
    start = BASE - timedelta(days=5)  # 운전년수 0.0 — 예전엔 Furan에서 0으로 나눠 계산 오류
    out = ef1_transformer.calculate(_row(start, start + timedelta(days=3), fal=1), as_of=BASE)
    assert out["operation_year"] == 0.0 and out["furan_diag_year"] == 0.0 and out["furan_desc"] == "이상"


def test_mock_diagnosis_date_is_between_install_and_today():
    random.seed(3)
    for _ in range(300):
        row = ef1_transformer.generate_input_row()
        assert row["operation_start_time"] < row["furan_diag_time"] <= max(date.today(), row["operation_start_time"] + timedelta(days=30))
        assert ef1_transformer.calculate(row)["furan_diag_year"] is not None


async def test_import_warns_about_unevaluated_furan(session_factory, tmp_path):
    good, bad = _row(date(2020, 1, 1), date(2023, 1, 1)), _row(date(2022, 1, 1), date(2021, 6, 1))
    names = [c["name"] for c in ef1_transformer.INPUT_COLUMNS]
    fmt = lambda v: v.isoformat() if isinstance(v, date) else str(v)  # noqa: E731
    path = tmp_path / "ef1.dat"
    path.write_text("\t".join(names) + "\n" + "\n".join("\t".join(fmt(r[n]) for n in names) for r in (good, bad)) + "\n", encoding="utf-8")
    async with session_factory() as session:
        result = await import_file(str(path), "EF1", session)
    assert result.ok and result.imported_rows == 2
    assert len(result.warnings) == 1 and "1건(3행)" in result.warnings[0] and "Furan" in result.warnings[0]


def test_furan_diag_year_migration_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "furan.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()

    def cols():
        with sqlite3.connect(db_path) as conn:
            return {r[1] for r in conn.execute("PRAGMA table_info(transformer_score_detail)")}

    try:
        cfg = Config()
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        command.upgrade(cfg, "head")
        assert "furan_diag_year" in cols()
        command.downgrade(cfg, "d4b9a2c6e8f1")
        assert "furan_diag_year" not in cols()
        command.upgrade(cfg, "head")
        assert "furan_diag_year" in cols()
    finally:
        get_settings.cache_clear()
