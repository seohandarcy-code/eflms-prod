import { apiClient } from "./client";
import type { EquipmentDetail, EquipmentSummary, EquipmentTypeInfo, FormulaDocs, SummaryKPI } from "../types/equipment";

export async function fetchEquipmentList(params: { factoryCode?: string; efCode?: string } = {}): Promise<EquipmentSummary[]> {
  const { data } = await apiClient.get<EquipmentSummary[]>("/api/equipment", {
    params: { factory_code: params.factoryCode, ef_code: params.efCode },
  });
  return data;
}

export async function fetchSummary(efCode?: string): Promise<SummaryKPI> {
  const { data } = await apiClient.get<SummaryKPI>("/api/summary", { params: { ef_code: efCode } });
  return data;
}

export async function fetchEquipmentTypes(): Promise<EquipmentTypeInfo[]> {
  const { data } = await apiClient.get<EquipmentTypeInfo[]>("/api/equipment-types");
  return data;
}

/** 지표설명 상세 페이지 — 유형의 감점 항목별 계산식(Stage 22-11). */
export async function fetchFormulaDocs(efCode: string): Promise<FormulaDocs> {
  const { data } = await apiClient.get<FormulaDocs>(`/api/equipment-types/${encodeURIComponent(efCode)}/formulas`);
  return data;
}

export async function fetchEquipmentDetail(equipmentId: number): Promise<EquipmentDetail> {
  const { data } = await apiClient.get<EquipmentDetail>(`/api/equipment/${equipmentId}`);
  return data;
}
