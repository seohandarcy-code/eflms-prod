"""EF4(수배전반) 전용 테이블 (Stage 10-1). 매핑은 docs/DATA_DICTIONARY.md "EF4(수배전반)" 절.

EF1~EF3과 같은 원칙: 입력은 성격별 테이블로 나누고(설비당 1행 + 시점 컬럼 — 이력 전환 대비),
계산값은 switchgear_score_detail에 둔다. 공통 PoF/CoF/DoF/종합점수는 score_snapshot(공통)에 있다.
사업장·설비코드(eqp_id)·가동년월은 공통 equipment에 있다. 원본에 전압 입력이 없어
equipment.voltage는 0으로 저장한다(공통 화면은 전압을 표시하지 않음 — Stage 10-0).
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SwitchgearSpec(Base):
    """설비 식별·설치 위치 — install_building(설치건물 분류)만 CoF 계산에 쓰인다."""

    __tablename__ = "switchgear_spec"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    eqp_id_name: Mapped[str] = mapped_column(String(50))
    eqp_building: Mapped[str] = mapped_column(String(50))
    eqp_disting: Mapped[str] = mapped_column(String(20))
    eqp_floor: Mapped[str] = mapped_column(String(20))
    install_building: Mapped[str] = mapped_column(String(20))


class SwitchgearCondition(Base):
    """점검결과(열적·물리적 요소) — PoF."""

    __tablename__ = "switchgear_condition"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    measured_at: Mapped[date] = mapped_column(Date)
    part_thermal_chk: Mapped[str] = mapped_column(String(10))
    elec_room_avg_temp: Mapped[int] = mapped_column(Integer)
    temp_diff_chk: Mapped[int] = mapped_column(Integer)
    max_temp_chk: Mapped[int] = mapped_column(Integer)
    load_chk: Mapped[float] = mapped_column(Float)
    ex_box_chk: Mapped[str] = mapped_column(String(10))
    noise_chk: Mapped[str] = mapped_column(String(10))
    bolt_chk: Mapped[str] = mapped_column(String(10))


class SwitchgearConsequenceAttribute(Base):
    """고장 영향(계통·비용·기간 요소) — CoF. 설치건물은 switchgear_spec에 있다."""

    __tablename__ = "switchgear_consequence_attribute"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    scale_dam_chk: Mapped[float] = mapped_column(Float)
    sup_sys_chk: Mapped[str] = mapped_column(String(10))
    prod_chk: Mapped[str] = mapped_column(String(10))
    op_chk: Mapped[str] = mapped_column(String(10))
    replace_chk: Mapped[float] = mapped_column(Float)
    recovery_time_chk: Mapped[float] = mapped_column(Float)
    replace_time_chk: Mapped[int] = mapped_column(Integer)


class SwitchgearDesignAttribute(Base):
    """설계·방어 수준(이중화, ATO, 점검·진단, 부품단종) — DoF."""

    __tablename__ = "switchgear_design_attribute"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    reliability: Mapped[str] = mapped_column(String(10))
    ato: Mapped[str] = mapped_column(String(10))
    cb_inspect: Mapped[str] = mapped_column(String(10))
    relay_chk: Mapped[str] = mapped_column(String(10))
    online_diag: Mapped[str] = mapped_column(String(10))
    part_shortage: Mapped[str] = mapped_column(String(10))


class SwitchgearScoreDetail(Base):
    """EF4 세부 감점 breakdown — score_snapshot에 들어가는 7개 필드를 제외한 계산 컬럼 전부."""

    __tablename__ = "switchgear_score_detail"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    today: Mapped[date] = mapped_column(Date)
    operation_year: Mapped[float] = mapped_column(Float)
    age_minus: Mapped[int] = mapped_column(Integer)
    cb_op_year: Mapped[float] = mapped_column(Float)
    cb_stat: Mapped[float] = mapped_column(Float)
    cb_stat_minus: Mapped[int] = mapped_column(Integer)
    durability_minus: Mapped[int] = mapped_column(Integer)
    part_thermal_chk_minus: Mapped[int] = mapped_column(Integer)
    elec_room_avg_temp_minus: Mapped[int] = mapped_column(Integer)
    temp_diff_chk_minus: Mapped[int] = mapped_column(Integer)
    max_temp_chk_minus: Mapped[int] = mapped_column(Integer)
    load_minus: Mapped[int] = mapped_column(Integer)
    thermal_minus: Mapped[int] = mapped_column(Integer)
    ex_box_chk_minus: Mapped[int] = mapped_column(Integer)
    noise_chk_minus: Mapped[int] = mapped_column(Integer)
    bolt_chk_minus: Mapped[int] = mapped_column(Integer)
    phy_minus: Mapped[int] = mapped_column(Integer)

    scale_dam_chk_minus: Mapped[int] = mapped_column(Integer)
    install_building_minus: Mapped[int] = mapped_column(Integer)
    sup_sys_chk_minus: Mapped[int] = mapped_column(Integer)
    cof_sys_minus: Mapped[int] = mapped_column(Integer)
    prod_chk_minus: Mapped[int] = mapped_column(Integer)
    op_chk_minus: Mapped[int] = mapped_column(Integer)
    replace_chk_minus: Mapped[int] = mapped_column(Integer)
    cof_cost_minus: Mapped[int] = mapped_column(Integer)
    recovery_time_chk_minus: Mapped[int] = mapped_column(Integer)
    replace_time_chk_minus: Mapped[int] = mapped_column(Integer)
    cof_recov_minus: Mapped[int] = mapped_column(Integer)

    operation_start_year: Mapped[int] = mapped_column(Integer)
    reliability_minus: Mapped[int] = mapped_column(Integer)
    ato_minus: Mapped[int] = mapped_column(Integer)
    dof_sys_minus: Mapped[int] = mapped_column(Integer)
    cb_inspect_minus: Mapped[int] = mapped_column(Integer)
    relay_chk_minus: Mapped[int] = mapped_column(Integer)
    online_diag_minus: Mapped[int] = mapped_column(Integer)
    dof_cost_minus: Mapped[int] = mapped_column(Integer)
    part_shortage_minus: Mapped[int] = mapped_column(Integer)
    ct_use: Mapped[str] = mapped_column(String(10))
    ct_use_minus: Mapped[int] = mapped_column(Integer)
    longlife_fan_use: Mapped[str] = mapped_column(String(10))
    lighting_use: Mapped[str] = mapped_column(String(10))
    spec_use_minus: Mapped[int] = mapped_column(Integer)
    dof_recov_minus: Mapped[int] = mapped_column(Integer)
