export interface DatabaseStatus {
  name: string
  size: string
  tables: number
  live_rows: number
  inserts: number
  updates: number
  deletes: number
  last_checked: string | null
  last_backup: LastBackup | null
  needs_backup: boolean
}

export interface LastBackup {
  timestamp: string
  backup_size: number
  sql_size: number
  duration: number
}

export interface StatusResponse {
  databases: DatabaseStatus[]
  total_dbs: number
  backup_running: boolean
  retention_days: number
  configured?: boolean
}

export interface BackupProgress {
  running: boolean
  started_at: string | null
  current_db: string | null
  current_step: string | null
  processed: number
  total: number
  last_completed_db: string | null
  last_completed_status: string | null
  download_bytes: number
  download_total: number
  active_jobs: ActiveJob[]
  updated_at: string | null
}

export interface ActiveJob {
  db: string
  step: string
  download_bytes: number
  download_total: number
}

export interface AppSettings {
  SSH_HOST: string
  SSH_PORT: number | string
  SSH_USER: string
  SSH_PASSWORD: string
  SSH_KEY_PATH: string
  PG_HOST: string
  PG_PORT: number | string
  PG_USER: string
  PG_PASSWORD: string
  BACKUP_LOCAL_DIR: string
  BACKUP_REMOTE_TMP_DIR: string
  RETENTION_DAYS: number | string
  SCHEDULER_HOUR: number | string
  SCHEDULER_MINUTE: number | string
  GENERATE_SQL: boolean
  PARALLEL_WORKERS: number | string
}

export interface ConnectionTestResult {
  success: boolean
  ssh: boolean
  postgres: boolean
  pg_version?: string
  error?: string
  message?: string
}

export interface BackupRun {
  started_at: string
  finished_at: string | null
  total_dbs: number
  backed_up: number
  skipped: number
  failed: number
  results: BackupResult[]
  errors: BackupError[]
}

export interface BackupResult {
  db_name: string
  status: string
  timestamp?: string
  backup_file?: string
  sql_file?: string
  backup_size?: number
  sql_size?: number
  duration_seconds?: number
  error?: string
  reason?: string
}

export interface BackupError {
  db_name: string
  error: string
}

export interface Report {
  generated_at: string
  server: string
  total_databases: number
  total_backup_runs: number
  total_backups_created: number
  total_failures: number
  success_rate: number
  local_storage_used: string
  retention_days: number
  databases: ReportDatabase[]
}

export interface ReportDatabase {
  name: string
  size: string
  tables: number
  live_rows: number
  last_backup: LastBackup | null
}

export interface NotificationChannel {
  channel: string
  enabled: boolean
  on_success: boolean
  on_failure: boolean
  on_partial: boolean
  settings: Record<string, string>
}

export interface NotificationTestResult {
  success: boolean
  message: string
}

// ── Authentication ──────────────────────────────────────────────

export interface AuthUser {
  id: number
  username: string
  email: string | null
  role: string
  force_password_change: boolean
}

export interface LoginResponse {
  access_token: string
  user: AuthUser
  force_password_change: boolean
}

// ── User Management ─────────────────────────────────────────────

export interface ManagedUser {
  id: number
  username: string
  email: string | null
  is_active: boolean
  force_password_change: boolean
  role_id: number
  role_name: string
  created_at: string | null
  updated_at: string | null
  deleted_at: string | null
}

export interface CreateUserRequest {
  username: string
  email?: string
  password: string
  role_id: number
}

export interface UpdateUserRequest {
  username?: string
  email?: string
  role_id?: number
  is_active?: boolean
}

export interface Role {
  id: number
  name: string
  description: string | null
}
