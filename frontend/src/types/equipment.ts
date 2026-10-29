export type EquipmentStatus = "normal" | "review" | "replace";

export interface EquipmentSummary {
  equipment_id: number;
  factory_code: string;
  ef_code: string;
  equipment_name: string;
  voltage: number;
  operation_start_time: string;
  pof: number;
  cof: number;
  dof: number;
  total_score: number;
  status: EquipmentStatus;
  last_diag_date: string | null;
}

export interface TypeKPI {
  ef_code: string;
  ef_name: string;
  total_equipment: number;
  review_count: number;
  replace_count: number;
}

export interface SummaryKPI {
  total_equipment: number;
  review_count: number;
  replace_count: number;
  last_updated: string | null;
  by_type: TypeKPI[];
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

/** EF1(변압기) 전용 상세 — EquipmentDetail.type_detail (Stage 8-4) */
export interface Ef1TypeDetail {
  ef_code: "EF1";
  spec: { updated_at: string; onan_val: number; onaf_val: number };
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
  score_detail: ScoreDetail;
}

/** EF2(GIS) 전용 상세 — EquipmentDetail.type_detail (Stage 8-5). 필드는 backend app/schemas/ef2.py와 1:1 */
export interface Ef2ScoreDetail {
  computed_at: string;
  today: string;
  operation_year: number;
  age_minus: number;
  cb_op_num_minus: number;
  cb_op_year: number;
  cb_stat: number;
  cb_stat_minus: number;
  insul_year: number;
  insul_stat: number;
  insul_stat_minus: number;
  gis_mech_minus: number;
  rated_trip_count_minus: number;
  cum_trip_current_minus: number;
  load_minus: number;
  leakage_curr_minus: number;
  gis_elec_minus: number;
  part_dischar_minus: number;
  sf6_minus: number;
  elec_room_minus: number;
  gis_chem_minus: number;
  in_vol_minus: number;
  productivity_minus: number;
  fire_spread_minus: number;
  env_minus: number;
  emerge_resp_minus: number;
  rep_cost_minus: number;
  rep_time_minus: number;
  in_line_minus: number;
  ato_minus: number;
  reliability_minus: number;
  online_diag_minus: number;
  offline_diag_minus: number;
  tbm_minus: number;
  conn_rev_minus: number;
  leak_str_minus: number;
  insul_str_minus: number;
  vt_la_minus: number;
}

export interface Ef2TypeDetail {
  ef_code: "EF2";
  operation: {
    measured_at: string;
    op_type: string;
    cb_op_num: number;
    rated_trip_count: number;
    cum_trip_current: number;
    load_percent: number;
    leakage_curr: number;
  };
  diagnosis: {
    measured_at: string;
    part_dischar_pat: string;
    elec_room_max_temp: number;
  };
  sf6: {
    diag_time: string;
    sf6_so2: number;
    sf6_leak: string;
    sf6_h2o: number;
    sf6_purity: number;
  };
  consequence: {
    updated_at: string;
    in_vol: string;
    capa_times_load: string;
    fire_spread: string;
    env_loc: string;
    emerge_resp_pat: string;
    rep_cost: string;
    rep_time: string;
  };
  design: {
    updated_at: string;
    in_line_num: string;
    ato: string;
    reliability: string;
    online_diag: string;
    offline_diag: string;
    tbm: string;
    conn_rev: string;
    leak_str: string;
    insul_str: string;
    vt_la_str: string;
  };
  score_detail: Ef2ScoreDetail;
}

/** EF3(초고압케이블) 전용 상세 — EquipmentDetail.type_detail (Stage 9-4). 필드는 backend app/schemas/ef3.py와 1:1 */
export interface Ef3ScoreDetail {
  computed_at: string;
  today: string;
  operation_year: number;
  age_minus: number;
  load_percent: number;
  load_minus: number;
  temp_minus: number;
  diff_temp_minus: number;
  failure_rate_minus: number;
  pd_minus: number;
  sys_cycle_curr_minus: number;
  svl_leak_curr_minus: number;
  joint_ex_damage_minus: number;
  cable_move_minus: number;
  risk_mva: number;
  risk_mva_minus: number;
  laying_type_minus: number;
  mid_joint_minus: number;
  end_joint_minus: number;
  emerge_resp_minus: number;
  rep_cost: number;
  rep_cost_minus: number;
  rep_time_minus: number;
  reliability_minus: number;
  temp_diag_minus: number;
  pd_diag_minus: number;
  live_line_diag_minus: number;
  cable_move_diag_minus: number;
  offline_diag_minus: number;
  longlife_insul_minus: number;
}

export interface Ef3TypeDetail {
  ef_code: "EF3";
  spec: {
    updated_at: string;
    cable_sq: number;
    cable_per_phase: number;
    cable_mva: number;
    cable_length: number;
    laying_type: string;
    mid_joint: number;
    end_joint: string;
  };
  condition: {
    measured_at: string;
    max_load: number;
    max_temp: number;
    diff_temp: number;
    failure_rate: number;
    pd_num: number;
    sys_cycle_curr: number;
    svl_leak_curr: number;
    joint_ex_damage: string;
    cable_move: number;
  };
  consequence: {
    updated_at: string;
    emerge_resp: string;
    rep_time: string;
  };
  design: {
    updated_at: string;
    reliability: number;
    temp_diag: string;
    pd_diag: string;
    live_line_diag: string;
    cable_move_diag: string;
    offline_diag: string;
    longlife_insul: string;
  };
  score_detail: Ef3ScoreDetail;
}

export type TypeDetail = Ef1TypeDetail | Ef2TypeDetail | Ef3TypeDetail;

export interface ProjectionPoint {
  years_ahead: number;
  as_of: string;
  pof: number;
  cof: number;
  dof: number;
  total_score: number;
}

export interface EquipmentDetail {
  equipment_id: number;
  factory_code: string;
  ef_code: string;
  ef_name: string;
  equipment_name: string;
  voltage: number;
  operation_start_time: string;
  status: EquipmentStatus;
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
  type_detail: TypeDetail;
  projection: ProjectionPoint[];
}

/** /api/equipment-types — 설비유형과 감점 항목 메타데이터(화면 라벨의 단일 원본, Stage 8-5) */
export interface BreakdownItem {
  field: string;
  label: string;
  group: string | null;
  summed: boolean;
}

export type Axis = "pof" | "cof" | "dof";

export interface EquipmentTypeInfo {
  ef_code: string;
  ef_name: string;
  equipment_count: number;
  breakdown: Record<Axis, BreakdownItem[]>;
}
