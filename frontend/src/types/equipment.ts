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
  dga_tcg: number | null;
  dga_diag: string | null;
  dga_minus: number;
  load_minus: number;
  temp_minus: number;
  dielec_str_te_avg: number | null;
  dielec_str_te_diag: string | null;
  dielec_str_te_minus: number;
  acid_measure_desc: string | null;
  acid_measure_minus: number;
  moisture_desc: string | null;
  moisture_minus: number;
  furan_total: number | null;
  furan_total_per_year: number | null;
  furan_desc: string | null;
  furan_minus: number;
  part_discharge_minus: number;
  oltc_96t_minus: number;
  oltc_diag: string | null;
  oltc_minus: number;
  thermal_img_minus: number;
  noise_minus: number;
  first_voltage: number;
  first_voltage_minus: number;
  capa_times_load: number | null;
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
  spec: { updated_at: string; onan_val: number | null; onaf_val: number | null };
  dga: {
    diag_time: string | null;
    dga_h2: number | null;
    dga_c2h2: number | null;
    dga_c2h4: number | null;
    dga_c2h6: number | null;
    dga_ch4: number | null;
    dga_c3h8: number | null;
    dga_co: number | null;
    dga_co2: number | null;
    dga_o2: number | null;
    dga_n2: number | null;
    dga_fluc: number | null;
  };
  furan: {
    diag_time: string | null;
    furan_5h2f: number | null;
    furan_2fol: number | null;
    furan_2fal: number | null;
    furan_2acf: number | null;
    furan_5m2f: number | null;
  };
  dielectric: {
    measured_at: string;
    dielec_str_te_1: number | null;
    dielec_str_te_2: number | null;
    dielec_str_te_3: number | null;
    dielec_str_te_4: number | null;
    dielec_str_te_5: number | null;
    dielec_str_te_6: number | null;
  };
  oil: { measured_at: string; acid_measure_val: number | null; moisture_rslt: number | null };
  load: { measured_at: string; load_percent: number | null; coil_max_temp: number | null };
  inspection: {
    measured_at: string;
    part_discharge_diag: string | null;
    oltc_96t_diag: string | null;
    oltc_rslt: number | null;
    oltc_type: string | null;
    thermal_img_temp: string | null;
    noise_diag: string | null;
  };
  design: {
    updated_at: string;
    fire_vul_type: string | null;
    fire_spread_loc: string | null;
    emerge_response_1s: string | null;
    redundancy: string | null;
    ato: string | null;
    online_og_chk: string | null;
    offline_safety_chk: string | null;
    sec_num: number | null;
    alarm_num: number | null;
    insul_1st_lvup: string | null;
    high_insul_adt: string | null;
    double_insul: string | null;
    install_55k: string | null;
    sfra_test: string | null;
    rip_install: string | null;
    vacuum_set: string | null;
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
    op_type: string | null;
    cb_op_num: number | null;
    rated_trip_count: number | null;
    cum_trip_current: number | null;
    load_percent: number | null;
    leakage_curr: number | null;
  };
  diagnosis: {
    measured_at: string;
    part_dischar_pat: string | null;
    elec_room_max_temp: number | null;
  };
  sf6: {
    diag_time: string | null;
    sf6_so2: number | null;
    sf6_leak: string | null;
    sf6_h2o: number | null;
    sf6_purity: number | null;
  };
  consequence: {
    updated_at: string;
    in_vol: string | null;
    capa_times_load: string | null;
    fire_spread: string | null;
    env_loc: string | null;
    emerge_resp_pat: string | null;
    rep_cost: string | null;
    rep_time: string | null;
  };
  design: {
    updated_at: string;
    in_line_num: string | null;
    ato: string | null;
    reliability: string | null;
    online_diag: string | null;
    offline_diag: string | null;
    tbm: string | null;
    conn_rev: string | null;
    leak_str: string | null;
    insul_str: string | null;
    vt_la_str: string | null;
  };
  score_detail: Ef2ScoreDetail;
}

/** EF3(초고압케이블) 전용 상세 — EquipmentDetail.type_detail (Stage 9-4). 필드는 backend app/schemas/ef3.py와 1:1 */
export interface Ef3ScoreDetail {
  computed_at: string;
  today: string;
  operation_year: number;
  age_minus: number;
  load_percent: number | null;
  load_minus: number;
  temp_minus: number;
  diff_temp_minus: number;
  failure_rate_minus: number;
  pd_minus: number;
  sys_cycle_curr_minus: number;
  svl_leak_curr_minus: number;
  joint_ex_damage_minus: number;
  cable_move_minus: number;
  risk_mva: number | null;
  risk_mva_minus: number;
  laying_type_minus: number;
  mid_joint_minus: number;
  end_joint_minus: number;
  emerge_resp_minus: number;
  rep_cost: number | null;
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
    cable_sq: number | null;
    cable_per_phase: number | null;
    cable_mva: number | null;
    cable_length: number | null;
    laying_type: string | null;
    mid_joint: number | null;
    end_joint: string | null;
  };
  condition: {
    measured_at: string;
    max_load: number | null;
    max_temp: number | null;
    diff_temp: number | null;
    failure_rate: number | null;
    pd_num: number | null;
    sys_cycle_curr: number | null;
    svl_leak_curr: number | null;
    joint_ex_damage: string | null;
    cable_move: number | null;
  };
  consequence: {
    updated_at: string;
    emerge_resp: string | null;
    rep_time: string | null;
  };
  design: {
    updated_at: string;
    reliability: number | null;
    temp_diag: string | null;
    pd_diag: string | null;
    live_line_diag: string | null;
    cable_move_diag: string | null;
    offline_diag: string | null;
    longlife_insul: string | null;
  };
  score_detail: Ef3ScoreDetail;
}

/** EF4(수배전반) 전용 상세 — EquipmentDetail.type_detail (Stage 10-4). 필드는 backend app/schemas/ef4.py와 1:1 */
export interface Ef4ScoreDetail {
  computed_at: string;
  today: string;
  operation_year: number;
  age_minus: number;
  cb_op_year: number;
  cb_stat: number;
  cb_stat_minus: number;
  durability_minus: number;
  part_thermal_chk_minus: number;
  elec_room_avg_temp_minus: number;
  temp_diff_chk_minus: number;
  max_temp_chk_minus: number;
  load_minus: number;
  thermal_minus: number;
  ex_box_chk_minus: number;
  noise_chk_minus: number;
  bolt_chk_minus: number;
  phy_minus: number;
  scale_dam_chk_minus: number;
  install_building_minus: number;
  sup_sys_chk_minus: number;
  cof_sys_minus: number;
  prod_chk_minus: number;
  op_chk_minus: number;
  replace_chk_minus: number;
  cof_cost_minus: number;
  recovery_time_chk_minus: number;
  replace_time_chk_minus: number;
  cof_recov_minus: number;
  operation_start_year: number;
  reliability_minus: number;
  ato_minus: number;
  dof_sys_minus: number;
  cb_inspect_minus: number;
  relay_chk_minus: number;
  online_diag_minus: number;
  dof_cost_minus: number;
  part_shortage_minus: number;
  ct_use: string;
  ct_use_minus: number;
  longlife_fan_use: string;
  lighting_use: string;
  spec_use_minus: number;
  dof_recov_minus: number;
}

export interface Ef4TypeDetail {
  ef_code: "EF4";
  spec: {
    updated_at: string;
    eqp_id_name: string | null;
    eqp_building: string | null;
    eqp_disting: string | null;
    eqp_floor: string | null;
    install_building: string | null;
  };
  condition: {
    measured_at: string;
    part_thermal_chk: string | null;
    elec_room_avg_temp: number | null;
    temp_diff_chk: number | null;
    max_temp_chk: number | null;
    load_chk: number | null;
    ex_box_chk: string | null;
    noise_chk: string | null;
    bolt_chk: string | null;
  };
  consequence: {
    updated_at: string;
    scale_dam_chk: number | null;
    sup_sys_chk: string | null;
    prod_chk: string | null;
    op_chk: string | null;
    replace_chk: number | null;
    recovery_time_chk: number | null;
    replace_time_chk: number | null;
  };
  design: {
    updated_at: string;
    reliability: string | null;
    ato: string | null;
    cb_inspect: string | null;
    relay_chk: string | null;
    online_diag: string | null;
    part_shortage: string | null;
  };
  score_detail: Ef4ScoreDetail;
}

export type TypeDetail = Ef1TypeDetail | Ef2TypeDetail | Ef3TypeDetail | Ef4TypeDetail;

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
