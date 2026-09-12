export interface EquipmentSummary {
  equipment_id: number;
  factory_code: string;
  ef_code: string;
  transformer_name: string;
  voltage: number;
  pof: number;
  cof: number;
  dof: number;
  total_score: number;
  needs_inspection: boolean;
  last_diag_date: string | null;
}

export interface SummaryKPI {
  total_equipment: number;
  needs_inspection_count: number;
  last_updated: string | null;
}

export interface ScoreDetail {
  today: string;
  operation_year: number;
  age_minus: number;
  dga_tcg: number;
  dga_diag: string;
  dga_minus: number;
  load_minus: number;
  temp_minus: number;
  dielec_str_te_avg: number;
  dielec_str_te_diag: string;
  dielec_str_te_minus: number;
  acid_measure_desc: string;
  acid_measure_minus: number;
  moisture_desc: string;
  moisture_minus: number;
  furan_total: number;
  furan_total_per_year: number;
  furan_desc: string;
  furan_minus: number;
  part_discharge_minus: number;
  oltc_96t_minus: number;
  oltc_diag: string;
  oltc_minus: number;
  thermal_img_minus: number;
  noise_minus: number;
  first_voltage: number;
  first_voltage_minus: number;
  capa_times_load: number;
  productivity_minus: number;
  fire_minus: number;
  fire_spread_minus: number;
  emerge_response_minus: number;
  rep_cost: number;
  rep_cost_minus: number;
  rep_time: number;
  rep_time_minus: number;
  redundancy_minus: number;
  ato_minus: number;
  online_og_minus: number;
  offline_safety_minus: number;
  sec_minus: number;
  alarm_minus: number;
  winding_minus: number;
  prod_life_minus: number;
  connect_part_minus: number;
  temp_inc_limit_minus: number;
  test_reliability_minus: number;
  bushing_minus: number;
  oltc2_minus: number;
}

export interface EquipmentDetail {
  equipment_id: number;
  factory_code: string;
  ef_code: string;
  transformer_name: string;
  voltage: number;
  onan_val: number;
  onaf_val: number;
  operation_start_time: string;
  needs_inspection: boolean;
  dga: {
    diag_time: string;
    dga_h2: number;
    dga_c2h2: number;
    dga_c2h4: number;
    dga_c2h6: number;
    dga_ch4: number;
    dga_c3h8: number;
    dga_co: number;
    dga_co2: number;
    dga_o2: number;
    dga_n2: number;
    dga_fluc: number;
  };
  furan: {
    diag_time: string;
    furan_5h2f: number;
    furan_2fol: number;
    furan_2fal: number;
    furan_2acf: number;
    furan_5m2f: number;
  };
  dielectric: {
    measured_at: string;
    dielec_str_te_1: number;
    dielec_str_te_2: number;
    dielec_str_te_3: number;
    dielec_str_te_4: number;
    dielec_str_te_5: number;
    dielec_str_te_6: number;
  };
  oil: { measured_at: string; acid_measure_val: number; moisture_rslt: number };
  load: { measured_at: string; load_percent: number; coil_max_temp: number };
  inspection: {
    measured_at: string;
    part_discharge_diag: string;
    oltc_96t_diag: string;
    oltc_rslt: number;
    oltc_type: string;
    thermal_img_temp: string;
    noise_diag: string;
  };
  design: {
    updated_at: string;
    fire_vul_type: string;
    fire_spread_loc: string;
    emerge_response_1s: string;
    redundancy: string;
    ato: string;
    online_og_chk: string;
    offline_safety_chk: string;
    sec_num: number;
    alarm_num: number;
    insul_1st_lvup: string;
    high_insul_adt: string;
    double_insul: string;
    install_55k: string;
    sfra_test: string;
    rip_install: string;
    vacuum_set: string;
  };
  score: {
    pof_minus: number;
    pof: number;
    cof_minus: number;
    cof: number;
    dof_minus: number;
    dof: number;
    total_score: number;
    computed_at: string;
  };
  score_detail: ScoreDetail;
}
