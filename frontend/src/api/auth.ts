import apiClient from "./client";

export interface UserResponse {
  id: string;
  username: string;
  email: string | null;
  is_active: boolean;
  role: "ADMIN" | "ANALYST" | "VIEWER";
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

/**
 * Register a new operator account in the ChronoShield system.
 */
export async function registerUser(payload: { username: string; email: string; password: string }): Promise<UserResponse> {
  const res = await apiClient.post<UserResponse>("/api/v1/auth/register", payload);
  return res.data;
}

/**
 * Authenticate with credentials, obtain access token, and establish refresh token cookie session.
 */
export async function loginUser(payload: { username: string; password: string }): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>("/api/v1/auth/login", payload);
  return res.data;
}

/**
 * Request a new access token using the HttpOnly refresh token cookie rotation.
 */
export async function refreshToken(): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>("/api/v1/auth/refresh");
  return res.data;
}

/**
 * Revoke the current refresh token session and clear client cookies.
 */
export async function logoutUser(): Promise<{ success: boolean; message: string }> {
  const res = await apiClient.post<{ success: boolean; message: string }>("/api/v1/auth/logout");
  return res.data;
}

/**
 * Retrieve the current authenticated operator profile.
 */
export async function fetchCurrentUser(): Promise<UserResponse> {
  const res = await apiClient.get<UserResponse>("/api/v1/auth/me");
  return res.data;
}
