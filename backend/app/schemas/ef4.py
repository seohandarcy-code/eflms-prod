"""EF4(수배전반) 상세 응답 스키마 (Stage 10-3). 필드는 app/db/models/switchgear.py 컬럼과 1:1."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class SwitchgearSpecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    eqp_id_name: str
    eqp_building: str
    eqp_disting: str
    eqp_floor: str
    install_building: str


class SwitchgearConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    part_thermal_chk: str
    elec_room_avg_temp: int
    temp_diff_chk: int
    max_temp_chk: int
    load_chk: float
    ex_box_chk: str
    noise_chk: str
    bolt_chk: str


class SwitchgearConsequenceAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    scale_dam_chk: float
    sup_sys_chk: str
    prod_chk: str
    op_chk: str
    replace_chk: float
    recovery_time_chk: float
    replace_time_chk: int


class SwitchgearDesignAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    reliability: str
    ato: str
    cb_inspect: str
    relay_chk: str
    online_diag: str
    part_shortage: str


class SwitchgearScoreDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    computed_at: datetime
    today: date
    operation_year: float
    age_minus: int
    cb_op_year: float
    cb_stat: float
    cb_stat_minus: int
    durability_minus: int
    part_thermal_chk_minus: int
    elec_room_avg_temp_minus: int
    temp_diff_chk_minus: int
    max_temp_chk_minus: int
    load_minus: int
    thermal_minus: int
    ex_box_chk_minus: int
    noise_chk_minus: int
    bolt_chk_minus: int
    phy_minus: int
    scale_dam_chk_minus: int
    install_building_minus: int
    sup_sys_chk_minus: int
    cof_sys_minus: int
    prod_chk_minus: int
    op_chk_minus: int
    replace_chk_minus: int
    cof_cost_minus: int
    recovery_time_chk_minus: int
    replace_time_chk_minus: int
    cof_recov_minus: int
    operation_start_year: int
    reliability_minus: int
    ato_minus: int
    dof_sys_minus: int
    cb_inspect_minus: int
    relay_chk_minus: int
    online_diag_minus: int
    dof_cost_minus: int
    part_shortage_minus: int
    ct_use: str
    ct_use_minus: int
    longlife_fan_use: str
    lighting_use: str
    spec_use_minus: int
    dof_recov_minus: int


class Ef4Detail(BaseModel):
    """EF4 유형 전용 상세 — EquipmentDetail.type_detail에 ef_code로 구분되어 들어간다."""

    ef_code: Literal["EF4"] = "EF4"
    spec: SwitchgearSpecOut
    condition: SwitchgearConditionOut
    consequence: SwitchgearConsequenceAttributeOut
    design: SwitchgearDesignAttributeOut
    score_detail: SwitchgearScoreDetailOut
