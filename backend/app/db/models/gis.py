"""EF2(GIS) 전용 테이블 (Stage 8-3). 매핑은 docs/DATA_DICTIONARY.md "EF2(GIS)" 절.

EF1과 같은 원칙: 입력은 성격별 테이블로 나누고(설비당 1행 + 시점 컬럼 — 이력 전환 대비),
계산값은 gis_score_detail에 둔다. 공통 PoF/CoF/DoF/종합점수는 score_snapshot(공통)에 있다.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GisOperation(Base):
    """차단·동작 이력과 전기적 운전 상태 — PoF 기계·전기."""

    __tablename__ = "gis_operation"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    measured_at: Mapped[date] = mapped_column(Date)
    op_type: Mapped[str] = mapped_column(String(20))
    cb_op_num: Mapped[int] = mapped_column(Integer)
    rated_trip_count: Mapped[int] = mapped_column(Integer)
    cum_trip_current: Mapped[int] = mapped_column(Integer)
    cb_op_char_over: Mapped[str] = mapped_column(String(10))
    load_percent: Mapped[float] = mapped_column(Float)
    leakage_curr: Mapped[float] = mapped_column(Float)


class GisDiagnosis(Base):
    """부분방전·전기실 온도 진단 — PoF 화학."""

    __tablename__ = "gis_diagnosis"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    measured_at: Mapped[date] = mapped_column(Date)
    part_dischar_pat: Mapped[str] = mapped_column(String(10))
    elec_room_max_temp: Mapped[int] = mapped_column(Integer)


class GisSf6Reading(Base):
    """SF6 가스 분석 — PoF 화학. diag_time은 원본 sf6_diag_time(화면 '최근 진단일')."""

    __tablename__ = "gis_sf6_reading"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    diag_time: Mapped[date] = mapped_column(Date)
    sf6_so2: Mapped[float] = mapped_column(Float)
    sf6_leak: Mapped[str] = mapped_column(String(10))
    sf6_h2o: Mapped[float] = mapped_column(Float)
    sf6_purity: Mapped[float] = mapped_column(Float)


class GisConsequenceAttribute(Base):
    """고장 영향 등급(A~E 코드) — CoF."""

    __tablename__ = "gis_consequence_attribute"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    in_vol: Mapped[str] = mapped_column(String(10))
    capa_times_load: Mapped[str] = mapped_column(String(10))
    fire_spread: Mapped[str] = mapped_column(String(10))
    env_loc: Mapped[str] = mapped_column(String(10))
    emerge_resp_pat: Mapped[str] = mapped_column(String(10))
    rep_cost: Mapped[str] = mapped_column(String(10))
    rep_time: Mapped[str] = mapped_column(String(10))


class GisDesignAttribute(Base):
    """설계·방어 수준(코드/Y·N) — DoF."""

    __tablename__ = "gis_design_attribute"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    in_line_num: Mapped[str] = mapped_column(String(10))
    ato: Mapped[str] = mapped_column(String(10))
    reliability: Mapped[str] = mapped_column(String(10))
    online_diag: Mapped[str] = mapped_column(String(10))
    offline_diag: Mapped[str] = mapped_column(String(10))
    tbm: Mapped[str] = mapped_column(String(10))
    conn_rev: Mapped[str] = mapped_column(String(10))
    leak_str: Mapped[str] = mapped_column(String(10))
    insul_str: Mapped[str] = mapped_column(String(10))
    vt_la_str: Mapped[str] = mapped_column(String(10))


class GisScoreDetail(Base):
    """EF2 세부 감점 breakdown — score_snapshot에 들어가는 7개 필드를 제외한 계산 컬럼 전부."""

    __tablename__ = "gis_score_detail"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    today: Mapped[date] = mapped_column(Date)
    operation_year: Mapped[float] = mapped_column(Float)
    age_minus: Mapped[int] = mapped_column(Integer)

    cb_op_num_minus: Mapped[int] = mapped_column(Integer)
    cb_op_year: Mapped[float] = mapped_column(Float)
    cb_stat: Mapped[float] = mapped_column(Float)
    cb_stat_minus: Mapped[int] = mapped_column(Integer)
    insul_year: Mapped[float] = mapped_column(Float)
    insul_stat: Mapped[float] = mapped_column(Float)
    insul_stat_minus: Mapped[int] = mapped_column(Integer)
    gis_mech_minus: Mapped[int] = mapped_column(Integer)

    rated_trip_count_minus: Mapped[int] = mapped_column(Integer)
    cum_trip_current_minus: Mapped[int] = mapped_column(Integer)
    cb_op_char_over_minus: Mapped[int] = mapped_column(Integer)
    load_minus: Mapped[int] = mapped_column(Integer)
    leakage_curr_minus: Mapped[int] = mapped_column(Integer)
    gis_elec_minus: Mapped[int] = mapped_column(Integer)

    part_dischar_minus: Mapped[int] = mapped_column(Integer)
    sf6_minus: Mapped[int] = mapped_column(Integer)
    elec_room_minus: Mapped[int] = mapped_column(Integer)
    gis_chem_minus: Mapped[int] = mapped_column(Integer)

    in_vol_minus: Mapped[int] = mapped_column(Integer)
    productivity_minus: Mapped[int] = mapped_column(Integer)
    fire_spread_minus: Mapped[int] = mapped_column(Integer)
    env_minus: Mapped[int] = mapped_column(Integer)
    emerge_resp_minus: Mapped[int] = mapped_column(Integer)
    rep_cost_minus: Mapped[int] = mapped_column(Integer)
    rep_time_minus: Mapped[int] = mapped_column(Integer)

    in_line_minus: Mapped[int] = mapped_column(Integer)
    ato_minus: Mapped[int] = mapped_column(Integer)
    reliability_minus: Mapped[int] = mapped_column(Integer)
    online_diag_minus: Mapped[int] = mapped_column(Integer)
    offline_diag_minus: Mapped[int] = mapped_column(Integer)
    tbm_minus: Mapped[int] = mapped_column(Integer)
    conn_rev_minus: Mapped[int] = mapped_column(Integer)
    leak_str_minus: Mapped[int] = mapped_column(Integer)
    insul_str_minus: Mapped[int] = mapped_column(Integer)
    vt_la_minus: Mapped[int] = mapped_column(Integer)
