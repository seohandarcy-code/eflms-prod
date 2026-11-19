"""EF4(수배전반) 상세 응답 스키마 (Stage 10-3). 필드는 app/db/models/switchgear.py 컬럼과 1:1."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class SwitchgearSpecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    eqp_id_name: str | None
    eqp_building: str | None
    eqp_disting: str | None
    eqp_floor: str | None
    install_building: str | None


class SwitchgearConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    part_thermal_chk: str | None
    elec_room_avg_temp: int | None
    temp_diff_chk: int | None
    max_temp_chk: int | None
    load_chk: float | None
    ex_box_chk: str | None
    noise_chk: str | None
    bolt_chk: str | None


class SwitchgearConsequenceAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    scale_dam_chk: float | None
    sup_sys_chk: str | None
    prod_chk: str | None
    op_chk: str | None
    replace_chk: float | None
    recovery_time_chk: float | None
    replace_time_chk: int | None


class SwitchgearDesignAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    reliability: str | None
    ato: str | None
    cb_inspect: str | None
    relay_chk: str | None
    online_diag: str | None
    part_shortage: str | None


class SwitchgearScoreDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    computed_at: datetime
    today: date
    operation_year: float
    age_minus: float
    cb_op_year: float
    cb_stat: float
    cb_stat_minus: float
    durability_minus: float
    part_thermal_chk_minus: float
    elec_room_avg_temp_minus: float
    temp_diff_chk_minus: float
    max_temp_chk_minus: float
    load_minus: float
    thermal_minus: float
    ex_box_chk_minus: float
    noise_chk_minus: float
    bolt_chk_minus: float
    phy_minus: float
    scale_dam_chk_minus: float
    install_building_minus: float
    sup_sys_chk_minus: float
    cof_sys_minus: float
    prod_chk_minus: float
    op_chk_minus: float
    replace_chk_minus: float
    cof_cost_minus: float
    recovery_time_chk_minus: float
    replace_time_chk_minus: float
    cof_recov_minus: float
    operation_start_year: int
    reliability_minus: float
    ato_minus: float
    dof_sys_minus: float
    cb_inspect_minus: float
    relay_chk_minus: float
    online_diag_minus: float
    dof_cost_minus: float
    part_shortage_minus: float
    ct_use: str
    ct_use_minus: float
    longlife_fan_use: str
    lighting_use: str
    spec_use_minus: float
    dof_recov_minus: float


class Ef4Detail(BaseModel):
    """EF4 유형 전용 상세 — EquipmentDetail.type_detail에 ef_code로 구분되어 들어간다."""

    ef_code: Literal["EF4"] = "EF4"
    spec: SwitchgearSpecOut
    condition: SwitchgearConditionOut
    consequence: SwitchgearConsequenceAttributeOut
    design: SwitchgearDesignAttributeOut
    score_detail: SwitchgearScoreDetailOut
