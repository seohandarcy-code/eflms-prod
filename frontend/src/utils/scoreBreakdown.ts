import type { ScoreDetail } from "../types/equipment";

const MINUS_FIELD_LABELS: Partial<Record<keyof ScoreDetail, string>> = {
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
  first_voltage_minus: "1차전압",
  productivity_minus: "생산성 영향(용량×부하율)",
  fire_minus: "화재취약성",
  fire_spread_minus: "화재확산장소",
  emerge_response_minus: "비상대응시간",
  rep_cost_minus: "교체비용",
  rep_time_minus: "교체기간",
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

/** 감점 절댓값이 큰 순서(내림차순)로 상위 N개 사유를 반환한다. 0인 항목은 제외. */
export function getTopReasons(detail: ScoreDetail, limit = 3): ScoreReason[] {
  const reasons: ScoreReason[] = [];
  for (const [field, label] of Object.entries(MINUS_FIELD_LABELS)) {
    const value = detail[field as keyof ScoreDetail] as number;
    if (typeof value === "number" && value < 0) {
      reasons.push({ label, value });
    }
  }
  return reasons.sort((a, b) => a.value - b.value).slice(0, limit);
}

export interface ProjectedPoint {
  x: number;
  y: number;
}

const ORIGIN = { x: 280, y: 190 };
const SCALE = 1.3;
const COS30 = Math.cos(Math.PI / 6);
const SIN30 = 0.5;

function clampAxis(value: number): number {
  return Math.max(0, Math.min(100, value));
}

/** 등각(isometric) 3축(PoF/CoF/DoF) 투영. viewBox "0 0 560 300" 기준. 축 범위 밖 값은 표시용으로 0~100에 잘라낸다. */
export function projectScorePoint(pof: number, cof: number, dof: number): ProjectedPoint {
  const p = clampAxis(pof);
  const c = clampAxis(cof);
  const d = clampAxis(dof);
  return {
    x: ORIGIN.x + (p - c) * COS30 * SCALE,
    y: ORIGIN.y + (p + c) * SIN30 * SCALE - d * SCALE,
  };
}

export function axisEndPoint(axis: "pof" | "cof" | "dof", value = 100): ProjectedPoint {
  if (axis === "pof") return projectScorePoint(value, 0, 0);
  if (axis === "cof") return projectScorePoint(0, value, 0);
  return projectScorePoint(0, 0, value);
}
