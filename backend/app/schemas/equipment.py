from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class EquipmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_id: int
    factory_code: str
    ef_code: str
    transformer_name: str
    voltage: int
    pof: int
    cof: int
    dof: int
    total_score: float
    needs_inspection: bool
    last_diag_date: date | None = None


class DgaReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    diag_time: date
    dga_h2: int
    dga_c2h2: float
    dga_c2h4: int
    dga_c2h6: int
    dga_ch4: int
    dga_c3h8: int
    dga_co: int
    dga_co2: int
    dga_o2: int
    dga_n2: int
    dga_fluc: int


class FuranReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    diag_time: date
    furan_5h2f: int
    furan_2fol: float
    furan_2fal: int
    furan_2acf: int
    furan_5m2f: int


class DielectricTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    dielec_str_te_1: float
    dielec_str_te_2: float
    dielec_str_te_3: float
    dielec_str_te_4: float
    dielec_str_te_5: float
    dielec_str_te_6: float


class OilTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    acid_measure_val: float
    moisture_rslt: float


class LoadConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    load_percent: float
    coil_max_temp: int


class PeriodicInspectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    measured_at: date
    part_discharge_diag: str
    oltc_96t_diag: str
    oltc_rslt: int
    oltc_type: str
    thermal_img_temp: str
    noise_diag: str


class DesignAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    updated_at: date
    fire_vul_type: str
    fire_spread_loc: str
    emerge_response_1s: str
    redundancy: str
    ato: str
    online_og_chk: str
    offline_safety_chk: str
    sec_num: int
    alarm_num: int
    insul_1st_lvup: str
    high_insul_adt: str
    double_insul: str
    install_55k: str
    sfra_test: str
    rip_install: str
    vacuum_set: str


class ScoreSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    pof_minus: int
    pof: int
    cof_minus: int
    cof: int
    dof_minus: int
    dof: int
    total_score: float
    computed_at: datetime


class TransformerScoreDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    computed_at: datetime
    today: date
    operation_year: float
    age_minus: int
    dga_tcg: float
    dga_diag: str
    dga_minus: int
    load_minus: int
    temp_minus: int
    dielec_str_te_avg: float
    dielec_str_te_diag: str
    dielec_str_te_minus: int
    acid_measure_desc: str
    acid_measure_minus: int
    moisture_desc: str
    moisture_minus: int
    furan_total: float
    furan_total_per_year: float
    furan_desc: str
    furan_minus: int
    part_discharge_minus: int
    oltc_96t_minus: int
    oltc_diag: str
    oltc_minus: int
    thermal_img_minus: int
    noise_minus: int
    first_voltage: int
    first_voltage_minus: int
    capa_times_load: float
    productivity_minus: int
    fire_minus: int
    fire_spread_minus: int
    emerge_response_minus: int
    rep_cost: float
    rep_cost_minus: int
    rep_time: int
    rep_time_minus: int
    redundancy_minus: int
    ato_minus: int
    online_og_minus: int
    offline_safety_minus: int
    sec_minus: int
    alarm_minus: int
    winding_minus: int
    prod_life_minus: int
    connect_part_minus: int
    temp_inc_limit_minus: int
    test_reliability_minus: int
    bushing_minus: int
    oltc2_minus: int


class EquipmentDetail(BaseModel):
    equipment_id: int
    factory_code: str
    ef_code: str
    transformer_name: str
    voltage: int
    onan_val: int
    onaf_val: float
    operation_start_time: date
    needs_inspection: bool

    dga: DgaReadingOut
    furan: FuranReadingOut
    dielectric: DielectricTestOut
    oil: OilTestOut
    load: LoadConditionOut
    inspection: PeriodicInspectionOut
    design: DesignAttributeOut
    score: ScoreSnapshotOut
    score_detail: TransformerScoreDetailOut


class SummaryKPI(BaseModel):
    total_equipment: int
    needs_inspection_count: int
    last_updated: datetime | None = None
