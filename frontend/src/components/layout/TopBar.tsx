import React, { useState, useEffect } from "react";
import { Search, Bell, Menu, Clock, LogOut, Sun, Moon } from "lucide-react";
import { ConnectionStatus } from "../common/ConnectionStatus";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";

interface TopBarProps {
  onToggleSidebar: () => void;
  searchTerm: string;
  onSearchChange: (val: string) => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  onToggleSidebar,
  searchTerm,
  onSearchChange
}) => {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [showNotifications, setShowNotifications] = useState(false);
  const toggleNotifications = () => setShowNotifications(prev => !prev);
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  // Update clock ticks
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const userInitials = user?.username ? user.username.slice(0, 2).toUpperCase() : "OP";
  const userRoleDisplay = user?.role ? `${user.role.charAt(0) + user.role.slice(1).toLowerCase()} Operator` : "Viewer Operator";

  return (
    <div className="topbar">
      {/* Search & Collapse Trigger */}
      <div className="topbar-left">
        <button className="menu-toggle" onClick={onToggleSidebar} aria-label="Toggle menu Navigation">
          <Menu size={22} />
        </button>
        
        <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
          <Search 
            size={18} 
            color="var(--text-muted)" 
            style={{ position: "absolute", left: "10px" }} 
          />
          <input
            type="text"
            className="search-input"
            style={{ paddingLeft: "2.25rem" }}
            placeholder="Search operational logs..."
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>
      </div>

      {/* Clock, Latency, Profiles */}
      <div className="topbar-right">
        {/* Real-time Clock display */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.9rem", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
          <Clock size={16} color="var(--accent-cyan)" />
          <span>{currentTime.toLocaleTimeString()}</span>
        </div>

        {/* Animated Theme Toggle Sun/Moon */}
        <button 
          onClick={toggleTheme}
          className="theme-toggle-btn"
          title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
          aria-label="Toggle visual theme"
        >
          {theme === "dark" ? <Sun size={20} /> : <Moon size={20} />}
        </button>

        {/* Live API Connection Status Badge */}
        <ConnectionStatus compact />
        <div style={{ position: "relative" }}>
          <button 
            className="notification-button" 
            style={{ cursor: "pointer", background: "none", border: "none", display: "flex", alignItems: "center", justifyContent: "center" }} 
            onClick={toggleNotifications} 
            aria-label="Toggle notifications"
          >
            <Bell size={20} color="var(--text-secondary)" />
            <span 
              style={{ 
                position: "absolute", 
                top: "-2px", 
                right: "-2px", 
                background: "var(--status-critical)", 
                width: "8px", 
                height: "8px", 
                borderRadius: "50%", 
                boxShadow: "0 0 5px var(--status-critical)" 
              }}
            />
          </button>
          {showNotifications && (
            <div className="notification-panel" style={{
              position: "absolute",
              top: "calc(100% + 8px)",
              right: 0,
              width: "260px",
              maxHeight: "300px",
              overflowY: "auto",
              background: "var(--bg-surface)",
              border: "1px solid var(--border-card)",
              borderRadius: "8px",
              boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
              zIndex: 1000,
              padding: "0.5rem"
            }}>
              <div style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.5rem", color: "var(--text-primary)" }}>
                Notifications
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                No new alerts.
              </div>
            </div>
          )}
        </div>

        {/* User profile identifier */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", borderLeft: "1px solid var(--border-card)", paddingLeft: "1.25rem" }}>
          <div 
            style={{ 
              width: "32px", 
              height: "32px", 
              borderRadius: "50%", 
              background: "linear-gradient(135deg, var(--accent-blue), var(--accent-purple))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: "0.85rem",
              color: "var(--text-primary)"
            }}
          >
            {userInitials}
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>{user?.username || "Ops Controller"}</span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{userRoleDisplay}</span>
          </div>

          <button 
            onClick={logout}
            title="Log Out Operator Session"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-muted)",
              padding: "0.25rem",
              borderRadius: "4px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginLeft: "0.5rem",
              transition: "color 0.2s"
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = "var(--status-critical)"}
            onMouseLeave={(e) => e.currentTarget.style.color = "var(--text-muted)"}
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default TopBar;
