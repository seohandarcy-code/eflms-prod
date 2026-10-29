import { na } from "./formatValue";
import type { Axis, BreakdownItem, Ef1TypeDetail, Ef2TypeDetail, Ef3TypeDetail, Ef4TypeDetail, EquipmentDetail } from "../types/equipment";

// 감점 항목 라벨은 백엔드 설비유형 모듈의 BREAKDOWN(/api/equipment-types)이 단일 원본이다(Stage 8-5).
// 예전처럼 여기에 유형별 라벨을 하드코딩하지 않는다.

export interface ScoreReason {
  field: string;
  label: string;
  value: number;
}

export interface ReasonsByAxis {
  pof: ScoreReason[];
  cof: ScoreReason[];
  dof: ScoreReason[];
}

const AXES: Axis[] = ["pof", "cof", "dof"];

/** PoF/CoF/DoF 축별로 감점 사유 전부(0인 항목 제외)를 감점 큰 순으로 반환한다. */
export function getReasonsByAxis(scoreDetail: object, breakdown: Record<Axis, BreakdownItem[]>): ReasonsByAxis {
  const values = scoreDetail as Record<string, unknown>;
  const result: ReasonsByAxis = { pof: [], cof: [], dof: [] };
  for (const axis of AXES) {
    for (const item of breakdown[axis] ?? []) {
      const value = values[item.field];
      if (typeof value === "number" && value < 0) {
        result[axis].push({ field: item.field, label: item.label, value });
      }
    }
    result[axis].sort((a, b) => a.value - b.value);
  }
  return result;
}

// 감점 항목별로 "왜 감점됐는지" 실제 근거(원본 측정값/판정)를 한 줄로 보여준다(hover 툴팁용).
const EF1_EVIDENCE: Record<string, (d: Ef1TypeDetail) => string> = {
  age_minus: (d) => `경과연수 ${na(d.score_detail.operation_year, { unit: "년차" })}`,
  dga_minus: (d) => `TCG ${na(d.score_detail.dga_tcg, { unit: "ppm" })} · 판정 ${na(d.score_detail.dga_diag)}`,
  load_minus: (d) => `부하율 ${na(d.load.load_percent, { unit: "%" })}`,
  temp_minus: (d) => `권선 최고온도 ${na(d.load.coil_max_temp, { unit: "℃" })}`,
  dielec_str_te_minus: (d) => `절연내력 평균 ${na(d.score_detail.dielec_str_te_avg, { unit: "kV" })} · 판정 ${na(d.score_detail.dielec_str_te_diag)}`,
  acid_measure_minus: (d) => `산가도 판정 ${na(d.score_detail.acid_measure_desc)}`,
  moisture_minus: (d) => `수분 판정 ${na(d.score_detail.moisture_desc)}`,
  furan_minus: (d) => `Furan 총량 ${na(d.score_detail.furan_total)}(연 ${na(d.score_detail.furan_total_per_year, { digits: 1 })}) · 판정 ${na(d.score_detail.furan_desc)}`,
  part_discharge_minus: (d) => `부분방전 판정 ${na(d.inspection.part_discharge_diag)}`,
  oltc_96t_minus: (d) => `OLTC 96T 판정 ${na(d.inspection.oltc_96t_diag)}`,
  oltc_minus: (d) => `OLTC 동작 판정 ${na(d.score_detail.oltc_diag)} (${na(d.inspection.oltc_type)})`,
  thermal_img_minus: (d) => `열화상 온도 ${na(d.inspection.thermal_img_temp)}`,
  noise_minus: (d) => `이상소음 판정 ${na(d.inspection.noise_diag)}`,

  first_voltage_minus: (d) => `1차전압 ${na(d.score_detail.first_voltage, { locale: true, unit: "V" })}`,
  productivity_minus: (d) => `용량×부하율 지수 ${na(d.score_detail.capa_times_load)}`,
  fire_minus: (d) => `화재취약 유형 ${na(d.design.fire_vul_type)}`,
  fire_spread_minus: (d) => `화재확산 장소 ${na(d.design.fire_spread_loc)}`,
  emerge_response_minus: (d) => `비상대응 1단계 조치 ${na(d.design.emerge_response_1s)}`,
  rep_cost_minus: (d) => `교체비용 지수 ${na(d.score_detail.rep_cost)}`,
  rep_time_minus: (d) => `교체기간 ${na(d.score_detail.rep_time, { unit: "개" })}월`,

  redundancy_minus: (d) => `예비화 ${na(d.design.redundancy)}`,
  ato_minus: (d) => `계통자동전환 ${na(d.design.ato)}`,
  online_og_minus: (d) => `온라인 유중가스 ${na(d.design.online_og_chk)}`,
  offline_safety_minus: (d) => `안전공사 정밀점검 ${na(d.design.offline_safety_chk)}`,
  sec_minus: (d) => `보호요소 ${na(d.design.sec_num, { unit: "개" })}`,
  alarm_minus: (d) => `알람요소 ${na(d.design.alarm_num, { unit: "개" })}`,
  winding_minus: (d) => `권선 절연단계 ${na(d.design.insul_1st_lvup)}`,
  prod_life_minus: (d) => `고밀도 절연지 적용 ${na(d.design.high_insul_adt)}`,
  connect_part_minus: (d) => `이중절연 접속부 ${na(d.design.double_insul)}`,
  temp_inc_limit_minus: (d) => `온도상승한도 55K 적용 ${na(d.design.install_55k)}`,
  test_reliability_minus: (d) => `SFRA 시험 ${na(d.design.sfra_test)}`,
  bushing_minus: (d) => `부싱(RIP) 적용 ${na(d.design.rip_install)}`,
  oltc2_minus: (d) => `OLTC(진공식) 적용 ${na(d.design.vacuum_set)}`,
};

const EF2_EVIDENCE: Record<string, (d: Ef2TypeDetail) => string> = {
  cb_op_num_minus: (d) => `차단기 동작횟수 ${na(d.operation.cb_op_num, { unit: "회" })}`,
  cb_stat_minus: (d) => `사용 ${na(d.score_detail.cb_op_year, { unit: "년" })} · 차단기 상태점수 ${na(d.score_detail.cb_stat, { digits: 3 })}`,
  insul_stat_minus: (d) => `사용 ${na(d.score_detail.insul_year, { unit: "년" })} · 절연물 상태점수 ${na(d.score_detail.insul_stat, { digits: 3 })}`,
  rated_trip_count_minus: (d) => `정격차단 동작 ${na(d.operation.rated_trip_count, { unit: "회" })}`,
  cum_trip_current_minus: (d) => `누적차단전류 ${na(d.operation.cum_trip_current)}`,
  load_minus: (d) => `부하율 ${na(d.operation.load_percent, { unit: "%" })}`,
  leakage_curr_minus: (d) => `누설전류 ${na(d.operation.leakage_curr)}`,
  age_minus: (d) => `경과연수 ${na(d.score_detail.operation_year, { unit: "년차" })}`,
  part_dischar_minus: (d) => `부분방전 이상패턴 ${na(d.diagnosis.part_dischar_pat)}`,
  sf6_minus: (d) => `SO2 ${na(d.sf6.sf6_so2)} · 누기 ${na(d.sf6.sf6_leak)} · 수분 ${na(d.sf6.sf6_h2o)} · 순도 ${na(d.sf6.sf6_purity, { unit: "%" })}`,
  elec_room_minus: (d) => `전기실 최대온도 ${na(d.diagnosis.elec_room_max_temp, { unit: "℃" })}`,

  in_vol_minus: (d) => `인입전압 등급 ${na(d.consequence.in_vol)}`,
  productivity_minus: (d) => `생산영향성 등급 ${na(d.consequence.capa_times_load)}`,
  fire_spread_minus: (d) => `화재확산 등급 ${na(d.consequence.fire_spread)}`,
  env_minus: (d) => `환경_위치 등급 ${na(d.consequence.env_loc)}`,
  emerge_resp_minus: (d) => `비상대응시간 등급 ${na(d.consequence.emerge_resp_pat)}`,
  rep_cost_minus: (d) => `사고복구비용 등급 ${na(d.consequence.rep_cost)}`,
  rep_time_minus: (d) => `정상화기간 등급 ${na(d.consequence.rep_time)}`,

  in_line_minus: (d) => `인입선로 등급 ${na(d.design.in_line_num)}`,
  ato_minus: (d) => `ATO 구성 ${na(d.design.ato)}`,
  reliability_minus: (d) => `공급신뢰도 등급 ${na(d.design.reliability)}`,
  online_diag_minus: (d) => `온라인진단 등급 ${na(d.design.online_diag)}`,
  offline_diag_minus: (d) => `오프라인진단 ${na(d.design.offline_diag)}`,
  tbm_minus: (d) => `TBM 실시 ${na(d.design.tbm)}`,
  conn_rev_minus: (d) => `도체접속구조개선 ${na(d.design.conn_rev)}`,
  leak_str_minus: (d) => `가스기밀강화 ${na(d.design.leak_str)}`,
  insul_str_minus: (d) => `절연스펙강화 ${na(d.design.insul_str)}`,
  vt_la_minus: (d) => `부품신뢰성강화 ${na(d.design.vt_la_str)}`,
};

const EF3_EVIDENCE: Record<string, (d: Ef3TypeDetail) => string> = {
  age_minus: (d) => `경과연수 ${na(d.score_detail.operation_year, { unit: "년차" })}`,
  load_minus: (d) => `부하율 ${na(d.score_detail.load_percent, { digits: 1, unit: "%" })} (최대부하 ${na(d.condition.max_load)} / 용량 ${na(d.spec.cable_mva)})`,
  temp_minus: (d) => `최고온도 ${na(d.condition.max_temp, { unit: "℃" })}`,
  diff_temp_minus: (d) => `상간온도차 ${na(d.condition.diff_temp, { unit: "℃" })}`,
  failure_rate_minus: (d) => `온도기반손상률 ${na(d.condition.failure_rate)}`,
  pd_minus: (d) => `부분방전 ${na(d.condition.pd_num, { unit: "회" })}`,
  sys_cycle_curr_minus: (d) => `시스순환전류 ${na(d.condition.sys_cycle_curr)}`,
  svl_leak_curr_minus: (d) => `SVL누설전류 ${na(d.condition.svl_leak_curr)}`,
  joint_ex_damage_minus: (d) => `접속함 외관 ${na(d.condition.joint_ex_damage)}`,
  cable_move_minus: (d) => `케이블이동량 ${na(d.condition.cable_move)}`,

  risk_mva_minus: (d) => `사고영향성용량 ${na(d.score_detail.risk_mva)}`,
  laying_type_minus: (d) => `포설방법 ${na(d.spec.laying_type)}`,
  mid_joint_minus: (d) => `중간접속함 ${na(d.spec.mid_joint, { unit: "개" })}`,
  end_joint_minus: (d) => `종단접속함 ${na(d.spec.end_joint)}`,
  emerge_resp_minus: (d) => `비상대응시간 ${na(d.consequence.emerge_resp)}`,
  rep_cost_minus: (d) => `사고복구교체비용 ${na(d.score_detail.rep_cost, { digits: 1 })} (길이 ${na(d.spec.cable_length, { locale: true })})`,
  rep_time_minus: (d) => `정상화기간 ${na(d.consequence.rep_time)}`,

  reliability_minus: (d) => `공급신뢰도 ${na(d.design.reliability, { unit: "회선" })}`,
  temp_diag_minus: (d) => `열화상진단 ${na(d.design.temp_diag)}`,
  pd_diag_minus: (d) => `PD진단 ${na(d.design.pd_diag)}`,
  live_line_diag_minus: (d) => `활선진단 ${na(d.design.live_line_diag)}`,
  cable_move_diag_minus: (d) => `이동량 측정 ${na(d.design.cable_move_diag)}`,
  offline_diag_minus: (d) => `오프라인진단 ${na(d.design.offline_diag)}`,
  longlife_insul_minus: (d) => `장수명절연물 ${na(d.design.longlife_insul)}`,
};

const EF4_EVIDENCE: Record<string, (d: Ef4TypeDetail) => string> = {
  age_minus: (d) => `경과년수 ${na(d.score_detail.operation_year, { unit: "년차" })}`,
  cb_stat_minus: (d) => `차단기상태점수 ${na(d.score_detail.cb_stat, { digits: 4 })} (사용 ${na(d.score_detail.cb_op_year, { unit: "년" })})`,
  part_thermal_chk_minus: (d) => `각종부품열화여부 ${na(d.condition.part_thermal_chk)}`,
  elec_room_avg_temp_minus: (d) => `전기실평균온도 ${na(d.condition.elec_room_avg_temp, { unit: "℃" })}`,
  temp_diff_chk_minus: (d) => `각상별온도편차 ${na(d.condition.temp_diff_chk, { unit: "℃" })}`,
  max_temp_chk_minus: (d) => `차단기CLIP최고온도 ${na(d.condition.max_temp_chk, { unit: "℃" })}`,
  load_minus: (d) => `부하율 ${na(d.condition.load_chk, { scale: 100, digits: 0, unit: "%" })}`,
  ex_box_chk_minus: (d) => `외함정상상태 ${na(d.condition.ex_box_chk)}`,
  noise_chk_minus: (d) => `차단기소음 ${na(d.condition.noise_chk)}`,
  bolt_chk_minus: (d) => `BOLT풀림 ${na(d.condition.bolt_chk)}`,

  scale_dam_chk_minus: (d) => `피해규모 ${na(d.consequence.scale_dam_chk)}`,
  install_building_minus: (d) => `설치건물 ${na(d.spec.install_building)}`,
  sup_sys_chk_minus: (d) => `공급계통 ${na(d.consequence.sup_sys_chk)}`,
  prod_chk_minus: (d) => `${na(d.consequence.prod_chk)} 설비`,
  op_chk_minus: (d) => `상시가동 ${na(d.consequence.op_chk)}`,
  replace_chk_minus: (d) => `교체비용 ${na(d.consequence.replace_chk)}`,
  recovery_time_chk_minus: (d) => `복구시부하정상동작시간 ${na(d.consequence.recovery_time_chk)}`,
  replace_time_chk_minus: (d) => `설비교체기간 ${na(d.consequence.replace_time_chk)}`,

  reliability_minus: (d) => `이중화 ${na(d.design.reliability)}`,
  ato_minus: (d) => `ATO ${na(d.design.ato)}`,
  cb_inspect_minus: (d) => `차단기정밀점검 ${na(d.design.cb_inspect)}`,
  relay_chk_minus: (d) => `계전기점검 ${na(d.design.relay_chk)}`,
  online_diag_minus: (d) => `온라인진단 ${na(d.design.online_diag)}`,
  part_shortage_minus: (d) => `부품 ${na(d.design.part_shortage)}`,
  ct_use_minus: (d) => `관통형CT ${na(d.score_detail.ct_use)} (${na(d.score_detail.operation_start_year, { unit: "년" })} 설치)`,
  spec_use_minus: (d) => `장수명FAN ${na(d.score_detail.longlife_fan_use)} · 조명등 ${na(d.score_detail.lighting_use)}`,
};

/** 감점 항목 하나의 근거(원본 측정값/판정)를 한 줄 텍스트로 반환한다. 매핑이 없으면 빈 문자열. */
export function getEvidence(field: string, detail: EquipmentDetail): string {
  const typeDetail = detail.type_detail;
  if (typeDetail.ef_code === "EF1") return EF1_EVIDENCE[field]?.(typeDetail) ?? "";
  if (typeDetail.ef_code === "EF2") return EF2_EVIDENCE[field]?.(typeDetail) ?? "";
  if (typeDetail.ef_code === "EF3") return EF3_EVIDENCE[field]?.(typeDetail) ?? "";
  if (typeDetail.ef_code === "EF4") return EF4_EVIDENCE[field]?.(typeDetail) ?? "";
  return "";
}
