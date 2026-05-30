import React, { useState } from "react";
import {
  Settings,
  Shield,
  Bell,
  Database,
  Palette,
  Globe,
  Key,
  Save,
  RefreshCw,
  ToggleLeft,
  ToggleRight,
  ChevronRight,
  AlertTriangle,
  CheckCircle,
  Cpu,
  Clock,
  Wifi,
} from "lucide-react";
import { useTheme } from "../../context/ThemeContext";

type SettingsTab = "general" | "security" | "notifications" | "data" | "appearance";

interface ToggleProps {
  value: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
}

const Toggle: React.FC<ToggleProps> = ({ value, onChange, label, description }) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0.9rem 1rem",
      background: "var(--bg-card)",
      borderRadius: "10px",
      border: "1px solid var(--border-card)",
      marginBottom: "0.6rem",
      cursor: "pointer",
      transition: "border-color 0.2s",
    }}
    onClick={() => onChange(!value)}
    onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--accent-cyan)")}
    onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border-card)")}
  >
    <div>
      <div style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "0.88rem" }}>{label}</div>
      {description && (
        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>{description}</div>
      )}
    </div>
    <div style={{ color: value ? "var(--accent-cyan)" : "var(--text-muted)", flexShrink: 0 }}>
      {value ? <ToggleRight size={28} /> : <ToggleLeft size={28} />}
    </div>
  </div>
);

interface SelectFieldProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}

const SelectField: React.FC<SelectFieldProps> = ({ label, value, options, onChange }) => (
  <div style={{ marginBottom: "0.9rem" }}>
    <label style={{ display: "block", fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "0.4rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
      {label}
    </label>
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        width: "100%",
        background: "var(--bg-card)",
        border: "1px solid var(--border-card)",
        borderRadius: "8px",
        color: "var(--text-primary)",
        padding: "0.6rem 0.85rem",
        fontSize: "0.88rem",
        outline: "none",
        cursor: "pointer",
      }}
    >
      {options.map(o => (
        <option key={o.value} value={o.value} style={{ background: "var(--bg-panel)" }}>
          {o.label}
        </option>
      ))}
    </select>
  </div>
);

const SETTINGS_TABS: { id: SettingsTab; label: string; icon: React.ReactNode }[] = [
  { id: "general",       label: "General",       icon: <Settings size={16} /> },
  { id: "security",      label: "Security",      icon: <Shield size={16} /> },
  { id: "notifications", label: "Notifications", icon: <Bell size={16} /> },
  { id: "data",          label: "Data & Storage", icon: <Database size={16} /> },
  { id: "appearance",    label: "Appearance",    icon: <Palette size={16} /> },
];

import { getWithRetry, putWithRetry } from "../../api/client";

export const SystemSettings: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const [activeSection, setActiveSection] = useState<SettingsTab>("general");
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);

  // General settings state
  const [timezone, setTimezone] = useState("UTC+0");
  const [language, setLanguage] = useState("en");
  const [refreshInterval, setRefreshInterval] = useState("30");
  const [autoLogout, setAutoLogout] = useState(true);
  const [telemetryEnabled, setTelemetryEnabled] = useState(true);
  const [compressLogs, setCompressLogs] = useState(false);

  // Security state
  const [mfaEnabled, setMfaEnabled] = useState(true);
  const [apiKeyRotation, setApiKeyRotation] = useState(false);
  const [sessionTimeout, setSessionTimeout] = useState("60");
  const [auditLogging, setAuditLogging] = useState(true);
  const [ipWhitelist, setIpWhitelist] = useState(false);
  const [rateLimitingEnabled, setRateLimitingEnabled] = useState(true);

  // Notifications
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [slackIntegration, setSlackIntegration] = useState(false);
  const [pagerDuty, setPagerDuty] = useState(false);
  const [criticalOnly, setCriticalOnly] = useState(false);
  const [digestMode, setDigestMode] = useState(true);

  // Data
  const [retentionDays, setRetentionDays] = useState("90");
  const [backupEnabled, setBackupEnabled] = useState(true);
  const [compressionLevel, setCompressionLevel] = useState("medium");
  const [exportFormat, setExportFormat] = useState("parquet");

  React.useEffect(() => {
    const fetchSettings = async () => {
      try {
        setLoading(true);
        const res = await getWithRetry<{ success: boolean; data: { rate_limiting_enabled?: boolean } }>("/api/v1/settings");
        if (res.success && res.data) {
          if (res.data.rate_limiting_enabled !== undefined) {
            setRateLimitingEnabled(res.data.rate_limiting_enabled);
          }
        }
      } catch (err) {
        console.error("Failed to load settings from API:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    try {
      setLoading(true);
      const res = await putWithRetry<{ success: boolean }>("/api/v1/settings", {
        rate_limiting_enabled: rateLimitingEnabled,
      });
      if (res.success) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    } catch (err) {
      console.error("Failed to save settings:", err);
      alert("Failed to save security settings.");
    } finally {
      setLoading(false);
    }
  };

  const renderContent = () => {
    switch (activeSection) {
      case "general":
        return (
          <div>
            <h3 style={{ color: "var(--text-primary)", marginBottom: "1.25rem", fontWeight: 700 }}>General Configuration</h3>
            <SelectField label="Timezone" value={timezone} onChange={setTimezone} options={[
              { value: "UTC-8", label: "UTC-8 (Pacific)" },
              { value: "UTC-5", label: "UTC-5 (Eastern)" },
              { value: "UTC+0", label: "UTC+0 (GMT)" },
              { value: "UTC+1", label: "UTC+1 (CET)" },
              { value: "UTC+5:30", label: "UTC+5:30 (IST)" },
              { value: "UTC+8", label: "UTC+8 (SGT)" },
            ]} />
            <SelectField label="Interface Language" value={language} onChange={setLanguage} options={[
              { value: "en", label: "English" },
              { value: "fr", label: "Français" },
              { value: "de", label: "Deutsch" },
              { value: "ja", label: "日本語" },
            ]} />
            <SelectField label="Dashboard Refresh Interval (seconds)" value={refreshInterval} onChange={setRefreshInterval} options={[
              { value: "10", label: "10s (High frequency)" },
              { value: "30", label: "30s (Default)" },
              { value: "60", label: "60s (Low load)" },
              { value: "300", label: "5 min (Minimal)" },
            ]} />
            <div style={{ marginTop: "1rem" }}>
              <Toggle value={autoLogout} onChange={setAutoLogout} label="Auto Logout on Inactivity" description="Locks session after 30 minutes of no interaction" />
              <Toggle value={telemetryEnabled} onChange={setTelemetryEnabled} label="Telemetry Ingestion Active" description="Real-time streaming from all registered sensors" />
              <Toggle value={compressLogs} onChange={setCompressLogs} label="Compress Log Output" description="Reduce log storage footprint with gzip compression" />
            </div>
          </div>
        );

      case "security":
        return (
          <div>
            <h3 style={{ color: "var(--text-primary)", marginBottom: "1.25rem", fontWeight: 700 }}>Security Policies</h3>
            <Toggle value={mfaEnabled} onChange={setMfaEnabled} label="Multi-Factor Authentication" description="Require TOTP on all admin logins" />
            <Toggle value={apiKeyRotation} onChange={setApiKeyRotation} label="Automatic API Key Rotation" description="Rotate all API keys every 30 days" />
            <Toggle value={auditLogging} onChange={setAuditLogging} label="Full Audit Logging" description="Log all user actions to immutable audit trail" />
            <Toggle value={ipWhitelist} onChange={setIpWhitelist} label="IP Allowlist Enforcement" description="Restrict dashboard access to approved IP ranges" />
            <Toggle value={rateLimitingEnabled} onChange={setRateLimitingEnabled} label="Enforce API Rate Limiting" description="Rate limit requests to 100 req/min per IP to prevent Denial of Service" />
            <SelectField label="Session Timeout (minutes)" value={sessionTimeout} onChange={setSessionTimeout} options={[
              { value: "15", label: "15 min" },
              { value: "30", label: "30 min" },
              { value: "60", label: "1 hour" },
              { value: "480", label: "8 hours" },
            ]} />
            <div style={{ marginTop: "1.5rem", padding: "1rem", background: "rgba(239,68,68,0.08)", borderRadius: "10px", border: "1px solid rgba(239,68,68,0.2)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--accent-rose)", fontWeight: 700, marginBottom: "0.5rem" }}>
                <Key size={15} /> Danger Zone
              </div>
              <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>Revoke all active sessions and force re-authentication for all users.</p>
              <button
                style={{ padding: "0.5rem 1rem", background: "rgba(239,68,68,0.15)", border: "1px solid var(--accent-rose)", borderRadius: "6px", color: "var(--accent-rose)", cursor: "pointer", fontSize: "0.82rem", fontWeight: 600 }}
                onClick={() => alert("All sessions revoked (demo mode)")}
              >
                Revoke All Sessions
              </button>
            </div>
          </div>
        );

      case "notifications":
        return (
          <div>
            <h3 style={{ color: "var(--text-primary)", marginBottom: "1.25rem", fontWeight: 700 }}>Alert Delivery Channels</h3>
            <Toggle value={emailAlerts} onChange={setEmailAlerts} label="Email Alerts" description="Send anomaly alerts to registered operator emails" />
            <Toggle value={slackIntegration} onChange={setSlackIntegration} label="Slack Integration" description="Post alerts to #chronoshield-ops channel" />
            <Toggle value={pagerDuty} onChange={setPagerDuty} label="PagerDuty Escalation" description="Auto-page on-call engineer for CRITICAL events" />
            <Toggle value={criticalOnly} onChange={setCriticalOnly} label="Critical Alerts Only" description="Suppress WARNING and INFO level notifications" />
            <Toggle value={digestMode} onChange={setDigestMode} label="Daily Summary Digest" description="Send 08:00 UTC daily status summary" />
            <div style={{ marginTop: "1rem", padding: "0.85rem 1rem", background: "var(--bg-card)", borderRadius: "10px", border: "1px solid var(--border-card)" }}>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "0.4rem", fontWeight: 600, textTransform: "uppercase" }}>Webhook Endpoint (Slack)</div>
              <input
                placeholder="https://hooks.slack.com/services/..."
                style={{ width: "100%", background: "transparent", border: "none", outline: "none", color: "var(--text-primary)", fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}
              />
            </div>
          </div>
        );

      case "data":
        return (
          <div>
            <h3 style={{ color: "var(--text-primary)", marginBottom: "1.25rem", fontWeight: 700 }}>Data Management</h3>
            <SelectField label="Telemetry Retention Window" value={retentionDays} onChange={setRetentionDays} options={[
              { value: "30", label: "30 days" },
              { value: "90", label: "90 days (Default)" },
              { value: "180", label: "6 months" },
              { value: "365", label: "1 year" },
            ]} />
            <SelectField label="Export Format" value={exportFormat} onChange={setExportFormat} options={[
              { value: "parquet", label: "Apache Parquet (Recommended)" },
              { value: "csv", label: "CSV" },
              { value: "json", label: "JSON Lines" },
            ]} />
            <SelectField label="Compression Level" value={compressionLevel} onChange={setCompressionLevel} options={[
              { value: "none", label: "None" },
              { value: "medium", label: "Medium (gzip)" },
              { value: "high", label: "High (zstd)" },
            ]} />
            <Toggle value={backupEnabled} onChange={setBackupEnabled} label="Automated Backups" description="Daily snapshot to cold storage at 02:00 UTC" />
            <div style={{ marginTop: "1.25rem", display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem" }}>
              {[
                { label: "Stored Records", value: "14.2M", icon: <Database size={16} /> },
                { label: "Storage Used", value: "38.7 GB", icon: <Cpu size={16} /> },
                { label: "Oldest Record", value: "89 days", icon: <Clock size={16} /> },
              ].map(s => (
                <div key={s.label} style={{ background: "var(--bg-card)", borderRadius: "10px", border: "1px solid var(--border-card)", padding: "0.85rem", textAlign: "center" }}>
                  <div style={{ color: "var(--accent-cyan)", marginBottom: "0.35rem" }}>{s.icon}</div>
                  <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>{s.value}</div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        );

      case "appearance":
        return (
          <div>
            <h3 style={{ color: "var(--text-primary)", marginBottom: "1.25rem", fontWeight: 700 }}>Appearance & Display</h3>
            <div style={{ marginBottom: "1.5rem" }}>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "0.75rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Color Theme</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem" }}>
                {([
                  { id: "dark", label: "Midnight Ops", colors: ["#0d1117", "#161b22", "#00f5d4"] },
                  { id: "light", label: "Glacier", colors: ["#f0f4f8", "#ffffff", "#0066ff"] },
                  { id: "solarized", label: "Solarized", colors: ["#002b36", "#073642", "#2aa198"] },
                ] as { id: string; label: string; colors: string[] }[]).map(t => (
                  <button
                    key={t.id}
                    onClick={() => setTheme(t.id as "dark" | "light" | "solarized")}
                    style={{
                      background: t.colors[0],
                      border: `2px solid ${theme === t.id ? t.colors[2] : "transparent"}`,
                      borderRadius: "10px",
                      padding: "1rem 0.75rem",
                      cursor: "pointer",
                      textAlign: "center",
                      transition: "border-color 0.2s, transform 0.15s",
                      transform: theme === t.id ? "scale(1.03)" : "scale(1)",
                    }}
                  >
                    <div style={{ display: "flex", gap: "4px", justifyContent: "center", marginBottom: "0.5rem" }}>
                      {t.colors.map((c, i) => (
                        <div key={i} style={{ width: 12, height: 12, borderRadius: "50%", background: c }} />
                      ))}
                    </div>
                    <div style={{ fontSize: "0.76rem", color: t.colors[2], fontWeight: 600 }}>{t.label}</div>
                    {theme === t.id && <div style={{ fontSize: "0.65rem", color: t.colors[2], marginTop: "0.2rem" }}>Active</div>}
                  </button>
                ))}
              </div>
            </div>

            <SelectField label="Dashboard Density" value="comfortable" onChange={() => {}} options={[
              { value: "compact", label: "Compact" },
              { value: "comfortable", label: "Comfortable (Default)" },
              { value: "spacious", label: "Spacious" },
            ]} />
            <SelectField label="Chart Rendering" value="webgl" onChange={() => {}} options={[
              { value: "canvas", label: "Canvas 2D (Compatible)" },
              { value: "webgl", label: "WebGL (High Performance)" },
              { value: "svg", label: "SVG (Accessible)" },
            ]} />

            <div style={{ marginTop: "0.5rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.9rem 1rem", background: "var(--bg-card)", borderRadius: "10px", border: "1px solid var(--border-card)" }}>
                <Globe size={16} color="var(--text-muted)" />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "0.88rem" }}>Data Region</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>AP-East-4 · Singapore</div>
                </div>
                <Wifi size={14} color="var(--accent-cyan)" />
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", maxWidth: 900, margin: "0 auto", padding: "0 0.5rem" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            System Settings
          </h2>
          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", margin: "0.25rem 0 0" }}>
            Configure platform behaviour, security policies, and integrations
          </p>
        </div>
        <button
          onClick={handleSave}
          style={{
            display: "flex", alignItems: "center", gap: "0.5rem",
            padding: "0.6rem 1.25rem",
            background: saved ? "rgba(0,245,212,0.15)" : "var(--accent-cyan)",
            border: saved ? "1px solid var(--accent-cyan)" : "none",
            borderRadius: "8px",
            color: saved ? "var(--accent-cyan)" : "var(--bg-panel)",
            fontWeight: 700, fontSize: "0.85rem", cursor: "pointer",
            transition: "all 0.3s",
          }}
        >
          {saved ? <><CheckCircle size={15} /> Saved!</> : <><Save size={15} /> Save Changes</>}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: "1.25rem" }}>
        {/* Left nav */}
        <div style={{ background: "var(--bg-card)", borderRadius: "12px", border: "1px solid var(--border-card)", padding: "0.5rem", height: "fit-content" }}>
          {SETTINGS_TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveSection(tab.id)}
              style={{
                display: "flex", alignItems: "center", gap: "0.6rem", width: "100%",
                padding: "0.7rem 0.85rem", borderRadius: "8px", border: "none",
                background: activeSection === tab.id ? "rgba(0,245,212,0.1)" : "transparent",
                color: activeSection === tab.id ? "var(--accent-cyan)" : "var(--text-muted)",
                cursor: "pointer", textAlign: "left", fontWeight: activeSection === tab.id ? 700 : 400,
                fontSize: "0.85rem", transition: "all 0.2s", marginBottom: "0.2rem",
              }}
            >
              {tab.icon}
              {tab.label}
              {activeSection === tab.id && <ChevronRight size={13} style={{ marginLeft: "auto" }} />}
            </button>
          ))}
        </div>

        {/* Right content */}
        <div style={{ background: "var(--bg-card)", borderRadius: "12px", border: "1px solid var(--border-card)", padding: "1.5rem" }}>
          {renderContent()}

          {/* Unsaved changes warning */}
          <div style={{ marginTop: "1.5rem", paddingTop: "1rem", borderTop: "1px solid var(--border-card)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <AlertTriangle size={13} color="var(--text-muted)" />
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Changes are applied immediately after saving. Some settings require a service restart.
            </span>
            <button onClick={handleSave} style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "0.4rem", background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "0.8rem" }}>
              <RefreshCw size={12} /> Reset to Defaults
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemSettings;
