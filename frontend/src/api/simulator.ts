import { apiClient } from "./client";
import type { EquipmentStatus } from "../types/equipment";

// 점수 시뮬레이터(Stage 19) — 계산만 하고 DB에는 쓰지 않는다. 권한은 대시보드와 같다.

export interface SimulatorColumn {
  name: string;
  label: string;
  dtype: string;
  choices?: (string | number)[] | null;
  min?: number | null;
  max?: number | null;
  gt?: number | null;
  required?: boolean | null;
  na_allowed: boolean;
}

export interface SimulatorForm {
  ef_code: string;
  ef_name: string;
  name_field: string;
  columns: SimulatorColumn[];
  header: string;
  /** 그 유형의 설비가 있고 사업장별 참고표(EF7 방전이력)에도 행이 있는 사업장 */
  sites: { factory_code: string; equipment_count: number }[];
  excluded_sites: { factory_code: string; reason: string }[];
  equipment: { equipment_id: number; factory_code: string; equipment_name: string }[];
}

export interface SimulatorFieldError {
  column: string;
  raw_value: string;
  reason: string;
}

export interface SimulatorItem {
  field: string;
  label: string;
  group: string | null;
  summed: boolean;
  value: number | null;
}

export interface SimulatorResult {
  ok: boolean;
  errors: SimulatorFieldError[];
  as_of: string | null;
  pof: number | null;
  cof: number | null;
  dof: number | null;
  total_score: number | null;
  status: EquipmentStatus | null;
  breakdown: Record<string, SimulatorItem[]>;
}

export interface SimulatorSample {
  values: Record<string, string>;
  source: "example" | "equipment";
  equipment_id: number | null;
  baseline: SimulatorResult;
}

export async function fetchSimulatorForm(efCode: string): Promise<SimulatorForm> {
  const { data } = await apiClient.get<SimulatorForm>(`/api/simulator/${efCode}/form`);
  return data;
}

export async function fetchSimulatorSample(efCode: string, equipmentId: number | null): Promise<SimulatorSample> {
  const { data } = await apiClient.get<SimulatorSample>(`/api/simulator/${efCode}/sample`, {
    params: { equipment_id: equipmentId ?? undefined },
  });
  return data;
}

export async function calculateSimulation(efCode: string, values: Record<string, string>): Promise<SimulatorResult> {
  const { data } = await apiClient.post<SimulatorResult>(`/api/simulator/${efCode}/calculate`, { values });
  return data;
}
