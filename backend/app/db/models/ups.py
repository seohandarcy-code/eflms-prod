"""EF5(UPS) 전용 테이블 (Stage 13-1). 매핑은 docs/DATA_DICTIONARY.md "EF5(UPS)" 절.

EF1~EF4와 같은 원칙: 입력은 성격별 테이블로 나누고(설비당 1행 + 시점 컬럼 — 이력 전환 대비),
계산값은 ups_score_detail에 둔다. 공통 PoF/CoF/DoF/종합점수는 score_snapshot(공통)에 있다.
사업장·설비코드(eqp_id)·설치년월은 공통 equipment에 있다. 원본에 전압 입력이 없어
equipment.voltage는 0으로 저장한다(EF4와 같음, 공통 화면은 전압을 표시하지 않음).
입력 컬럼은 처음부터 null 허용(입력파일 N/A — Stage 11 규칙), 감점은 소수 첫째 자리(Stage 13-0)라 FLOAT.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UpsSpec(Base):
    """설비 정보(라인·제작사·모델명)와 정격용량 — 정격용량만 CoF 계산(부하량)에 쓰인다."""

    __tablename__ = "ups_spec"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    line_no: Mapped[str | None] = mapped_column(String(50))
    manufacturer: Mapped[str | None] = mapped_column(String(50))
    model_name: Mapped[str | None] = mapped_column(String(50))
    capa: Mapped[int | None] = mapped_column(Integer)


class UpsCondition(Base):
    """운전·점검 상태 — PoF."""

    __tablename__ = "ups_condition"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    measured_at: Mapped[date] = mapped_column(Date)
    fan_replace_no: Mapped[int | None] = mapped_column(Integer)
    elec_room_max_temp: Mapped[float | None] = mapped_column(Float)
    load: Mapped[float | None] = mapped_column(Float)
    mod_cir_curr: Mapped[int | None] = mapped_column(Integer)
    mod_vol_diff: Mapped[int | None] = mapped_column(Integer)
    noise: Mapped[int | None] = mapped_column(Integer)
    thermal_img_chk: Mapped[str | None] = mapped_column(String(10))
    ex_box_chk: Mapped[str | None] = mapped_column(String(10))


class UpsConsequenceAttribute(Base):
    """고장 영향 등급 — CoF. 정격용량은 ups_spec에 있다."""

    __tablename__ = "ups_consequence_attribute"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    ins_build_rank: Mapped[str | None] = mapped_column(String(10))
    fire_spread_rank: Mapped[str | None] = mapped_column(String(10))
    emerge_resp: Mapped[str | None] = mapped_column(String(10))
    rep_time: Mapped[str | None] = mapped_column(String(10))
    rep_cost: Mapped[str | None] = mapped_column(String(10))


class UpsDesignAttribute(Base):
    """설계·방어 수준 등급 — DoF."""

    __tablename__ = "ups_design_attribute"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    sys_rel: Mapped[str | None] = mapped_column(String(10))
    emerge_sys: Mapped[str | None] = mapped_column(String(10))
    fac_rel: Mapped[str | None] = mapped_column(String(10))
    part_shortage: Mapped[str | None] = mapped_column(String(10))
    model_type: Mapped[str | None] = mapped_column(String(10))
    switching_type: Mapped[str | None] = mapped_column(String(10))
    igbt_rev: Mapped[str | None] = mapped_column(String(10))
    online_diag: Mapped[str | None] = mapped_column(String(10))


class UpsScoreDetail(Base):
    """EF5 세부 감점 breakdown — score_snapshot에 들어가는 7개 필드를 제외한 계산 컬럼 전부.

    null 가능: 전기실최대온도가 N/A면 부품 5종 상태점수, 팬교체횟수가 N/A면 fan 사용수명,
    부하율·정격용량이 N/A면 부하량(그 값을 쓰는 감점은 0 — app/equipment_types/na.py).
    """

    __tablename__ = "ups_score_detail"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    today: Mapped[date] = mapped_column(Date)
    operation_year: Mapped[float] = mapped_column(Float)
    age_minus: Mapped[float] = mapped_column(Float)
    cb_replace_no: Mapped[int] = mapped_column(Integer)
    cb_life_year: Mapped[float] = mapped_column(Float)
    cb_stat: Mapped[float | None] = mapped_column(Float)
    cb_stat_minus: Mapped[float] = mapped_column(Float)
    cap_life_year: Mapped[float] = mapped_column(Float)
    cap_stat: Mapped[float | None] = mapped_column(Float)
    cap_stat_minus: Mapped[float] = mapped_column(Float)
    fan_life_year: Mapped[float | None] = mapped_column(Float)
    fan_stat: Mapped[float | None] = mapped_column(Float)
    fan_stat_minus: Mapped[float] = mapped_column(Float)
    igbt_life_year: Mapped[float] = mapped_column(Float)
    igbt_stat: Mapped[float | None] = mapped_column(Float)
    igbt_stat_minus: Mapped[float] = mapped_column(Float)
    board_life_year: Mapped[float] = mapped_column(Float)
    board_stat: Mapped[float | None] = mapped_column(Float)
    board_stat_minus: Mapped[float] = mapped_column(Float)
    elec_room_max_temp_minus: Mapped[float] = mapped_column(Float)
    load_minus: Mapped[float] = mapped_column(Float)
    mod_cir_curr_minus: Mapped[float] = mapped_column(Float)
    mod_vol_diff_minus: Mapped[float] = mapped_column(Float)
    noise_minus: Mapped[float] = mapped_column(Float)
    thermal_img_chk_minus: Mapped[float] = mapped_column(Float)
    ex_box_chk_minus: Mapped[float] = mapped_column(Float)

    capa_times_load: Mapped[float | None] = mapped_column(Float)
    capa_times_load_minus: Mapped[float] = mapped_column(Float)
    ins_build_rank_minus: Mapped[float] = mapped_column(Float)
    fire_spread_rank_minus: Mapped[float] = mapped_column(Float)
    emerge_resp_minus: Mapped[float] = mapped_column(Float)
    rep_time_minus: Mapped[float] = mapped_column(Float)
    rep_cost_minus: Mapped[float] = mapped_column(Float)

    sys_rel_minus: Mapped[float] = mapped_column(Float)
    emerge_sys_minus: Mapped[float] = mapped_column(Float)
    fac_rel_minus: Mapped[float] = mapped_column(Float)
    part_shortage_minus: Mapped[float] = mapped_column(Float)
    model_type_minus: Mapped[float] = mapped_column(Float)
    switching_type_minus: Mapped[float] = mapped_column(Float)
    igbt_rev_minus: Mapped[float] = mapped_column(Float)
    online_diag_minus: Mapped[float] = mapped_column(Float)
