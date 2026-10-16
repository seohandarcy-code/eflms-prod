"""EF2(GIS) 상세 응답 스키마 (Stage 8-4). 필드는 app/db/models/gis.py 컬럼과 1:1."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class GisOperationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    op_type: str
    cb_op_num: int
    rated_trip_count: int
    cum_trip_current: int
    cb_op_char_over: str
    load_percent: float
    leakage_curr: float


class GisDiagnosisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    part_dischar_pat: str
    elec_room_max_temp: int


class GisSf6ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    diag_time: date
    sf6_so2: float
    sf6_leak: str
    sf6_h2o: float
    sf6_purity: float


class GisConsequenceAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    in_vol: str
    capa_times_load: str
    fire_spread: str
    env_loc: str
    emerge_resp_pat: str
    rep_cost: str
    rep_time: str


class GisDesignAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    in_line_num: str
    ato: str
    reliability: str
    online_diag: str
    offline_diag: str
    tbm: str
    conn_rev: str
    leak_str: str
    insul_str: str
    vt_la_str: str


class GisScoreDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    computed_at: datetime
    today: date
    operation_year: float
    age_minus: int
    cb_op_num_minus: int
    cb_op_year: float
    cb_stat: float
    cb_stat_minus: int
    insul_year: float
    insul_stat: float
    insul_stat_minus: int
    gis_mech_minus: int
    rated_trip_count_minus: int
    cum_trip_current_minus: int
    cb_op_char_over_minus: int
    load_minus: int
    leakage_curr_minus: int
    gis_elec_minus: int
    part_dischar_minus: int
    sf6_minus: int
    elec_room_minus: int
    gis_chem_minus: int
    in_vol_minus: int
    productivity_minus: int
    fire_spread_minus: int
    env_minus: int
    emerge_resp_minus: int
    rep_cost_minus: int
    rep_time_minus: int
    in_line_minus: int
    ato_minus: int
    reliability_minus: int
    online_diag_minus: int
    offline_diag_minus: int
    tbm_minus: int
    conn_rev_minus: int
    leak_str_minus: int
    insul_str_minus: int
    vt_la_minus: int


class Ef2Detail(BaseModel):
    """EF2 유형 전용 상세 — EquipmentDetail.type_detail에 ef_code로 구분되어 들어간다."""

    ef_code: Literal["EF2"] = "EF2"
    operation: GisOperationOut
    diagnosis: GisDiagnosisOut
    sf6: GisSf6ReadingOut
    consequence: GisConsequenceAttributeOut
    design: GisDesignAttributeOut
    score_detail: GisScoreDetailOut
