"""EF7(배터리) 전용 테이블 (Stage 15-1). 매핑은 docs/DATA_DICTIONARY.md "EF7(배터리)" 절.

EF4~EF6과 같은 원칙: 입력은 성격별 테이블로 나누고(설비당 1행 + 시점 컬럼 — 이력 전환 대비),
계산값은 battery_score_detail에 둔다. 공통 PoF/CoF/DoF/종합점수는 score_snapshot(공통)에 있다.
사업장·설비코드(eqp_id)·설치년월은 공통 equipment에 있다. 원본에 전압 입력이 없어
equipment.voltage는 0으로 저장한다(EF4~EF6과 같음).
입력 컬럼은 처음부터 null 허용(입력파일 N/A — Stage 11 규칙), 감점은 소수 첫째 자리(Stage 13-0)라 FLOAT.

**참고표**(Stage 15-0, 2026-11-16 사용자 결정): 배터리는 설비 입력 말고도 계산에 쓰는 표가 두 개 있다 —
방전이력(battery_discharge_history)과 온도감소계수(battery_temp_decay_coef). 설비에 딸린 행이 아니라
(equipment_id 없음) 따로 dat 파일로 넣고·교체하고·리셋한다(app/services/reference_service.py). 설비 리셋은
참고표를 지우지 않는다.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BatterySpec(Base):
    """설비 정보(라인·제작사·모델명)와 정격용량 — 정격용량만 CoF 계산(부하량)에 쓰인다."""

    __tablename__ = "battery_spec"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    line_no: Mapped[str | None] = mapped_column(String(50))
    manufacturer: Mapped[str | None] = mapped_column(String(50))
    model_name: Mapped[str | None] = mapped_column(String(50))
    capa: Mapped[float | None] = mapped_column(Float)


class BatteryCondition(Base):
    """셀·배터리실 상태 — PoF(부하율은 CoF 부하량에 쓰인다)."""

    __tablename__ = "battery_condition"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    measured_at: Mapped[date] = mapped_column(Date)
    vol_diff: Mapped[float | None] = mapped_column(Float)
    temp_diff: Mapped[float | None] = mapped_column(Float)
    temp_range_over: Mapped[float | None] = mapped_column(Float)
    bat_room_temp: Mapped[float | None] = mapped_column(Float)
    bat_room_humid: Mapped[float | None] = mapped_column(Float)
    load: Mapped[float | None] = mapped_column(Float)


class BatteryConsequenceAttribute(Base):
    """고장 영향 등급 — CoF. 정격용량은 battery_spec, 부하율은 battery_condition에 있다."""

    __tablename__ = "battery_consequence_attribute"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    con_rank: Mapped[str | None] = mapped_column(String(10))
    ins_build_rank: Mapped[str | None] = mapped_column(String(10))
    fire_spread_rank: Mapped[str | None] = mapped_column(String(10))
    emerge_resp: Mapped[str | None] = mapped_column(String(10))
    rep_time: Mapped[str | None] = mapped_column(String(10))
    rep_cost: Mapped[str | None] = mapped_column(String(10))


class BatteryDesignAttribute(Base):
    """설계·방어 수준 — DoF."""

    __tablename__ = "battery_design_attribute"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    updated_at: Mapped[date] = mapped_column(Date)
    model_gen: Mapped[int | None] = mapped_column(Integer)
    fire_resist: Mapped[str | None] = mapped_column(String(10))
    ul_auth: Mapped[str | None] = mapped_column(String(10))
    fac_rel: Mapped[int | None] = mapped_column(Integer)
    part_stat_diag: Mapped[str | None] = mapped_column(String(10))
    bat_server: Mapped[str | None] = mapped_column(String(10))
    bat_room_fire_resist: Mapped[str | None] = mapped_column(String(10))


class BatteryScoreDetail(Base):
    """EF7 세부 감점 breakdown — score_snapshot에 들어가는 7개 필드를 제외한 계산 컬럼 전부.

    방전인덱스합·온도감소계수는 **계산 당시 참고표로 낸 값**이라, 나중에 참고표가 바뀌어도 그때 점수의 근거가 남는다
    (참고표를 바꾸면 배터리 점수는 다시 계산되어 이 값도 같이 바뀐다).
    null 가능: 배터리실온도가 N/A면 온도감소계수·BMS 상태점수, 부하율·정격용량이 N/A면 부하량
    (그 값을 쓰는 감점은 0 — app/equipment_types/na.py).
    """

    __tablename__ = "battery_score_detail"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.equipment_id"), primary_key=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    today: Mapped[date] = mapped_column(Date)
    operation_year: Mapped[float] = mapped_column(Float)
    age_minus: Mapped[float] = mapped_column(Float)
    disch_index: Mapped[float] = mapped_column(Float)
    disch_dec_coef: Mapped[float] = mapped_column(Float)
    temp_dec_coef: Mapped[float | None] = mapped_column(Float)
    soh_minus: Mapped[float] = mapped_column(Float)
    bms_life: Mapped[float] = mapped_column(Float)
    bms_stat: Mapped[float | None] = mapped_column(Float)
    bms_minus: Mapped[float] = mapped_column(Float)
    vol_diff_minus: Mapped[float] = mapped_column(Float)
    temp_diff_minus: Mapped[float] = mapped_column(Float)
    temp_range_over_minus: Mapped[float] = mapped_column(Float)
    bat_room_temp_minus: Mapped[float] = mapped_column(Float)
    bat_room_humid_minus: Mapped[float] = mapped_column(Float)

    capa_times_load: Mapped[float | None] = mapped_column(Float)
    capa_times_load_minus: Mapped[float] = mapped_column(Float)
    con_rank_minus: Mapped[float] = mapped_column(Float)
    ins_build_rank_minus: Mapped[float] = mapped_column(Float)
    fire_spread_rank_minus: Mapped[float] = mapped_column(Float)
    emerge_resp_minus: Mapped[float] = mapped_column(Float)
    rep_time_minus: Mapped[float] = mapped_column(Float)
    rep_cost_minus: Mapped[float] = mapped_column(Float)

    model_gen_minus: Mapped[float] = mapped_column(Float)
    fire_resist_minus: Mapped[float] = mapped_column(Float)
    ul_auth_minus: Mapped[float] = mapped_column(Float)
    fac_rel_minus: Mapped[float] = mapped_column(Float)
    part_stat_diag_minus: Mapped[float] = mapped_column(Float)
    bat_server_minus: Mapped[float] = mapped_column(Float)
    bat_room_fire_resist_minus: Mapped[float] = mapped_column(Float)


# ------------------------------------------------------------------ 참고표 (설비에 딸리지 않음)
class BatteryDischargeHistory(Base):
    """방전이력 — 사업장별 방전 기록. 같은 사업장 + 설치일 이후 방전인덱스 합이 SOH 감점에 쓰인다.

    같은 행 판정(넣기 = 갱신/추가): 사업장 + 일자.
    """

    __tablename__ = "battery_discharge_history"
    __table_args__ = (UniqueConstraint("factory_code", "disch_date", name="uq_battery_discharge_history_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    disch_date: Mapped[date] = mapped_column(Date)
    factory_code: Mapped[str] = mapped_column(String(10))
    volt_change: Mapped[float] = mapped_column(Float)
    disch_index: Mapped[float] = mapped_column(Float)


class BatteryTempDecayCoef(Base):
    """온도감소계수 — 사용 년차별 계수(gamma_y). 1~n년 합 + 소수 보정에 배터리실 온도 배율을 곱해 SOH 감점에 쓴다.

    같은 행 판정: year.
    """

    __tablename__ = "battery_temp_decay_coef"

    year: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    gamma_y: Mapped[float] = mapped_column(Float)
