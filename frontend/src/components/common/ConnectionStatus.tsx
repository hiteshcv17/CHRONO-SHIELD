import React from "react";
import { Wifi, WifiOff, RefreshCw, Clock } from "lucide-react";
import { useApiStatus } from "../../hooks/useApiStatus";

interface ConnectionStatusProps {
  compact?: boolean;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  compact = false,
}) => {
  const { connected, latencyMs, version, lastChecked, checking, refresh } =
    useApiStatus();

  const formattedTime = lastChecked
    ? lastChecked.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
    : "—";

  if (compact) {
    // Minimal variant for use in TopBar
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          fontSize: "0.85rem",
        }}
      >
        {/* Animated connection dot */}
        <span
          className={`pulse-indicator ${connected ? "" : "critical"}`}
          style={
            checking
              ? { animation: "none", opacity: 0.5 }
              : {}
          }
        />

        {connected ? (
          <>
            <Wifi size={15} color="var(--status-safe)" />
            <span style={{ color: "var(--status-safe)", fontWeight: 600 }}>
              API Connected
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                background: "rgba(16, 185, 129, 0.12)",
                color: "var(--status-safe)",
                padding: "0.15rem 0.5rem",
                borderRadius: "4px",
                border: "1px solid rgba(16, 185, 129, 0.25)",
              }}
            >
              {latencyMs}ms
            </span>
            {version && (
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.72rem",
                  color: "var(--text-muted)",
                }}
              >
                v{version}
              </span>
            )}
          </>
        ) : (
          <>
            <WifiOff size={15} color="var(--status-critical)" />
            <span style={{ color: "var(--status-critical)", fontWeight: 600 }}>
              {checking ? "Checking..." : "API Offline"}
            </span>
          </>
        )}

        {/* Manual refresh trigger */}
        <button
          onClick={refresh}
          disabled={checking}
          title="Refresh connection check"
          style={{
            background: "transparent",
            border: "none",
            color: "var(--text-muted)",
            cursor: checking ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            padding: "0",
          }}
        >
          <RefreshCw
            size={13}
            style={checking ? { animation: "spin 1s linear infinite" } : {}}
          />
        </button>

        <style>{`
          @keyframes spin { 100% { transform: rotate(360deg); } }
        `}</style>
      </div>
    );
  }

  // Expanded variant (for a dedicated panel)
  return (
    <div
      className="card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
        borderColor: connected
          ? "rgba(16, 185, 129, 0.25)"
          : "rgba(239, 68, 68, 0.25)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h3 style={{ fontSize: "1rem" }}>Backend Connection</h3>
        <span className={`badge ${connected ? "badge-safe" : "badge-critical"}`}>
          {checking ? "Checking..." : connected ? "ONLINE" : "OFFLINE"}
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
        <Row label="Status">
          <span style={{ color: connected ? "var(--status-safe)" : "var(--status-critical)", fontWeight: 600 }}>
            {connected ? "✓ Healthy" : "✗ Unreachable"}
          </span>
        </Row>
        <Row label="Latency">
          <span style={{ fontFamily: "var(--font-mono)" }}>
            {connected ? `${latencyMs} ms` : "—"}
          </span>
        </Row>
        <Row label="Version">
          <span style={{ fontFamily: "var(--font-mono)" }}>
            {version ?? "—"}
          </span>
        </Row>
        <Row label="Last Checked">
          <span
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.82rem",
            }}
          >
            <Clock size={13} />
            {formattedTime}
          </span>
        </Row>
      </div>

      <button
        className="btn-secondary"
        onClick={refresh}
        disabled={checking}
        style={{ width: "100%", justifyContent: "center" }}
      >
        <RefreshCw
          size={14}
          style={checking ? { animation: "spin 1s linear infinite" } : {}}
        />
        {checking ? "Checking..." : "Re-check Connection"}
      </button>

      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

// Helper sub-component
const Row: React.FC<{ label: string; children: React.ReactNode }> = ({
  label,
  children,
}) => (
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "0.4rem 0",
      borderBottom: "1px solid var(--border-card)",
      fontSize: "0.875rem",
    }}
  >
    <span style={{ color: "var(--text-muted)" }}>{label}</span>
    <span style={{ color: "var(--text-primary)" }}>{children}</span>
  </div>
);

export default ConnectionStatus;
