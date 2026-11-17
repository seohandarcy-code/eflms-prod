import type { BreakdownItem, EquipmentSummary } from "../types/equipment";
import ef1Png from "../assets/facilities/ef1.png";
import ef2Png from "../assets/facilities/ef2.png";
import ef3Png from "../assets/facilities/ef3.png";
import ef4Png from "../assets/facilities/ef4.png";
import ef5Png from "../assets/facilities/ef5.png";
import ef6Png from "../assets/facilities/ef6.png";
import ef7Png from "../assets/facilities/ef7.png";
import ef1Gif from "../assets/facilities/ef1.gif";
import ef2Gif from "../assets/facilities/ef2.gif";
import ef3Gif from "../assets/facilities/ef3.gif";
import ef4Gif from "../assets/facilities/ef4.gif";
import ef5Gif from "../assets/facilities/ef5.gif";
import ef6Gif from "../assets/facilities/ef6.gif";
import ef7Gif from "../assets/facilities/ef7.gif";
import ef1Webp from "../assets/facilities/ef1.webp";
import ef2Webp from "../assets/facilities/ef2.webp";
import ef3Webp from "../assets/facilities/ef3.webp";
import ef4Webp from "../assets/facilities/ef4.webp";
import ef5Webp from "../assets/facilities/ef5.webp";
import ef6Webp from "../assets/facilities/ef6.webp";
import ef7Webp from "../assets/facilities/ef7.webp";

// 전기설비를 잘 모르는 사용자를 위한 설비 설명(대시보드 "선택한 설비" 카드 · 설비 안내 페이지).
// 설비 이름은 백엔드 레지스트리(ef_name)가 원본이고, 여기에는 사람이 읽는 설명과 사진만 둔다.
// 사진은 design/elec_fac_img 원본에서 아래 이름표를 잘라낸 가공본(496×366) — 파일 번호가 아니라
// EF 코드로 연결한다. 움직이는 사진은 WebP(GIF의 약 1/9 크기, 원래 색)가 기본이고 GIF는 WebP를 못 쓰는
// 브라우저용 대체, PNG는 정지 사진(표·계통도·움직임 줄이기 설정·로딩 중 배경) — components/FacilityImage.vue. 새 설비유형은 여기 항목이 없어도 화면이 깨지지 않는다(사진 자리 아이콘, 설명 생략).
export interface FacilityInfo {
  /** 이름 옆 보조 설명(예: "가스절연개폐장치") */
  subtitle: string;
  /** 대시보드 카드의 한 줄 설명 */
  summary: string;
  /** 계통 위치(전압 단계) */
  position: string;
  /** 주요 기능 */
  role: string;
  /** 반도체 Fab에서의 역할 */
  fabRole: string;
  /** 고장 나면(COF가 뜻하는 것) */
  failure: string;
  overview: string;
  parts: string;
  causes: string;
  /** 정지 사진(PNG) — 카드·표·계통도 */
  image: string;
  /** 움직이는 사진(GIF) — WebP를 못 쓰는 브라우저용 대체 */
  animated: string;
  /** 움직이는 사진(WebP) — 대시보드 "선택한 설비" 카드·안내 페이지 상세 카드 */
  animatedWebp: string;
}

export const FACILITY_INFO: Record<string, FacilityInfo> = {
  EF1: {
    subtitle: "154 → 22.9kV",
    summary: "154kV 전기를 사내에서 쓰는 22.9kV로 낮추는 설비",
    position: "154 → 22.9kV",
    role: "전압을 낮춰 사내 배전 전압으로 바꿈",
    fabRole: "생산동별 전력 공급의 중심",
    failure: "담당 구역 장시간 정전(교체에 수개월)",
    overview:
      "154kV 전기를 공장 안에서 쓰는 22.9kV로 낮춥니다. 내부는 절연유로 채워져 있어, 기름 속 가스(DGA)를 분석하면 속 상태를 알 수 있습니다.",
    parts: "철심·권선, 절연유, 부싱, 탭절환기(OLTC), 냉각기(방열기·팬)",
    causes: "열·수분에 따른 절연지·절연유 열화, 과부하, OLTC 마모",
    image: ef1Png,
    animated: ef1Gif,
    animatedWebp: ef1Webp,
  },
  EF2: {
    subtitle: "가스절연개폐장치",
    summary: "154kV 회로를 열고 닫고 사고 전류를 끊는 개폐장치",
    position: "154kV",
    role: "가스로 절연한 개폐장치 — 회로를 열고 닫고 사고 전류를 차단",
    fabRole: "사고 구간을 빠르게 떼어 내 나머지를 보호",
    failure: "전기를 받지 못해 넓은 정전",
    overview:
      "차단기·단로기·모선을 절연 가스(SF6)를 채운 금속 함 안에 넣은 154kV 개폐장치입니다. 작은 공간에 설치할 수 있습니다.",
    parts: "차단기, 단로기·접지개폐기, 모선, 계기용 변성기, SF6 가스",
    causes: "차단 동작 누적, 가스 누설, 절연물 열화, 부분방전",
    image: ef2Png,
    animated: ef2Gif,
    animatedWebp: ef2Webp,
  },
  EF3: {
    subtitle: "154kV",
    summary: "한전 154kV 전기를 공장까지 땅속으로 보내는 케이블",
    position: "154kV",
    role: "한전 전기를 Fab 변전소까지 땅속으로 전달",
    fabRole: "Fab 전체 전력의 입구",
    failure: "전체 또는 넓은 구역 정전",
    overview: "154kV 전력을 송전선로에서 Fab 변전소까지 전력구·관로를 따라 땅속으로 보내는 케이블입니다.",
    parts: "도체, 절연체(XLPE), 금속 시스, 중간·종단 접속함",
    causes: "과부하·고온에 따른 절연 열화, 부분방전, 접속함 불량, 시스 순환전류",
    image: ef3Png,
    animated: ef3Gif,
    animatedWebp: ef3Webp,
  },
  EF4: {
    subtitle: "22.9kV · 저압",
    summary: "전기를 라인·유틸리티로 나눠 보내고 차단기로 보호하는 설비",
    position: "22.9kV · 저압",
    role: "전기를 라인·유틸리티로 나누고 차단기로 보호",
    fabRole: "장비·공조·용수 설비 전원 분배",
    failure: "그 계통에 물린 장비 정지",
    overview: "변압기에서 온 전기를 각 동·라인·유틸리티로 나눠 보내는 차단기·계전기 묶음 함입니다.",
    parts: "차단기, 보호계전기, 모선, 계기용 변류기(CT)·변압기(PT), 외함",
    causes: "접촉부 볼트 풀림·과열, 차단기 노화, 전기실 고온·먼지",
    image: ef4Png,
    animated: ef4Gif,
    animatedWebp: ef4Webp,
  },
  EF5: {
    subtitle: "무정전전원장치",
    summary: "정전 때도 끊김 없이 전기를 주는 무정전전원장치",
    position: "저압",
    role: "정전 때 끊김 없이 전기 공급",
    fabRole: "핵심 장비·제어·IT 보호",
    failure: "정전 순간 장비가 바로 멈춤",
    overview:
      "정전이나 전압 변동이 있어도 끊김 없이 전기를 줍니다. 평소엔 전기를 정류해 배터리를 채우고, 정전 때 배터리 전기를 다시 교류로 바꿔 보냅니다.",
    parts: "정류기, 인버터(IGBT), 커패시터, 냉각 팬, 제어 보드, 바이패스",
    causes: "커패시터·팬 수명, IGBT 열화, 전기실 고온",
    image: ef5Png,
    animated: ef5Gif,
    animatedWebp: ef5Webp,
  },
  EF6: {
    subtitle: "순간전압강하 보상장치",
    summary: "아주 짧은 전압 저하를 메워 공정 장비가 멈추지 않게 하는 장치",
    position: "장비 앞단",
    role: "순간적인 전압 저하를 보상",
    fabRole: "1초도 안 되는 전압 저하에 장비가 멈추지 않게 함",
    failure: "공정 중단 → 웨이퍼 불량(스크랩)",
    overview:
      "낙뢰 등으로 전압이 아주 짧게 떨어질 때(1초 미만) 이를 감지해 저장해 둔 전기로 메워, 민감한 공정 장비가 멈추지 않게 합니다.",
    parts: "에너지 저장부(콘덴서 또는 공용 배터리), 인버터(IGBT), 냉각 팬, 제어 보드",
    causes: "커패시터·팬 수명, IGBT 열화, 전기실 고온",
    image: ef6Png,
    animated: ef6Gif,
    animatedWebp: ef6Webp,
  },
  EF7: {
    subtitle: "UPS 연결",
    summary: "UPS가 정전 때 쓸 전기를 저장해 두는 장치",
    position: "UPS 연결",
    role: "UPS가 쓸 전기를 저장",
    fabRole: "정전 때 수 분~수십 분 버팀",
    failure: "UPS가 있어도 백업 실패, 화재 위험",
    overview:
      "UPS가 정전 때 쓸 전기를 저장합니다. 충전·방전을 반복하며 저장할 수 있는 양(SOH)이 조금씩 줄어듭니다.",
    parts: "셀·모듈, 배터리 관리장치(BMS), 랙, 배터리실 공조·소화설비",
    causes: "충방전 반복·고온에 따른 용량 감소, 셀 간 전압·온도 편차, 화재 위험",
    image: ef7Png,
    animated: ef7Gif,
    animatedWebp: ef7Webp,
  },
};

// 전기가 흐르는 순서(한전 → 케이블 → GIS → 변압기 → 수배전반 → UPS·배터리 → VDP).
const FLOW_ORDER = ["EF3", "EF2", "EF1", "EF4", "EF5", "EF7", "EF6"];

/** 설비유형 코드를 전기가 흐르는 순서로 정렬한다. 순서에 없는 유형(새 유형)은 코드순으로 뒤에 붙는다. */
export function sortByFlow(codes: string[]): string[] {
  const rank = (code: string) => {
    const index = FLOW_ORDER.indexOf(code);
    return index === -1 ? FLOW_ORDER.length : index;
  };
  return [...codes].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
}

/** 안내 페이지 앵커 id(#ef7). */
export function facilityAnchor(efCode: string): string {
  return efCode.toLowerCase();
}

export interface FacilityCount {
  total: number;
  /** 점검필요 = 교체검토 + 즉시교체 */
  needsInspection: number;
}

/** 목록에서 설비유형별 대수와 점검필요 수를 센다. 목록에 없는 유형은 0대. */
export function countByType(list: EquipmentSummary[]): Record<string, FacilityCount> {
  const counts: Record<string, FacilityCount> = {};
  for (const item of list) {
    const count = (counts[item.ef_code] ??= { total: 0, needsInspection: 0 });
    count.total += 1;
    if (item.status === "review" || item.status === "replace") count.needsInspection += 1;
  }
  return counts;
}

/** "이 시스템이 보는 항목" — POF 감점 항목 라벨 앞쪽 몇 개와 나머지 개수. */
export function pofHighlights(items: BreakdownItem[], max = 5): { labels: string[]; rest: number } {
  const labels = items.map((item) => item.label);
  return { labels: labels.slice(0, max), rest: Math.max(0, labels.length - max) };
}
