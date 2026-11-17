import { apiClient } from "./client";

export interface LoginResponse {
  token: string;
  expires_in: number;
  is_admin: boolean;
  role: string;
}

export interface AuthConfig {
  auth_mode: "none" | "local" | "sso";
  local_login_available: boolean;
  // AUTH_MODE=sso면 대시보드도 로그인해야 보인다(Stage 16-1)
  dashboard_login_required: boolean;
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

/** next: 로그인 뒤 돌아올 화면 경로(같은 사이트 안 경로만 — 백엔드가 다시 검사한다). */
export function ssoLoginUrl(next = "/"): string {
  return `${apiClient.defaults.baseURL ?? ""}/api/admin/sso/login?next=${encodeURIComponent(next)}`;
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

// --- 데이터 입력·내보내기 (Stage 16-2/16-3, 16-6 붙여넣기 — admin 전용) ---

export interface ReferenceTableTarget {
  name: string;
  label: string;
  rows: number;
}

export interface DataTarget {
  ef_code: string;
  ef_name: string;
  equipment_count: number;
  reference_tables: ReferenceTableTarget[];
}

export interface ImportRowError {
  row_number: number;
  column: string;
  raw_value: string;
  reason: string;
}

/** 백엔드 ImportResult / ReferenceImportResult를 그대로 — kind로 구분한다. */
export interface ImportResultBody {
  kind: "equipment" | "reference";
  ok: boolean;
  file_path: string;
  ef_code: string;
  replace: boolean;
  dry_run: boolean;
  total_rows: number;
  file_errors: string[];
  row_errors: ImportRowError[];
  unknown_columns: string[];
  // 설비
  imported_rows?: number;
  replaced_rows?: number;
  existing_rows?: number;
  ignored_columns?: string[];
  na_values?: Record<string, number>;
  reference_warnings?: string[];
  // 참고표
  table?: string;
  inserted_rows?: number;
  updated_rows?: number;
  deleted_rows?: number;
  table_rows_before?: number;
  table_rows_after?: number;
  recalculated?: number;
  warnings?: string[];
  // 검증 통과 시 행별 구분 — 미리보기에서 확정 전에 보여준다
  row_actions: { row_number: number; action: "추가" | "갱신"; key?: string[] }[];
}

export interface TemplateColumn {
  name: string;
  label: string;
  dtype: string;
  choices?: (string | number)[];
  min?: number;
  max?: number;
  gt?: number;
  required?: boolean;
  na_allowed: boolean;
}

export interface DataTemplate {
  ef_code: string;
  table: string;
  key: string[];
  columns: TemplateColumn[];
  header: string;
}

export async function fetchDataTemplate(token: string, efCode: string, table: string): Promise<DataTemplate> {
  const { data } = await apiClient.get<DataTemplate>("/api/admin/data/template", {
    headers: { Authorization: `Bearer ${token}` },
    params: { ef_code: efCode, table: table || undefined },
  });
  return data;
}

export async function fetchDataTargets(token: string): Promise<DataTarget[]> {
  const { data } = await apiClient.get<DataTarget[]>("/api/admin/data/targets", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}

/** 붙여넣은 탭 구분 텍스트를 검증(check=true) 또는 반영(check=false). */
export async function importPastedData(
  token: string,
  params: { text: string; efCode: string; table: string; replace: boolean; check: boolean }
): Promise<ImportResultBody> {
  const { data } = await apiClient.post<ImportResultBody>(
    "/api/admin/data/import",
    { ef_code: params.efCode, table: params.table, replace: params.replace, check: params.check, text: params.text },
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return data;
}

/** 내보내기 파일을 받아 브라우저 다운로드로 넘긴다. 반환: 행 수. */
export async function downloadDataExport(token: string, efCode: string, table: string): Promise<number> {
  const response = await apiClient.get<Blob>("/api/admin/data/export", {
    headers: { Authorization: `Bearer ${token}` },
    params: { ef_code: efCode, table: table || undefined },
    responseType: "blob",
  });
  const disposition = String(response.headers["content-disposition"] ?? "");
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? `${efCode}_${table || "equipment"}.dat`;
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return Number(response.headers["x-row-count"] ?? 0);
}

// --- SQL 조회 (Stage 16-5, admin 전용) ---

export interface SqlQueryResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  truncated: boolean;
  elapsed_ms: number;
  max_rows: number;
}

export async function runSqlQuery(token: string, sql: string): Promise<SqlQueryResult> {
  const { data } = await apiClient.post<SqlQueryResult>(
    "/api/admin/sql",
    { sql },
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return data;
}

/** 전체 DB를 PostgreSQL용 .sql로 내려받는다(Stage 16-8). 반환: 테이블 수·전체 행 수. */
export async function downloadFullSqlDump(token: string): Promise<{ tables: number; rows: number }> {
  const response = await apiClient.get<Blob>("/api/admin/data/export-sql", {
    headers: { Authorization: `Bearer ${token}` },
    responseType: "blob",
  });
  const disposition = String(response.headers["content-disposition"] ?? "");
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "eflms_full.sql";
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return { tables: Number(response.headers["x-table-count"] ?? 0), rows: Number(response.headers["x-row-count"] ?? 0) };
}
