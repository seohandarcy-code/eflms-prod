"""EF3(초고압케이블) 전용 테이블 (Stage 9-1). 매핑은 docs/DATA_DICTIONARY.md "EF3(초고압케이블)" 절.

EF1·EF2와 같은 원칙: 입력은 성격별 테이블로 나누고(설비당 1행 + 시점 컬럼 — 이력 전환 대비),
계산값은 cable_score_detail에 둔다. 공통 PoF/CoF/DoF/종합점수는 score_snapshot(공통)에 있다.
사업장·T/L명·전압·가동년월은 공통 equipment에 있다.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CableSpec(Base):
    """케이블 사양·포설 — 부하율 분모(회선별용량)와 CoF."""

    __tablename__ = "cable_spec"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    cable_sq: Mapped[int | None] = mapped_column(Integer)
    cable_per_phase: Mapped[int | None] = mapped_column(Integer)
    cable_mva: Mapped[int | None] = mapped_column(Integer)
    tl_apply: Mapped[str | None] = mapped_column(String(20))  # 타T/L공동포설여부(Stage 22)
    tl_num: Mapped[int | None] = mapped_column(Integer)  # 타T/L회선수(Stage 22)
    laying_type: Mapped[str | None] = mapped_column(String(20))
    laying_type2: Mapped[str | None] = mapped_column(String(20))  # 포설방법2(Stage 22)
    mid_joint: Mapped[int | None] = mapped_column(Integer)
    end_joint: Mapped[str | None] = mapped_column(String(20))
    end_joint2: Mapped[str | None] = mapped_column(String(20))  # 종단접속함종류2(Stage 22)


class CableCondition(Base):
    """운전·상태 측정값 — PoF."""

    __tablename__ = "cable_condition"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    measured_at: Mapped[date] = mapped_column(Date)
    recent_diag_date: Mapped[date | None] = mapped_column(Date)  # 안전공사최근진단일 — 화면의 최근 진단일(Stage 22)
    max_load: Mapped[int | None] = mapped_column(Integer)
    max_temp: Mapped[float | None] = mapped_column(Float)
    max_temp_diag: Mapped[str | None] = mapped_column(String(10))
    diff_temp: Mapped[float | None] = mapped_column(Float)
    diff_temp_diag: Mapped[str | None] = mapped_column(String(10))
    # 대소문자는 입력 컬럼 이름 그대로(pd_signal_3Mhz)
    pd_signal_3Mhz: Mapped[int | None] = mapped_column(Integer)
    pd_signal_6Mhz: Mapped[int | None] = mapped_column(Integer)
    pd_signal_10Mhz: Mapped[int | None] = mapped_column(Integer)
    pd_diag_rslt: Mapped[str | None] = mapped_column(String(10))
    pd_num: Mapped[int | None] = mapped_column(Integer)  # Stage 22부터 계산에 안 씀(보관)
    sys_cycle_theo_curr: Mapped[float | None] = mapped_column(Float)
    sys_cycle_curr: Mapped[float | None] = mapped_column(Float)
    sys_cycle_curr_diag: Mapped[str | None] = mapped_column(String(10))
    svl_leak_curr: Mapped[float | None] = mapped_column(Float)
    svl_leak_curr_diag: Mapped[str | None] = mapped_column(String(10))
    basic_leak_curr: Mapped[float | None] = mapped_column(Float)
    third_har_leak_curr: Mapped[float | None] = mapped_column(Float)  # 입력 이름 3rd_har_leak_curr
    la_leak_curr_diag: Mapped[str | None] = mapped_column(String(10))
    joint_ex_damage: Mapped[str | None] = mapped_column(String(10))
    cable_move: Mapped[float | None] = mapped_column(Float)


class CableConsequenceAttribute(Base):
    """고장 영향 코드 — CoF."""

    __tablename__ = "cable_consequence_attribute"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    emerge_resp: Mapped[str | None] = mapped_column(String(20))
    rep_cost: Mapped[str | None] = mapped_column(String(10))  # 사고복구비용 등급(Stage 22 — 예전엔 케이블길이로 계산)
    rep_time: Mapped[str | None] = mapped_column(String(20))


class CableDesignAttribute(Base):
    """설계·방어 수준(회선수, O/X, 진단 주기) — DoF."""

    __tablename__ = "cable_design_attribute"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    reliability: Mapped[str | None] = mapped_column(String(10))  # N+0/N+1/N+N(Stage 22 — 예전엔 회선수)
    temp_diag: Mapped[str | None] = mapped_column(String(10))
    pd_diag: Mapped[str | None] = mapped_column(String(10))
    live_line_diag: Mapped[str | None] = mapped_column(String(10))
    cable_move_diag: Mapped[str | None] = mapped_column(String(10))
    offline_diag: Mapped[str | None] = mapped_column(String(20))
    longlife_insul: Mapped[str | None] = mapped_column(String(10))


class CableScoreDetail(Base):
    """EF3 세부 감점 breakdown — score_snapshot에 들어가는 7개 필드를 제외한 계산 컬럼 전부."""

    __tablename__ = "cable_score_detail"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    today: Mapped[date] = mapped_column(Date)
    operation_year: Mapped[float] = mapped_column(Float)
    age_minus: Mapped[float] = mapped_column(Float)
    load_percent: Mapped[float | None] = mapped_column(Float)
    load_minus: Mapped[float] = mapped_column(Float)
    temp_minus: Mapped[float] = mapped_column(Float)
    diff_temp_minus: Mapped[float] = mapped_column(Float)
    failure_rate: Mapped[float | None] = mapped_column(Float)  # 온도기반손상률 계산값(Stage 22 — 예전엔 입력)
    failure_rate_minus: Mapped[float] = mapped_column(Float)
    pd_minus: Mapped[float] = mapped_column(Float)
    sys_cycle_curr_minus: Mapped[float] = mapped_column(Float)
    svl_leak_curr_minus: Mapped[float] = mapped_column(Float)
    la_leak_curr_minus: Mapped[float] = mapped_column(Float)
    joint_ex_damage_minus: Mapped[float] = mapped_column(Float)
    cable_move_minus: Mapped[float] = mapped_column(Float)

    risk_mva: Mapped[int | None] = mapped_column(Integer)
    risk_mva_minus: Mapped[float] = mapped_column(Float)
    tl_minus: Mapped[float] = mapped_column(Float)
    laying_type_minus: Mapped[float] = mapped_column(Float)
    mid_joint_minus: Mapped[float] = mapped_column(Float)
    end_joint_minus: Mapped[float] = mapped_column(Float)
    emerge_resp_minus: Mapped[float] = mapped_column(Float)
    rep_cost_minus: Mapped[float] = mapped_column(Float)
    rep_time_minus: Mapped[float] = mapped_column(Float)

    reliability_minus: Mapped[float] = mapped_column(Float)
    temp_diag_minus: Mapped[float] = mapped_column(Float)
    pd_diag_minus: Mapped[float] = mapped_column(Float)
    live_line_diag_minus: Mapped[float] = mapped_column(Float)
    cable_move_diag_minus: Mapped[float] = mapped_column(Float)
    offline_diag_minus: Mapped[float] = mapped_column(Float)
    longlife_insul_minus: Mapped[float] = mapped_column(Float)
