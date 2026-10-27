// Auth and RBAC types aligned with backend models

export type Role =
  | 'ADMIN'
  | 'ENGINEERING_MANAGER'
  | 'SENIOR_DEVELOPER'
  | 'DEVELOPER'
  | 'SECURITY_ANALYST'
  | 'QA_ENGINEER'
  | 'VIEWER'

export type UserStatus = 'pending' | 'active' | 'locked'

export type Permission =
  | 'view:dashboard'
  | 'view:graph'
  | 'view:metrics'
  | 'view:reports'
  | 'view:smells'
  | 'run:ingestion'
  | 'view:refactor'
  | 'approve:refactor'
  | 'generate:reports'
  | 'view:security_findings'
  | 'export:security_reports'
  | 'view:team_analytics'
  | 'manage:users'
  | 'view:audit_logs'

export interface User {
  id: string
  full_name: string
  work_email: string
  employee_id: string
  department: string
  position: string
  role: Role
  status: UserStatus
  theme_preference: 'dark' | 'light' | 'system'
  notification_preferences: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export interface UserMeResponse {
  user: User
  permissions: Permission[]
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  role: Role
  permissions: Permission[]
}

export interface LoginPayload {
  work_email: string
  password: string
}

export interface RegisterPayload {
  full_name: string
  work_email: string
  password: string
  employee_id: string
  department: string
  position: string
  role?: Role
}

export interface ChangePasswordPayload {
  current_password: string
  new_password: string
}

export interface UpdateProfilePayload {
  full_name?: string
  department?: string
  position?: string
}

export interface UserPreferencesPayload {
  theme_preference?: 'dark' | 'light' | 'system'
  notification_preferences?: Record<string, unknown>
}

export interface AuditLogEntry {
  id: string
  timestamp: string
  user_id: string
  user_email: string
  user_role: string
  action: string
  resource_type: string
  resource_id?: string
  resource?: string
  status?: string
  details: Record<string, unknown>
  ip_address?: string
}

export interface AdminUser extends User {
  failed_login_attempts?: number
  locked_until?: string
}

export interface DemoUser {
  role: Role
  email: string
  password: string
  full_name: string
  employee_id: string
  department: string
  position: string
}
