import React from "react";
import { useAuth } from "../../context/AuthContext";
import LoadingSpinner from "./LoadingSpinner";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="full-center">
        <LoadingSpinner size={48} label="Securing connection..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div
        className="full-center"
        style={{ fontFamily: "var(--font-mono)", color: "var(--status-critical)", fontSize: "0.9rem" }}
      >
        UNAUTHORIZED ACCESS: Authentication required.
      </div>
    );
  }

  return <>{children}</>;
};

export default ProtectedRoute;
