"""EF5(UPS) 상세 응답 스키마 (Stage 13-1). 필드는 app/db/models/ups.py 컬럼과 1:1."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class UpsSpecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    line_no: str | None
    manufacturer: str | None
    model_name: str | None
    capa: int | None


class UpsConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    fan_replace_no: int | None
    elec_room_max_temp: float | None
    load: float | None
    mod_cir_curr: int | None
    mod_vol_diff: int | None
    noise: int | None
    thermal_img_chk: str | None
    ex_box_chk: str | None


class UpsConsequenceAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    ins_build_rank: str | None
    fire_spread_rank: str | None
    emerge_resp: str | None
    rep_time: str | None
    rep_cost: str | None


class UpsDesignAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    sys_rel: str | None
    emerge_sys: str | None
    fac_rel: str | None
    part_shortage: str | None
    model_type: str | None
    switching_type: str | None
    igbt_rev: str | None
    online_diag: str | None


class UpsScoreDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    computed_at: datetime
    today: date
    operation_year: float
    age_minus: float
    cb_replace_no: int
    cb_life_year: float
    cb_stat: float | None
    cb_stat_minus: float
    cap_life_year: float
    cap_stat: float | None
    cap_stat_minus: float
    fan_life_year: float | None
    fan_stat: float | None
    fan_stat_minus: float
    igbt_life_year: float
    igbt_stat: float | None
    igbt_stat_minus: float
    board_life_year: float
    board_stat: float | None
    board_stat_minus: float
    elec_room_max_temp_minus: float
    load_minus: float
    mod_cir_curr_minus: float
    mod_vol_diff_minus: float
    noise_minus: float
    thermal_img_chk_minus: float
    ex_box_chk_minus: float
    capa_times_load: float | None
    capa_times_load_minus: float
    ins_build_rank_minus: float
    fire_spread_rank_minus: float
    emerge_resp_minus: float
    rep_time_minus: float
    rep_cost_minus: float
    sys_rel_minus: float
    emerge_sys_minus: float
    fac_rel_minus: float
    part_shortage_minus: float
    model_type_minus: float
    switching_type_minus: float
    igbt_rev_minus: float
    online_diag_minus: float


class Ef5Detail(BaseModel):
    """EF5 유형 전용 상세 — EquipmentDetail.type_detail에 ef_code로 구분되어 들어간다."""

    ef_code: Literal["EF5"] = "EF5"
    spec: UpsSpecOut
    condition: UpsConditionOut
    consequence: UpsConsequenceAttributeOut
    design: UpsDesignAttributeOut
    score_detail: UpsScoreDetailOut
