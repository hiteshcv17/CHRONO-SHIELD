import React, { createContext, useContext, useState, useEffect } from "react";
import { fetchCurrentUser, loginUser, logoutUser, UserResponse } from "../api/auth";
import { setAccessToken } from "../api/client";

interface AuthContextType {
  user: UserResponse | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Initialize and check if session is already active (silent refresh or existing token)
  const initializeAuth = async () => {
    try {
      // First try to fetch the user profile. If our access token is null/expired,
      // the axios client response interceptor will automatically trigger /auth/refresh
      // and retry /auth/me seamlessly!
      const currentUser = await fetchCurrentUser();
      setUser(currentUser);
    } catch (err) {
      // No active session found or refresh token expired
      setUser(null);
      setAccessToken(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initializeAuth();

    // Listen for custom auth-session-expired events from Axios interceptor
    const handleSessionExpired = () => {
      setUser(null);
      setAccessToken(null);
    };

    window.addEventListener("auth-session-expired", handleSessionExpired);
    return () => {
      window.removeEventListener("auth-session-expired", handleSessionExpired);
    };
  }, []);

  const login = async (username: string, password: string) => {
    setLoading(true);
    try {
      const data = await loginUser({ username, password });
      setAccessToken(data.access_token);
      
      const currentUser = await fetchCurrentUser();
      setUser(currentUser);
    } catch (err) {
      setUser(null);
      setAccessToken(null);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      await logoutUser();
    } catch (err) {
      // Even if network call fails, we still clean up client state
    } finally {
      setUser(null);
      setAccessToken(null);
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
