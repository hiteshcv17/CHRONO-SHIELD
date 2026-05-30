export interface ErrorDetail {
  code: string;
  message: string;
  trace_id?: string | null;
  field?: string | null;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ErrorDetail | null;
  timestamp: string;
  request_id: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export type UserRole = "ADMIN" | "ANALYST" | "VIEWER";

export interface UserResponse {
  id: string;
  username: string;
  email: string | null;
  is_active: boolean;
  role: UserRole;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
