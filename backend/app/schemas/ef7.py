"""EF7(배터리) 상세 응답 스키마 (Stage 15-1). 필드는 app/db/models/battery.py 컬럼과 1:1."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class BatterySpecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    line_no: str | None
    manufacturer: str | None
    model_name: str | None
    capa: float | None


class BatteryConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    vol_diff: float | None
    temp_diff: float | None
    temp_range_over: float | None
    bat_room_temp: float | None
    bat_room_humid: float | None
    load: float | None


class BatteryConsequenceAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    con_rank: str | None
    ins_build_rank: str | None
    fire_spread_rank: str | None
    emerge_resp: str | None
    rep_time: str | None
    rep_cost: str | None


class BatteryDesignAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    model_gen: int | None
    fire_resist: str | None
    ul_auth: str | None
    fac_rel: int | None
    part_stat_diag: str | None
    bat_server: str | None
    bat_room_fire_resist: str | None


class BatteryScoreDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    computed_at: datetime
    today: date
    operation_year: float
    age_minus: float
    disch_index: float
    disch_dec_coef: float
    temp_dec_coef: float | None
    soh_minus: float
    bms_life: float
    bms_stat: float | None
    bms_minus: float
    vol_diff_minus: float
    temp_diff_minus: float
    temp_range_over_minus: float
    bat_room_temp_minus: float
    bat_room_humid_minus: float
    capa_times_load: float | None
    capa_times_load_minus: float
    con_rank_minus: float
    ins_build_rank_minus: float
    fire_spread_rank_minus: float
    emerge_resp_minus: float
    rep_time_minus: float
    rep_cost_minus: float
    model_gen_minus: float
    fire_resist_minus: float
    ul_auth_minus: float
    fac_rel_minus: float
    part_stat_diag_minus: float
    bat_server_minus: float
    bat_room_fire_resist_minus: float


class Ef7Detail(BaseModel):
    """EF7 유형 전용 상세 — EquipmentDetail.type_detail에 ef_code로 구분되어 들어간다."""

    ef_code: Literal["EF7"] = "EF7"
    spec: BatterySpecOut
    condition: BatteryConditionOut
    consequence: BatteryConsequenceAttributeOut
    design: BatteryDesignAttributeOut
    score_detail: BatteryScoreDetailOut
