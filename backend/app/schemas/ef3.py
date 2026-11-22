"""EF3(초고압케이블) 상세 응답 스키마 (Stage 9-3). 필드는 app/db/models/cable.py 컬럼과 1:1."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CableSpecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    cable_sq: int | None
    cable_per_phase: int | None
    cable_mva: int | None
    tl_apply: str | None
    tl_num: int | None
    laying_type: str | None
    laying_type2: str | None
    mid_joint: int | None
    end_joint: str | None
    end_joint2: str | None


class CableConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    recent_diag_date: date | None
    max_load: int | None
    max_temp: float | None
    max_temp_diag: str | None
    diff_temp: float | None
    diff_temp_diag: str | None
    pd_signal_3Mhz: int | None
    pd_signal_6Mhz: int | None
    pd_signal_10Mhz: int | None
    pd_diag_rslt: str | None
    pd_num: int | None
    sys_cycle_theo_curr: float | None
    sys_cycle_curr: float | None
    sys_cycle_curr_diag: str | None
    svl_leak_curr: float | None
    svl_leak_curr_diag: str | None
    basic_leak_curr: float | None
    third_har_leak_curr: float | None  # 입력 이름 3rd_har_leak_curr
    la_leak_curr_diag: str | None
    joint_ex_damage: str | None
    cable_move: float | None


class CableConsequenceAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    emerge_resp: str | None
    rep_cost: str | None
    rep_time: str | None


class CableDesignAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    reliability: str | None
    temp_diag: str | None
    pd_diag: str | None
    live_line_diag: str | None
    cable_move_diag: str | None
    offline_diag: str | None
    longlife_insul: str | None


class CableScoreDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    computed_at: datetime
    today: date
    operation_year: float
    age_minus: float
    load_percent: float | None
    load_minus: float
    temp_minus: float
    diff_temp_minus: float
    failure_rate: float | None
    failure_rate_minus: float
    pd_minus: float
    sys_cycle_curr_minus: float
    svl_leak_curr_minus: float
    la_leak_curr_minus: float
    joint_ex_damage_minus: float
    cable_move_minus: float
    risk_mva: int | None
    risk_mva_minus: float
    tl_minus: float
    laying_type_minus: float
    mid_joint_minus: float
    end_joint_minus: float
    emerge_resp_minus: float
    rep_cost_minus: float
    rep_time_minus: float
    reliability_minus: float
    temp_diag_minus: float
    pd_diag_minus: float
    live_line_diag_minus: float
    cable_move_diag_minus: float
    offline_diag_minus: float
    longlife_insul_minus: float


class Ef3Detail(BaseModel):
    """EF3 유형 전용 상세 — EquipmentDetail.type_detail에 ef_code로 구분되어 들어간다."""

    ef_code: Literal["EF3"] = "EF3"
    spec: CableSpecOut
    condition: CableConditionOut
    consequence: CableConsequenceAttributeOut
    design: CableDesignAttributeOut
    score_detail: CableScoreDetailOut
