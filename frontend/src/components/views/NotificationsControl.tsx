import React, { useState, useEffect } from "react";
import { 
  Mail, 
  Send, 
  Globe, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  Clock,
  List,
  Sliders,
  BellRing
} from "lucide-react";
import { 
  getChannels, 
  updateChannel, 
  triggerTestDispatch, 
  getDeliveryLogs, 
  NotificationChannelConfigResponse, 
  NotificationDeliveryLogResponse 
} from "../../api/notification";
import { useInterval } from "../../hooks/useInterval";

export const NotificationsControl: React.FC = () => {
  const [channels, setChannels] = useState<NotificationChannelConfigResponse[]>([]);
  const [logs, setLogs] = useState<NotificationDeliveryLogResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsFilter, setLogsFilter] = useState({ channel: "ALL", status: "ALL" });

  // Fields state for edit configuration
  const [emailForm, setEmailForm] = useState({ recipient: "", host: "localhost", port: 1025, username: "", password: "", severities: ["LOW", "MEDIUM", "HIGH", "CRITICAL"] });
  const [telegramForm, setTelegramForm] = useState({ token: "", chat_id: "", severities: ["HIGH", "CRITICAL"] });
  const [webhookForm, setWebhookForm] = useState({ url: "", severities: ["MEDIUM", "HIGH", "CRITICAL"] });

  // Status flags
  const [actionMessage, setActionMessage] = useState<{ text: string; type: "success" | "error" | "" }>({ text: "", type: "" });

  const loadData = async () => {
    try {
      setLoading(true);
      const chData = await getChannels();
      setChannels(chData);

      // Parse configs into form states
      chData.forEach(ch => {
        try {
          const cfg = JSON.parse(ch.config);
          if (ch.channel_type === "EMAIL") {
            setEmailForm({
              recipient: cfg.recipient_email || "",
              host: cfg.smtp_host || "localhost",
              port: cfg.smtp_port || 1025,
              username: cfg.smtp_username || "",
              password: cfg.smtp_password || "",
              severities: cfg.allowed_severities || ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            });
          } else if (ch.channel_type === "TELEGRAM") {
            setTelegramForm({
              token: cfg.bot_token || "",
              chat_id: cfg.chat_id || "",
              severities: cfg.allowed_severities || ["HIGH", "CRITICAL"]
            });
          } else if (ch.channel_type === "WEBHOOK") {
            setWebhookForm({
              url: cfg.webhook_url || "",
              severities: cfg.allowed_severities || ["MEDIUM", "HIGH", "CRITICAL"]
            });
          }
        } catch (e) {
          console.error("Failed to parse config string", ch.channel_type);
        }
      });

      const logData = await getDeliveryLogs();
      setLogs(logData);
    } catch (e) {
      console.error("Failed to fetch notification status", e);
    } finally {
      setLoading(false);
    }
  };

  const refreshLogs = async () => {
    try {
      setLogsLoading(true);
      const logData = await getDeliveryLogs(logsFilter);
      setLogs(logData);
    } catch (e) {
      console.error("Failed to refresh delivery logs", e);
    } finally {
      setLogsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Poll logs every 5 seconds for live status updates on retries/delivery
  useInterval(() => {
    refreshLogs();
  }, 5000);

  const handleSeverityToggle = (channel: "EMAIL" | "TELEGRAM" | "WEBHOOK", severity: string) => {
    if (channel === "EMAIL") {
      setEmailForm(prev => {
        const has = prev.severities.includes(severity);
        return {
          ...prev,
          severities: has 
            ? prev.severities.filter(s => s !== severity) 
            : [...prev.severities, severity]
        };
      });
    } else if (channel === "TELEGRAM") {
      setTelegramForm(prev => {
        const has = prev.severities.includes(severity);
        return {
          ...prev,
          severities: has 
            ? prev.severities.filter(s => s !== severity) 
            : [...prev.severities, severity]
        };
      });
    } else if (channel === "WEBHOOK") {
      setWebhookForm(prev => {
        const has = prev.severities.includes(severity);
        return {
          ...prev,
          severities: has 
            ? prev.severities.filter(s => s !== severity) 
            : [...prev.severities, severity]
        };
      });
    }
  };

  const handleSaveConfig = async (channelType: "EMAIL" | "TELEGRAM" | "WEBHOOK") => {
    setActionMessage({ text: "", type: "" });
    try {
      let configObj: any = {};
      const ch = channels.find(c => c.channel_type === channelType);
      const enabled = ch ? ch.enabled : false;

      if (channelType === "EMAIL") {
        configObj = {
          recipient_email: emailForm.recipient,
          smtp_host: emailForm.host,
          smtp_port: Number(emailForm.port),
          smtp_username: emailForm.username,
          smtp_password: emailForm.password,
          allowed_severities: emailForm.severities
        };
      } else if (channelType === "TELEGRAM") {
        configObj = {
          bot_token: telegramForm.token,
          chat_id: telegramForm.chat_id,
          allowed_severities: telegramForm.severities
        };
      } else if (channelType === "WEBHOOK") {
        configObj = {
          webhook_url: webhookForm.url,
          allowed_severities: webhookForm.severities
        };
      }

      await updateChannel(channelType, {
        config: JSON.stringify(configObj),
        enabled
      });

      setActionMessage({ text: `${channelType} configuration saved successfully.`, type: "success" });
      setTimeout(() => setActionMessage({ text: "", type: "" }), 4000);
      loadData();
    } catch (err: any) {
      setActionMessage({ text: `Failed to save configuration: ${err.message || err}`, type: "error" });
    }
  };

  const handleToggleChannel = async (channelType: "EMAIL" | "TELEGRAM" | "WEBHOOK", currentStatus: boolean) => {
    try {
      await updateChannel(channelType, {
        enabled: !currentStatus
      });
      setChannels(prev => 
        prev.map(c => c.channel_type === channelType ? { ...c, enabled: !currentStatus } : c)
      );
      setActionMessage({ text: `${channelType} channel ${!currentStatus ? "enabled" : "disabled"}.`, type: "success" });
      setTimeout(() => setActionMessage({ text: "", type: "" }), 3000);
    } catch (err: any) {
      setActionMessage({ text: `Toggle operation failed: ${err.message || err}`, type: "error" });
    }
  };

  const handleSendTest = async (channelType: "EMAIL" | "TELEGRAM" | "WEBHOOK") => {
    setActionMessage({ text: "", type: "" });
    try {
      let recipient = "";
      if (channelType === "EMAIL") recipient = emailForm.recipient;
      else if (channelType === "TELEGRAM") recipient = telegramForm.chat_id;
      else if (channelType === "WEBHOOK") recipient = webhookForm.url;

      if (!recipient) {
        setActionMessage({ text: `Please fill in the recipient details for ${channelType} first.`, type: "error" });
        return;
      }

      await triggerTestDispatch(channelType, {
        channel: channelType,
        recipient,
        message: `ChronoShield AI dynamic testing dispatch at ${new Date().toLocaleTimeString()}.`
      });

      setActionMessage({ text: `Test packet dispatched to ${channelType} transport.`, type: "success" });
      setTimeout(() => setActionMessage({ text: "", type: "" }), 4000);
      refreshLogs();
    } catch (err: any) {
      setActionMessage({ text: `Test dispatch failed: ${err.message || err}`, type: "error" });
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* View Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2>Notification Delivery Control</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Configure and audit multi-channel automated alert delivery pipelines.
          </p>
        </div>
        <button 
          onClick={loadData} 
          className="btn btn-secondary" 
          style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
        >
          <RefreshCw size={16} />
          Reload Panel
        </button>
      </div>

      {actionMessage.text && (
        <div 
          style={{
            padding: "1rem",
            borderRadius: "8px",
            border: `1px solid ${actionMessage.type === "success" ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
            background: actionMessage.type === "success" ? "rgba(16, 185, 129, 0.08)" : "rgba(239, 68, 68, 0.08)",
            color: actionMessage.type === "success" ? "var(--status-nominal)" : "var(--status-critical)",
            fontSize: "0.9rem",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem"
          }}
        >
          {actionMessage.type === "success" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{actionMessage.text}</span>
        </div>
      )}

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "4rem" }}>
          <RefreshCw size={36} className="spin" color="var(--accent-cyan)" />
        </div>
      ) : (
        <div className="dashboard-grid">
          {/* Left Column: Configuration Cards */}
          <div className="col-6" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            
            {/* EMAIL Config */}
            {channels.some(c => c.channel_type === "EMAIL") && (
              (() => {
                const ch = channels.find(c => c.channel_type === "EMAIL")!;
                return (
                  <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <Mail size={20} color="var(--accent-blue)" />
                        SMTP Email Channel
                      </h3>
                      <div className="switch-container" onClick={() => handleToggleChannel("EMAIL", ch.enabled)}>
                        <div className={`switch ${ch.enabled ? "active" : ""}`} />
                        <span style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                          {ch.enabled ? "ACTIVE" : "INACTIVE"}
                        </span>
                      </div>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                        <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Recipient Email</label>
                        <input 
                          type="email" 
                          className="search-input" 
                          placeholder="e.g. operators@chronoshield.ai"
                          value={emailForm.recipient}
                          onChange={(e) => setEmailForm(prev => ({ ...prev, recipient: e.target.value }))}
                        />
                      </div>

                      <div style={{ display: "flex", gap: "1rem" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", flex: 1 }}>
                          <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>SMTP Host</label>
                          <input 
                            type="text" 
                            className="search-input"
                            value={emailForm.host}
                            onChange={(e) => setEmailForm(prev => ({ ...prev, host: e.target.value }))}
                          />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", width: "100px" }}>
                          <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Port</label>
                          <input 
                            type="number" 
                            className="search-input"
                            value={emailForm.port}
                            onChange={(e) => setEmailForm(prev => ({ ...prev, port: Number(e.target.value) }))}
                          />
                        </div>
                      </div>

                      <div style={{ display: "flex", gap: "1rem" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", flex: 1 }}>
                          <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>SMTP Username (Optional)</label>
                          <input 
                            type="text" 
                            className="search-input"
                            placeholder="e.g. operators@gmail.com"
                            value={emailForm.username}
                            onChange={(e) => setEmailForm(prev => ({ ...prev, username: e.target.value }))}
                          />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", flex: 1 }}>
                          <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>SMTP Password (Optional)</label>
                          <input 
                            type="password" 
                            className="search-input"
                            placeholder="App Password / Secret"
                            value={emailForm.password}
                            onChange={(e) => setEmailForm(prev => ({ ...prev, password: e.target.value }))}
                          />
                        </div>
                      </div>

                      {/* Severities selection */}
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                        <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Allowed Severity Triggers</label>
                        <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.25rem" }}>
                          {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map(s => (
                            <button
                              key={s}
                              onClick={() => handleSeverityToggle("EMAIL", s)}
                              style={{
                                padding: "0.35rem 0.65rem",
                                borderRadius: "6px",
                                border: emailForm.severities.includes(s) ? "1px solid var(--accent-blue)" : "1px solid var(--border-card)",
                                background: emailForm.severities.includes(s) ? "rgba(59, 130, 246, 0.15)" : "transparent",
                                color: emailForm.severities.includes(s) ? "var(--text-primary)" : "var(--text-muted)",
                                fontSize: "0.75rem",
                                cursor: "pointer"
                              }}
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem" }}>
                      <button onClick={() => handleSaveConfig("EMAIL")} className="btn btn-secondary" style={{ flex: 1 }}>Save Config</button>
                      <button onClick={() => handleSendTest("EMAIL")} className="btn btn-primary" style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                        <Send size={14} />
                        Test
                      </button>
                    </div>
                  </div>
                );
              })()
            )}

            {/* TELEGRAM Config */}
            {channels.some(c => c.channel_type === "TELEGRAM") && (
              (() => {
                const ch = channels.find(c => c.channel_type === "TELEGRAM")!;
                return (
                  <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <BellRing size={20} color="var(--accent-purple)" />
                        Telegram Bot Integration
                      </h3>
                      <div className="switch-container" onClick={() => handleToggleChannel("TELEGRAM", ch.enabled)}>
                        <div className={`switch ${ch.enabled ? "active" : ""}`} />
                        <span style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                          {ch.enabled ? "ACTIVE" : "INACTIVE"}
                        </span>
                      </div>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                        <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Bot HTTP API Token</label>
                        <input 
                          type="password" 
                          className="search-input" 
                          placeholder="e.g. 123456:ABC-DEF..."
                          value={telegramForm.token}
                          onChange={(e) => setTelegramForm(prev => ({ ...prev, token: e.target.value }))}
                        />
                      </div>

                      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                        <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Target Chat / Channel ID</label>
                        <input 
                          type="text" 
                          className="search-input" 
                          placeholder="e.g. -10019284759"
                          value={telegramForm.chat_id}
                          onChange={(e) => setTelegramForm(prev => ({ ...prev, chat_id: e.target.value }))}
                        />
                      </div>

                      {/* Severities selection */}
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                        <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Allowed Severity Triggers</label>
                        <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.25rem" }}>
                          {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map(s => (
                            <button
                              key={s}
                              onClick={() => handleSeverityToggle("TELEGRAM", s)}
                              style={{
                                padding: "0.35rem 0.65rem",
                                borderRadius: "6px",
                                border: telegramForm.severities.includes(s) ? "1px solid var(--accent-purple)" : "1px solid var(--border-card)",
                                background: telegramForm.severities.includes(s) ? "rgba(168, 85, 247, 0.15)" : "transparent",
                                color: telegramForm.severities.includes(s) ? "var(--text-primary)" : "var(--text-muted)",
                                fontSize: "0.75rem",
                                cursor: "pointer"
                              }}
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem" }}>
                      <button onClick={() => handleSaveConfig("TELEGRAM")} className="btn btn-secondary" style={{ flex: 1 }}>Save Config</button>
                      <button onClick={() => handleSendTest("TELEGRAM")} className="btn btn-primary" style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                        <Send size={14} />
                        Test
                      </button>
                    </div>
                  </div>
                );
              })()
            )}

            {/* WEBHOOK Config */}
            {channels.some(c => c.channel_type === "WEBHOOK") && (
              (() => {
                const ch = channels.find(c => c.channel_type === "WEBHOOK")!;
                return (
                  <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <Globe size={20} color="var(--accent-cyan)" />
                        Custom Outbound Webhooks
                      </h3>
                      <div className="switch-container" onClick={() => handleToggleChannel("WEBHOOK", ch.enabled)}>
                        <div className={`switch ${ch.enabled ? "active" : ""}`} />
                        <span style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                          {ch.enabled ? "ACTIVE" : "INACTIVE"}
                        </span>
                      </div>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                        <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Webhook Destination Endpoint</label>
                        <input 
                          type="url" 
                          className="search-input" 
                          placeholder="e.g. https://your-server.com/api/v1/alert-receiver"
                          value={webhookForm.url}
                          onChange={(e) => setWebhookForm(prev => ({ ...prev, url: e.target.value }))}
                        />
                      </div>

                      {/* Severities selection */}
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                        <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Allowed Severity Triggers</label>
                        <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.25rem" }}>
                          {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map(s => (
                            <button
                              key={s}
                              onClick={() => handleSeverityToggle("WEBHOOK", s)}
                              style={{
                                padding: "0.35rem 0.65rem",
                                borderRadius: "6px",
                                border: webhookForm.severities.includes(s) ? "1px solid var(--accent-cyan)" : "1px solid var(--border-card)",
                                background: webhookForm.severities.includes(s) ? "rgba(6, 182, 212, 0.15)" : "transparent",
                                color: webhookForm.severities.includes(s) ? "var(--text-primary)" : "var(--text-muted)",
                                fontSize: "0.75rem",
                                cursor: "pointer"
                              }}
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem" }}>
                      <button onClick={() => handleSaveConfig("WEBHOOK")} className="btn btn-secondary" style={{ flex: 1 }}>Save Config</button>
                      <button onClick={() => handleSendTest("WEBHOOK")} className="btn btn-primary" style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                        <Send size={14} />
                        Test
                      </button>
                    </div>
                  </div>
                );
              })()
            )}

          </div>

          {/* Right Column: Historical Logs & Retry Audits */}
          <div className="card col-6" style={{ display: "flex", flexDirection: "column", gap: "1rem", minHeight: "600px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <List size={18} color="var(--accent-cyan)" />
                Notification Delivery Audit logs
              </h3>
              <button 
                onClick={refreshLogs} 
                disabled={logsLoading}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)" }}
              >
                <RefreshCw size={16} className={logsLoading ? "spin" : ""} />
              </button>
            </div>

            {/* Filter controls */}
            <div style={{ display: "flex", gap: "1rem", background: "rgba(30, 41, 59, 0.15)", padding: "0.75rem", borderRadius: "8px", border: "1px solid var(--border-card)" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", flex: 1 }}>
                <label style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Channel</label>
                <select 
                  className="select-dropdown" 
                  value={logsFilter.channel}
                  onChange={(e) => setLogsFilter(prev => ({ ...prev, channel: e.target.value }))}
                  style={{ width: "100%", padding: "0.25rem" }}
                >
                  <option value="ALL">All Channels</option>
                  <option value="EMAIL">Email</option>
                  <option value="TELEGRAM">Telegram</option>
                  <option value="WEBHOOK">Webhooks</option>
                </select>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", flex: 1 }}>
                <label style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Delivery Status</label>
                <select 
                  className="select-dropdown"
                  value={logsFilter.status}
                  onChange={(e) => setLogsFilter(prev => ({ ...prev, status: e.target.value }))}
                  style={{ width: "100%", padding: "0.25rem" }}
                >
                  <option value="ALL">All Statuses</option>
                  <option value="PENDING">Pending</option>
                  <option value="SENT">Sent</option>
                  <option value="FAILED">Failed</option>
                </select>
              </div>

              <button 
                onClick={refreshLogs}
                className="btn btn-secondary" 
                style={{ alignSelf: "flex-end", padding: "0.35rem 0.75rem", fontSize: "0.8rem", height: "32px", display: "flex", alignItems: "center", gap: "0.25rem" }}
              >
                <Sliders size={12} />
                Apply
              </button>
            </div>

            {/* Logs List */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", overflowY: "auto", flex: 1, maxHeight: "500px", paddingRight: "0.25rem" }}>
              {logs.length === 0 ? (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)", fontSize: "0.9rem", minHeight: "200px" }}>
                  No delivery logs matching filters.
                </div>
              ) : (
                logs.map((log) => {
                  const statusColor = 
                    log.status === "SENT" ? "var(--status-nominal)" : 
                    log.status === "PENDING" ? "var(--status-warning)" : 
                    "var(--status-critical)";
                  const channelColor = 
                    log.channel === "EMAIL" ? "var(--accent-blue)" : 
                    log.channel === "TELEGRAM" ? "var(--accent-purple)" : 
                    "var(--accent-cyan)";

                  return (
                    <div 
                      key={log.id}
                      style={{
                        background: "rgba(18, 24, 38, 0.4)",
                        border: "1px solid var(--border-card)",
                        borderRadius: "8px",
                        padding: "0.75rem",
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.5rem"
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span 
                          className="badge" 
                          style={{ 
                            background: `rgba(${log.channel === "EMAIL" ? "59, 130, 246" : log.channel === "TELEGRAM" ? "168, 85, 247" : "6, 182, 212"}, 0.12)`, 
                            color: channelColor,
                            border: `1px solid rgba(${log.channel === "EMAIL" ? "59, 130, 246" : log.channel === "TELEGRAM" ? "168, 85, 247" : "6, 182, 212"}, 0.25)` 
                          }}
                        >
                          {log.channel}
                        </span>
                        
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                            <Clock size={12} />
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                          <span 
                            className="badge" 
                            style={{ 
                              background: `rgba(${log.status === "SENT" ? "16, 185, 129" : log.status === "PENDING" ? "245, 158, 11" : "239, 68, 68"}, 0.12)`, 
                              color: statusColor,
                              border: `1px solid rgba(${log.status === "SENT" ? "16, 185, 129" : log.status === "PENDING" ? "245, 158, 11" : "239, 68, 68"}, 0.25)`
                            }}
                          >
                            {log.status}
                          </span>
                        </div>
                      </div>

                      <div style={{ display: "flex", flexDirection: "column" }}>
                        <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>{log.title}</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)", marginTop: "0.15rem", wordBreak: "break-all" }}>
                          Dest: {log.recipient}
                        </span>
                      </div>

                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem", borderTop: "1px dashed var(--border-card)", paddingTop: "0.4rem", marginTop: "0.15rem" }}>
                        <span style={{ color: "var(--text-secondary)" }}>
                          Retries: <strong style={{ color: log.retry_count > 0 ? "var(--status-warning)" : "var(--text-primary)" }}>{log.retry_count}</strong> / {log.max_retries}
                        </span>
                        {log.alert_id && (
                          <span style={{ color: "var(--text-muted)" }}>AlertRef: {log.alert_id.slice(0, 12)}</span>
                        )}
                      </div>

                      {log.error_message && (
                        <div 
                          style={{ 
                            fontSize: "0.75rem", 
                            color: "var(--status-critical)", 
                            background: "rgba(239, 68, 68, 0.08)", 
                            padding: "0.4rem", 
                            borderRadius: "4px",
                            borderLeft: "2px solid var(--status-critical)",
                            fontFamily: "var(--font-mono)",
                            wordBreak: "break-word"
                          }}
                        >
                          Error: {log.error_message}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationsControl;
