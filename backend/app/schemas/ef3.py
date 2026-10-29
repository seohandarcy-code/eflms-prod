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
    cable_length: int | None
    laying_type: str | None
    mid_joint: int | None
    end_joint: str | None


class CableConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    max_load: int | None
    max_temp: float | None
    diff_temp: float | None
    failure_rate: float | None
    pd_num: int | None
    sys_cycle_curr: float | None
    svl_leak_curr: float | None
    joint_ex_damage: str | None
    cable_move: float | None


class CableConsequenceAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    emerge_resp: str | None
    rep_time: str | None


class CableDesignAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    reliability: int | None
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
    age_minus: int
    load_percent: float | None
    load_minus: int
    temp_minus: int
    diff_temp_minus: int
    failure_rate_minus: int
    pd_minus: int
    sys_cycle_curr_minus: int
    svl_leak_curr_minus: int
    joint_ex_damage_minus: int
    cable_move_minus: int
    risk_mva: int | None
    risk_mva_minus: int
    laying_type_minus: int
    mid_joint_minus: int
    end_joint_minus: int
    emerge_resp_minus: int
    rep_cost: float | None
    rep_cost_minus: int
    rep_time_minus: int
    reliability_minus: int
    temp_diag_minus: int
    pd_diag_minus: int
    live_line_diag_minus: int
    cable_move_diag_minus: int
    offline_diag_minus: int
    longlife_insul_minus: int


class Ef3Detail(BaseModel):
    """EF3 유형 전용 상세 — EquipmentDetail.type_detail에 ef_code로 구분되어 들어간다."""

    ef_code: Literal["EF3"] = "EF3"
    spec: CableSpecOut
    condition: CableConditionOut
    consequence: CableConsequenceAttributeOut
    design: CableDesignAttributeOut
    score_detail: CableScoreDetailOut
