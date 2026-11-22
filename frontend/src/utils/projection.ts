// 5개년 POF 예측 그래프(Stage 21-2) — 서버 projection(저장된 입력으로 기준일만 늦춰 다시 계산한 값)을 그대로 쓴다.
// 진단값은 지금 그대로라고 가정하고 날짜에 따라 바뀌는 감점(경과연수·노화 등)만 반영하므로 POF가 오르는 해도 있다.
import type { ProjectionChange, ProjectionPoint } from "../types/equipment";

export interface ProjectionView {
  label: string; // "현재" / "1년 후"
  pof: number;
  status: ProjectionPoint["status"];
  rising: boolean; // 직전 해보다 POF가 올랐는지
  changes: ProjectionChange[]; // 감점 변화가 큰 순
}

export function projectionView(points: ProjectionPoint[]): ProjectionView[] {
  return points.map((p, i) => ({
    label: p.years_ahead === 0 ? "현재" : `${p.years_ahead}년 후`,
    pof: p.pof,
    status: p.status,
    rising: i > 0 && p.pof > points[i - 1].pof,
    changes: [...p.pof_changes].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta)),
  }));
}

/** "+24.0" / "-1.0" */
export function signed(value: number): string {
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}`;
}

/** POF가 오른 해의 설명 — 감점이 줄어든(양수) 항목 이름. 예: "Furan 감점이 줄어 POF 상승" */
export function risingReason(view: ProjectionView): string | null {
  if (!view.rising) return null;
  const up = view.changes.filter((c) => c.delta > 0).map((c) => c.label);
  return up.length ? `${up.join("·")} 감점이 줄어 POF 상승` : "POF 상승";
}

export const PROJECTION_NOTE =
  "현재 진단·점검값이 그대로라고 가정하고, 날짜에 따라 바뀌는 감점(경과연수·부품 노화 등)만 반영한 예측입니다. " +
  "교체 주기를 가정한 항목(UPS·VDP 차단기 7.5년)이 있으면 POF가 오르는 해가 있을 수 있습니다. 변압기 Furan은 진단 당시 기준이라 예측에서 바뀌지 않고, 케이블 온도기반손상률은 사용년수에 비례해 해마다 커집니다.";
