import type { ScoreDetail } from "../types/equipment";

const POF_FIELD_LABELS: Partial<Record<keyof ScoreDetail, string>> = {
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

const COF_FIELD_LABELS: Partial<Record<keyof ScoreDetail, string>> = {
  first_voltage_minus: "1차전압",
  productivity_minus: "생산성 영향(용량×부하율)",
  fire_minus: "화재취약성",
  fire_spread_minus: "화재확산장소",
  emerge_response_minus: "비상대응시간",
  rep_cost_minus: "교체비용",
  rep_time_minus: "교체기간",
};

const DOF_FIELD_LABELS: Partial<Record<keyof ScoreDetail, string>> = {
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
      reasons.push({ label, value });
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
