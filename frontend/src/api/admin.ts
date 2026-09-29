import { apiClient } from "./client";

export interface LoginResponse {
  token: string;
  expires_in: number;
  is_admin: boolean;
}

export interface AuthConfig {
  auth_mode: "none" | "local" | "sso";
  local_login_available: boolean;
}

export interface TablePage {
  table_name: string;
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
  page: number;
  page_size: number;
}

export interface AllowedUser {
  sso_id: string;
  name: string;
  team: string | null;
  is_admin: boolean;
  created_at: string;
}

export async function fetchAuthConfig(): Promise<AuthConfig> {
  const { data } = await apiClient.get<AuthConfig>("/api/admin/auth-config");
  return data;
}

export async function adminLogin(password: string): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>("/api/admin/login", { password });
  return data;
}

export async function adminLogout(token: string): Promise<void> {
  await apiClient.post("/api/admin/logout", null, { headers: { Authorization: `Bearer ${token}` } });
}

export function ssoLoginUrl(): string {
  return `${apiClient.defaults.baseURL ?? ""}/api/admin/sso/login`;
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

export async function fetchAccessUsers(token: string): Promise<AllowedUser[]> {
  const { data } = await apiClient.get<AllowedUser[]>("/api/admin/access-users", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export async function createAccessUser(
  token: string,
  body: { sso_id: string; name: string; team: string | null; is_admin: boolean }
): Promise<AllowedUser> {
  const { data } = await apiClient.post<AllowedUser>("/api/admin/access-users", body, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export async function updateAccessUser(
  token: string,
  ssoId: string,
  body: { name?: string; team?: string | null; is_admin?: boolean }
): Promise<AllowedUser> {
  const { data } = await apiClient.patch<AllowedUser>(`/api/admin/access-users/${ssoId}`, body, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

export async function deleteAccessUser(token: string, ssoId: string): Promise<void> {
  await apiClient.delete(`/api/admin/access-users/${ssoId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}
