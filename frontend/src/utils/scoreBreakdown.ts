import type { EquipmentDetail, ScoreDetail } from "../types/equipment";

export const POF_FIELD_LABELS: Partial<Record<keyof ScoreDetail, string>> = {
  age_minus: "경과연수",
  dga_minus: "DGA(유중가스)",
  load_minus: "부하율",
  temp_minus: "운전온도",
  dielec_str_te_minus: "절연내력시험",
  acid_measure_minus: "산가도시험",
  moisture_minus: "수분시험",
  furan_minus: "Furan",
  part_discharge_minus: "부분방전",
  oltc_96t_minus: "OLTC 96T 동작",
  oltc_minus: "OLTC 동작진단",
  thermal_img_minus: "열화상",
  noise_minus: "이상소음",
};

export const COF_FIELD_LABELS: Partial<Record<keyof ScoreDetail, string>> = {
  first_voltage_minus: "1차전압",
  productivity_minus: "생산성 영향(용량×부하율)",
  fire_minus: "화재취약성",
  fire_spread_minus: "화재확산장소",
  emerge_response_minus: "비상대응시간",
  rep_cost_minus: "교체비용",
  rep_time_minus: "교체기간",
};

export const DOF_FIELD_LABELS: Partial<Record<keyof ScoreDetail, string>> = {
  redundancy_minus: "예비화",
  ato_minus: "계통자동전환",
  online_og_minus: "온라인 유중가스",
  offline_safety_minus: "안전공사 정밀점검",
  sec_minus: "보호요소",
  alarm_minus: "알람요소",
  winding_minus: "권선(절연 1단계 상승)",
  prod_life_minus: "수명향상(고밀도 절연지)",
  connect_part_minus: "접속부(이중절연)",
  temp_inc_limit_minus: "온도상승한도",
  test_reliability_minus: "SFRA 시험",
  bushing_minus: "부싱",
  oltc2_minus: "OLTC(진공식)",
};

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

function collectReasons(detail: ScoreDetail, fields: Partial<Record<keyof ScoreDetail, string>>): ScoreReason[] {
  const reasons: ScoreReason[] = [];
  for (const [field, label] of Object.entries(fields)) {
    const value = detail[field as keyof ScoreDetail] as number;
    if (typeof value === "number" && value < 0) {
      reasons.push({ field, label, value });
    }
  }
  return reasons.sort((a, b) => a.value - b.value);
}

/** PoF/CoF/DoF 축별로 감점 사유 전부(0인 항목 제외)를 감점 큰 순으로 반환한다. */
export function getReasonsByAxis(detail: ScoreDetail): ReasonsByAxis {
  return {
    pof: collectReasons(detail, POF_FIELD_LABELS),
    cof: collectReasons(detail, COF_FIELD_LABELS),
    dof: collectReasons(detail, DOF_FIELD_LABELS),
  };
}

// 감점 항목별로 "왜 감점됐는지" 실제 근거(원본 측정값/판정)를 한 줄로 보여준다(hover 툴팁용).
const EVIDENCE: Record<string, (d: EquipmentDetail) => string> = {
  age_minus: (d) => `경과연수 ${d.score_detail.operation_year}년차`,
  dga_minus: (d) => `TCG ${d.score_detail.dga_tcg}ppm · 판정 ${d.score_detail.dga_diag}`,
  load_minus: (d) => `부하율 ${d.load.load_percent}%`,
  temp_minus: (d) => `권선 최고온도 ${d.load.coil_max_temp}℃`,
  dielec_str_te_minus: (d) => `절연내력 평균 ${d.score_detail.dielec_str_te_avg}kV · 판정 ${d.score_detail.dielec_str_te_diag}`,
  acid_measure_minus: (d) => `산가도 판정 ${d.score_detail.acid_measure_desc}`,
  moisture_minus: (d) => `수분 판정 ${d.score_detail.moisture_desc}`,
  furan_minus: (d) => `Furan 총량 ${d.score_detail.furan_total}(연 ${d.score_detail.furan_total_per_year.toFixed(1)}) · 판정 ${d.score_detail.furan_desc}`,
  part_discharge_minus: (d) => `부분방전 판정 ${d.inspection.part_discharge_diag}`,
  oltc_96t_minus: (d) => `OLTC 96T 판정 ${d.inspection.oltc_96t_diag}`,
  oltc_minus: (d) => `OLTC 동작 판정 ${d.score_detail.oltc_diag} (${d.inspection.oltc_type})`,
  thermal_img_minus: (d) => `열화상 온도 ${d.inspection.thermal_img_temp}`,
  noise_minus: (d) => `이상소음 판정 ${d.inspection.noise_diag}`,

  first_voltage_minus: (d) => `1차전압 ${d.score_detail.first_voltage.toLocaleString()}V`,
  productivity_minus: (d) => `용량×부하율 지수 ${d.score_detail.capa_times_load}`,
  fire_minus: (d) => `화재취약 유형 ${d.design.fire_vul_type}`,
  fire_spread_minus: (d) => `화재확산 장소 ${d.design.fire_spread_loc}`,
  emerge_response_minus: (d) => `비상대응 1단계 조치 ${d.design.emerge_response_1s}`,
  rep_cost_minus: (d) => `교체비용 지수 ${d.score_detail.rep_cost}`,
  rep_time_minus: (d) => `교체기간 ${d.score_detail.rep_time}개월`,

  redundancy_minus: (d) => `예비화 ${d.design.redundancy}`,
  ato_minus: (d) => `계통자동전환 ${d.design.ato}`,
  online_og_minus: (d) => `온라인 유중가스 ${d.design.online_og_chk}`,
  offline_safety_minus: (d) => `안전공사 정밀점검 ${d.design.offline_safety_chk}`,
  sec_minus: (d) => `보호요소 ${d.design.sec_num}개`,
  alarm_minus: (d) => `알람요소 ${d.design.alarm_num}개`,
  winding_minus: (d) => `권선 절연단계 ${d.design.insul_1st_lvup}`,
  prod_life_minus: (d) => `고밀도 절연지 적용 ${d.design.high_insul_adt}`,
  connect_part_minus: (d) => `이중절연 접속부 ${d.design.double_insul}`,
  temp_inc_limit_minus: (d) => `온도상승한도 55K 적용 ${d.design.install_55k}`,
  test_reliability_minus: (d) => `SFRA 시험 ${d.design.sfra_test}`,
  bushing_minus: (d) => `부싱(RIP) 적용 ${d.design.rip_install}`,
  oltc2_minus: (d) => `OLTC(진공식) 적용 ${d.design.vacuum_set}`,
};

/** 감점 항목 하나의 근거(원본 측정값/판정)를 한 줄 텍스트로 반환한다. 매핑이 없으면 빈 문자열. */
export function getEvidence(field: string, detail: EquipmentDetail): string {
  return EVIDENCE[field]?.(detail) ?? "";
}
