import { ViewTab } from "../types/navigation";

export const VIEW_LABELS: Record<ViewTab, string> = {
  health: "Infrastructure Health",
  monitoring: "Live Monitoring",
  alerts: "Anomaly Alerts",
  forecasting: "Forecasting Trends",
  correlation: "Correlation Analytics",
  social: "Social Media Signals",
  geomap: "Geospatial Map",
  replay: "Incident Replay",
  xai: "AI Reasoning",
  benchmark: "Model Benchmarking",
  notifications: "Alert Delivery Control",
  reports: "Executive Report Center",
  assets: "Infrastructure Asset Registry",
  simulation: "AI Simulation Control Deck",
  settings: "System Settings",
  docs: "Documentation",
};

export const ROLE_TABS: Record<string, ViewTab[]> = {
  VIEWER:  ["health", "monitoring", "geomap", "docs"],
  ANALYST: ["health", "monitoring", "geomap", "alerts", "forecasting", "correlation", "social", "replay", "xai", "notifications", "reports", "assets", "simulation", "docs"],
  ADMIN:   ["health", "monitoring", "geomap", "alerts", "forecasting", "correlation", "social", "replay", "xai", "benchmark", "notifications", "reports", "assets", "simulation", "settings", "docs"],
};
