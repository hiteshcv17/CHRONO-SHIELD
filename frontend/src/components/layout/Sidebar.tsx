import React from "react";
import { 
  Shield, 
  Activity, 
  Cpu, 
  AlertOctagon, 
  TrendingUp, 
  LineChart,
  Settings,
  HelpCircle,
  MessageSquare,
  Map,
  History,
  Brain,
  BarChart2,
  BellRing,
  FileText,
  Database,
  Play
} from "lucide-react";

import { useAuth } from "../../context/AuthContext";
import { ViewTab } from "../../types/navigation";
import { ROLE_TABS } from "../../constants/navigation";
import { Companion } from "./Companion";

interface SidebarProps {
  activeTab: ViewTab;
  onTabChange: (tab: ViewTab) => void;
  isOpen: boolean;
}

interface MenuItem {
  id: ViewTab;
  label: string;
  icon: React.ReactNode;
}


export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  isOpen
}) => {
  const { user } = useAuth();
  const userRole = user?.role || "VIEWER";
  const allowedTabs = ROLE_TABS[userRole] || ROLE_TABS.VIEWER;

  const allMenuItems: MenuItem[] = [
    {
      id: "health",
      label: "Infrastructure Health",
      icon: <Cpu size={18} />
    },
    {
      id: "monitoring",
      label: "Live Monitoring",
      icon: <Activity size={18} />
    },
    {
      id: "alerts",
      label: "Anomaly Alerts",
      icon: <AlertOctagon size={18} />
    },
    {
      id: "forecasting",
      label: "Forecasting Trends",
      icon: <TrendingUp size={18} />
    },
    {
      id: "correlation",
      label: "Correlation Analytics",
      icon: <LineChart size={18} />
    },
    {
      id: "social",
      label: "Social Signals",
      icon: <MessageSquare size={18} />
    },
    {
      id: "geomap",
      label: "Geo Map",
      icon: <Map size={18} />
    },
    {
      id: "replay",
      label: "Incident Replay",
      icon: <History size={18} />
    },
    {
      id: "xai",
      label: "AI Reasoning",
      icon: <Brain size={18} />
    },
    {
      id: "benchmark",
      label: "Benchmarking",
      icon: <BarChart2 size={18} />
    },
    {
      id: "notifications",
      label: "Alert Delivery",
      icon: <BellRing size={18} />
    },
    {
      id: "reports",
      label: "Executive Reports",
      icon: <FileText size={18} />
    },
    {
      id: "assets",
      label: "Infrastructure Assets",
      icon: <Database size={18} />
    },
    {
      id: "simulation",
      label: "AI Simulation Deck",
      icon: <Play size={18} color="var(--accent-cyan)" />
    }
  ];

  const menuItems = allMenuItems.filter(item => allowedTabs.includes(item.id));


  return (
    <aside className={`sidebar ${isOpen ? "active" : ""}`}>
      {/* Sidebar Top Logo */}
      <div className="sidebar-header">
        <Shield size={24} color="var(--accent-cyan)" />
        <span className="logo">ChronoShield AI</span>
      </div>

      {/* Main Core Navigation Links */}
      <nav className="sidebar-menu">
        {menuItems.map((item) => (
          <button
            key={item.id}
            className={`sidebar-item ${activeTab === item.id ? "active" : ""}`}
            onClick={() => onTabChange(item.id)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}

        {/* Separator */}
        <div style={{ height: "1px", background: "var(--border-card)", margin: "1.5rem 0" }} />

        {/* Static Auxiliary Links */}
        {allowedTabs.includes("settings") && (
          <button
            className={`sidebar-item ${activeTab === "settings" ? "active" : ""}`}
            onClick={() => onTabChange("settings")}
          >
            <Settings size={18} />
            <span>System Settings</span>
          </button>
        )}
        <button
          className={`sidebar-item ${activeTab === "docs" ? "active" : ""}`}
          onClick={() => onTabChange("docs")}
        >
          <HelpCircle size={18} />
          <span>Documentation</span>
        </button>
      </nav>

      {/* Cybernetic Eye-Tracking Companion Mascot */}
      <Companion />

      {/* Sidebar Footer Details */}
      <div className="sidebar-footer">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.25rem" }}>
          <span>Agent Version</span>
          <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>v1.0.0</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>Telemetry Node</span>
          <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>AP-East-4</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
