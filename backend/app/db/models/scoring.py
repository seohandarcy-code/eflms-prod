"""계산 데이터. score_snapshot은 모든 설비유형 공통 계약, transformer_score_detail은 EF1 전용
breakdown (다른 설비유형이 생기면 ef2_score_detail처럼 별도 테이블을 추가한다)."""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshot"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    # 소수 첫째 자리(2026-11-06, 마이그레이션 e1a5c0d3f7b2) — app/equipment_types/rounding.py
    pof_minus: Mapped[float] = mapped_column(Float)
    pof: Mapped[float] = mapped_column(Float)
    cof_minus: Mapped[float] = mapped_column(Float)
    cof: Mapped[float] = mapped_column(Float)
    dof_minus: Mapped[float] = mapped_column(Float)
    dof: Mapped[float] = mapped_column(Float)
    total_score: Mapped[float] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TransformerScoreDetail(Base):
    """EF1(변압기) 전용 세부 감점 breakdown. score_snapshot에 들어가는 4개 필드를 제외한 나머지 전부."""

    __tablename__ = "transformer_score_detail"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    today: Mapped[date] = mapped_column(Date)
    operation_year: Mapped[float] = mapped_column(Float)
    age_minus: Mapped[float] = mapped_column(Float)

    dga_tcg: Mapped[float | None] = mapped_column(Float)
    dga_diag: Mapped[str | None] = mapped_column(String(20))
    dga_minus: Mapped[float] = mapped_column(Float)
    load_minus: Mapped[float] = mapped_column(Float)
    temp_minus: Mapped[float] = mapped_column(Float)
    dielec_str_te_avg: Mapped[float | None] = mapped_column(Float)
    dielec_str_te_diag: Mapped[str | None] = mapped_column(String(20))
    dielec_str_te_minus: Mapped[float] = mapped_column(Float)
    acid_measure_desc: Mapped[str | None] = mapped_column(String(20))
    acid_measure_minus: Mapped[float] = mapped_column(Float)
    moisture_desc: Mapped[str | None] = mapped_column(String(20))
    moisture_minus: Mapped[float] = mapped_column(Float)
    furan_total: Mapped[float | None] = mapped_column(Float)
    furan_total_per_year: Mapped[float | None] = mapped_column(Float)
    furan_desc: Mapped[str | None] = mapped_column(String(20))
    furan_minus: Mapped[float] = mapped_column(Float)
    part_discharge_minus: Mapped[float] = mapped_column(Float)
    oltc_96t_minus: Mapped[float] = mapped_column(Float)
    oltc_diag: Mapped[str | None] = mapped_column(String(20))
    oltc_minus: Mapped[float] = mapped_column(Float)
    thermal_img_minus: Mapped[float] = mapped_column(Float)
    noise_minus: Mapped[float] = mapped_column(Float)

    first_voltage: Mapped[int] = mapped_column(Integer)
    first_voltage_minus: Mapped[float] = mapped_column(Float)
    capa_times_load: Mapped[float | None] = mapped_column(Float)
    productivity_minus: Mapped[float] = mapped_column(Float)
    fire_minus: Mapped[float] = mapped_column(Float)
    fire_spread_minus: Mapped[float] = mapped_column(Float)
    emerge_response_minus: Mapped[float] = mapped_column(Float)
    rep_cost: Mapped[float] = mapped_column(Float)
    rep_cost_minus: Mapped[float] = mapped_column(Float)
    rep_time: Mapped[int] = mapped_column(Integer)
    rep_time_minus: Mapped[float] = mapped_column(Float)

    redundancy_minus: Mapped[float] = mapped_column(Float)
    ato_minus: Mapped[float] = mapped_column(Float)
    online_og_minus: Mapped[float] = mapped_column(Float)
    offline_safety_minus: Mapped[float] = mapped_column(Float)
    sec_minus: Mapped[float] = mapped_column(Float)
    alarm_minus: Mapped[float] = mapped_column(Float)
    winding_minus: Mapped[float] = mapped_column(Float)
    prod_life_minus: Mapped[float] = mapped_column(Float)
    connect_part_minus: Mapped[float] = mapped_column(Float)
    temp_inc_limit_minus: Mapped[float] = mapped_column(Float)
    test_reliability_minus: Mapped[float] = mapped_column(Float)
    bushing_minus: Mapped[float] = mapped_column(Float)
    oltc2_minus: Mapped[float] = mapped_column(Float)
