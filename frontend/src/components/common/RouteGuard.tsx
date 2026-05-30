import React from "react";
import { Lock, ShieldAlert } from "lucide-react";
import { UserRole } from "../../types/api";
import { ViewTab } from "../../types/navigation";
import { ROLE_TABS } from "../../constants/navigation";

interface RouteGuardProps {
  role: UserRole;
  tab: ViewTab;
  children: React.ReactNode;
}

export const RouteGuard: React.FC<RouteGuardProps> = ({ role, tab, children }) => {
  const allowedTabs = ROLE_TABS[role] || ROLE_TABS.VIEWER;
  const isAllowed = allowedTabs.includes(tab);

  if (!isAllowed) {
    return (
      <div className="access-restricted-container">
        <div className="card access-restricted-card">
          <div className="access-restricted-icon-wrapper">
            <ShieldAlert size={32} className="text-rose" />
          </div>

          <div>
            <h2 className="access-restricted-title">Access Restricted</h2>
            <p className="access-restricted-description">
              Your account is registered as a <strong className="text-cyan">{role}</strong> operator. This view is restricted to higher privilege clearance levels.
            </p>
          </div>

          <div className="access-restricted-badge">
            <Lock size={14} className="text-rose" />
            <span>Decryption Bypass Clearance Level Required</span>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default RouteGuard;
