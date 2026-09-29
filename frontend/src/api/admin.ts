import { apiClient } from "./client";

export interface LoginResponse {
  token: string;
  expires_in: number;
}

export interface TablePage {
  table_name: string;
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
  page: number;
  page_size: number;
}

export async function adminLogin(password: string): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>("/api/admin/login", { password });
  return data;
}

export async function adminLogout(token: string): Promise<void> {
  await apiClient.post("/api/admin/logout", null, { headers: { Authorization: `Bearer ${token}` } });
}

export async function fetchAdminTables(token: string): Promise<string[]> {
  const { data } = await apiClient.get<{ tables: string[] }>("/api/admin/tables", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data.tables;
}

export async function fetchAdminTablePage(token: string, tableName: string, page: number): Promise<TablePage> {
  const { data } = await apiClient.get<TablePage>(`/api/admin/tables/${tableName}`, {
    headers: { Authorization: `Bearer ${token}` },
    params: { page },
  });
  return data;
}
