import { apiClient } from "./client";
import type { EquipmentDetail, EquipmentSummary, EquipmentTypeInfo, SummaryKPI } from "../types/equipment";

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

export async function fetchEquipmentDetail(equipmentId: number): Promise<EquipmentDetail> {
  const { data } = await apiClient.get<EquipmentDetail>(`/api/equipment/${equipmentId}`);
  return data;
}
