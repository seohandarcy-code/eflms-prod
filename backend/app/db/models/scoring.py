"""계산 데이터. score_snapshot은 모든 설비유형 공통 계약, transformer_score_detail은 EF1 전용
breakdown (다른 설비유형이 생기면 ef2_score_detail처럼 별도 테이블을 추가한다)."""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshot"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    pof_minus: Mapped[int] = mapped_column(Integer)
    pof: Mapped[int] = mapped_column(Integer)
    cof_minus: Mapped[int] = mapped_column(Integer)
    cof: Mapped[int] = mapped_column(Integer)
    dof_minus: Mapped[int] = mapped_column(Integer)
    dof: Mapped[int] = mapped_column(Integer)
    total_score: Mapped[float] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TransformerScoreDetail(Base):
    """EF1(변압기) 전용 세부 감점 breakdown. score_snapshot에 들어가는 4개 필드를 제외한 나머지 전부."""

    __tablename__ = "transformer_score_detail"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    today: Mapped[date] = mapped_column(Date)
    operation_year: Mapped[float] = mapped_column(Float)
    age_minus: Mapped[int] = mapped_column(Integer)

    dga_tcg: Mapped[float] = mapped_column(Float)
    dga_diag: Mapped[str] = mapped_column(String(20))
    dga_minus: Mapped[int] = mapped_column(Integer)
    load_minus: Mapped[int] = mapped_column(Integer)
    temp_minus: Mapped[int] = mapped_column(Integer)
    dielec_str_te_avg: Mapped[float] = mapped_column(Float)
    dielec_str_te_diag: Mapped[str] = mapped_column(String(20))
    dielec_str_te_minus: Mapped[int] = mapped_column(Integer)
    acid_measure_desc: Mapped[str] = mapped_column(String(20))
    acid_measure_minus: Mapped[int] = mapped_column(Integer)
    moisture_desc: Mapped[str] = mapped_column(String(20))
    moisture_minus: Mapped[int] = mapped_column(Integer)
    furan_total: Mapped[float] = mapped_column(Float)
    furan_total_per_year: Mapped[float] = mapped_column(Float)
    furan_desc: Mapped[str] = mapped_column(String(20))
    furan_minus: Mapped[int] = mapped_column(Integer)
    part_discharge_minus: Mapped[int] = mapped_column(Integer)
    oltc_96t_minus: Mapped[int] = mapped_column(Integer)
    oltc_diag: Mapped[str] = mapped_column(String(20))
    oltc_minus: Mapped[int] = mapped_column(Integer)
    thermal_img_minus: Mapped[int] = mapped_column(Integer)
    noise_minus: Mapped[int] = mapped_column(Integer)

    first_voltage: Mapped[int] = mapped_column(Integer)
    first_voltage_minus: Mapped[int] = mapped_column(Integer)
    capa_times_load: Mapped[float] = mapped_column(Float)
    productivity_minus: Mapped[int] = mapped_column(Integer)
    fire_minus: Mapped[int] = mapped_column(Integer)
    fire_spread_minus: Mapped[int] = mapped_column(Integer)
    emerge_response_minus: Mapped[int] = mapped_column(Integer)
    rep_cost: Mapped[float] = mapped_column(Float)
    rep_cost_minus: Mapped[int] = mapped_column(Integer)
    rep_time: Mapped[int] = mapped_column(Integer)
    rep_time_minus: Mapped[int] = mapped_column(Integer)

    redundancy_minus: Mapped[int] = mapped_column(Integer)
    ato_minus: Mapped[int] = mapped_column(Integer)
    online_og_minus: Mapped[int] = mapped_column(Integer)
    offline_safety_minus: Mapped[int] = mapped_column(Integer)
    sec_minus: Mapped[int] = mapped_column(Integer)
    alarm_minus: Mapped[int] = mapped_column(Integer)
    winding_minus: Mapped[int] = mapped_column(Integer)
    prod_life_minus: Mapped[int] = mapped_column(Integer)
    connect_part_minus: Mapped[int] = mapped_column(Integer)
    temp_inc_limit_minus: Mapped[int] = mapped_column(Integer)
    test_reliability_minus: Mapped[int] = mapped_column(Integer)
    bushing_minus: Mapped[int] = mapped_column(Integer)
    oltc2_minus: Mapped[int] = mapped_column(Integer)
