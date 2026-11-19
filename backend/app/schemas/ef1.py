"""EF1(변압기) 상세 응답 스키마 — Stage 8-4에 app/schemas/equipment.py에서 분리(필드 무변경)."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TransformerSpecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    onan_val: int | None
    onaf_val: float | None


class DgaReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    diag_time: date | None
    dga_h2: int | None
    dga_c2h2: float | None
    dga_c2h4: int | None
    dga_c2h6: int | None
    dga_ch4: int | None
    dga_c3h8: int | None
    dga_co: int | None
    dga_co2: int | None
    dga_o2: int | None
    dga_n2: int | None
    dga_fluc: int | None


class FuranReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    diag_time: date | None
    furan_5h2f: int | None
    furan_2fol: float | None
    furan_2fal: int | None
    furan_2acf: int | None
    furan_5m2f: int | None


class DielectricTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    dielec_str_te_1: float | None
    dielec_str_te_2: float | None
    dielec_str_te_3: float | None
    dielec_str_te_4: float | None
    dielec_str_te_5: float | None
    dielec_str_te_6: float | None


class OilTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    acid_measure_val: float | None
    moisture_rslt: float | None


class LoadConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    load_percent: float | None
    coil_max_temp: int | None


class PeriodicInspectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    part_discharge_diag: str | None
    oltc_96t_diag: str | None
    oltc_rslt: int | None
    oltc_type: str | None
    thermal_img_temp: str | None
    noise_diag: str | None


class DesignAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    fire_vul_type: str | None
    fire_spread_loc: str | None
    emerge_response_1s: str | None
    redundancy: str | None
    ato: str | None
    online_og_chk: str | None
    offline_safety_chk: str | None
    sec_num: int | None
    alarm_num: int | None
    insul_1st_lvup: str | None
    high_insul_adt: str | None
    double_insul: str | None
    install_55k: str | None
    sfra_test: str | None
    rip_install: str | None
    vacuum_set: str | None


class TransformerScoreDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    computed_at: datetime
    today: date
    operation_year: float
    age_minus: float
    dga_tcg: float | None
    dga_diag: str | None
    dga_minus: float
    load_minus: float
    temp_minus: float
    dielec_str_te_avg: float | None
    dielec_str_te_diag: str | None
    dielec_str_te_minus: float
    acid_measure_desc: str | None
    acid_measure_minus: float
    moisture_desc: str | None
    moisture_minus: float
    furan_total: float | None
    furan_diag_year: float | None = None  # Furan 진단 시점 사용년수 — 진단일 ≤ 가동년월이면 null(평가 불가)
    furan_total_per_year: float | None
    furan_desc: str | None
    furan_minus: float
    part_discharge_minus: float
    oltc_96t_minus: float
    oltc_diag: str | None
    oltc_minus: float
    thermal_img_minus: float
    noise_minus: float
    first_voltage: int
    first_voltage_minus: float
    capa_times_load: float | None
    productivity_minus: float
    fire_minus: float
    fire_spread_minus: float
    emerge_response_minus: float
    rep_cost: float
    rep_cost_minus: float
    rep_time: int
    rep_time_minus: float
    redundancy_minus: float
    ato_minus: float
    online_og_minus: float
    offline_safety_minus: float
    sec_minus: float
    alarm_minus: float
    winding_minus: float
    prod_life_minus: float
    connect_part_minus: float
    temp_inc_limit_minus: float
    test_reliability_minus: float
    bushing_minus: float
    oltc2_minus: float


class Ef1Detail(BaseModel):
    """EF1 유형 전용 상세 — EquipmentDetail.type_detail에 ef_code로 구분되어 들어간다."""

    ef_code: Literal["EF1"] = "EF1"
    spec: TransformerSpecOut
    dga: DgaReadingOut
    furan: FuranReadingOut
    dielectric: DielectricTestOut
    oil: OilTestOut
    load: LoadConditionOut
    inspection: PeriodicInspectionOut
    design: DesignAttributeOut
    score_detail: TransformerScoreDetailOut
