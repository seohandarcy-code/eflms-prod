import { apiClient } from "./client";
import type { EquipmentDetail, EquipmentSummary, SummaryKPI } from "../types/equipment";

export async function fetchEquipmentList(factoryCode?: string): Promise<EquipmentSummary[]> {
  const { data } = await apiClient.get<EquipmentSummary[]>("/api/equipment", {
    params: factoryCode ? { factory_code: factoryCode } : undefined,
  });
  return data;
}

export async function fetchSummary(): Promise<SummaryKPI> {
  const { data } = await apiClient.get<SummaryKPI>("/api/summary");
  return data;
}

export async function fetchEquipmentDetail(equipmentId: number): Promise<EquipmentDetail> {
  const { data } = await apiClient.get<EquipmentDetail>(`/api/equipment/${equipmentId}`);
  return data;
}
