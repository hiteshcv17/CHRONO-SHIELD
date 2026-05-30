import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { Shield, Lock, User, Eye, EyeOff, AlertCircle, ArrowRight, Terminal } from "lucide-react";

export const Login: React.FC = () => {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<{ username?: string; password?: string }>({});

  const validateForm = (): boolean => {
    const errors: { username?: string; password?: string } = {};
    if (!username.trim()) {
      errors.username = "Username token is required";
    } else if (username.length < 3) {
      errors.username = "Username must be at least 3 characters";
    }

    if (!password) {
      errors.password = "Access credential key is required";
    } else if (password.length < 6) {
      errors.password = "Access credential key must be at least 6 characters";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    if (!validateForm()) return;

    setLoading(true);
    try {
      await login(username, password);
    } catch (err: any) {
      // Decode typical API error format
      if (err && typeof err === "object") {
        setApiError(err.message || "Decryption gateway authentication failed.");
      } else {
        setApiError("Decryption gateway authentication failed.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        width: "100vw",
        backgroundColor: "var(--bg-deep)",
        backgroundImage: `
          radial-gradient(at 0% 0%, hsla(265, 89%, 60%, 0.12) 0px, transparent 50%),
          radial-gradient(at 100% 100%, hsla(180, 100%, 45%, 0.12) 0px, transparent 50%)
        `,
        padding: "1.5rem",
        overflow: "hidden",
      }}
    >
      {/* Background cyber grid effect */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(rgba(18, 24, 38, 0.4) 1px, transparent 1px),
            linear-gradient(90deg, rgba(18, 24, 38, 0.4) 1px, transparent 1px)
          `,
          backgroundSize: "20px 20px",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      <div
        style={{
          width: "100%",
          maxWidth: "460px",
          position: "relative",
          zIndex: 1,
        }}
      >
        {/* Glow effect backdrops */}
        <div
          style={{
            position: "absolute",
            width: "300px",
            height: "300px",
            background: "radial-gradient(circle, hsla(180, 100%, 45%, 0.15) 0%, transparent 70%)",
            top: "-100px",
            left: "-100px",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            position: "absolute",
            width: "300px",
            height: "300px",
            background: "radial-gradient(circle, hsla(265, 89%, 60%, 0.15) 0%, transparent 70%)",
            bottom: "-100px",
            right: "-100px",
            pointerEvents: "none",
          }}
        />

        {/* Card */}
        <div
          className="card"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "2rem",
            padding: "2.5rem",
            border: "1px solid var(--border-card)",
            boxShadow: "0 20px 50px rgba(0, 0, 0, 0.7)",
            background: "rgba(9, 13, 24, 0.75)",
          }}
        >
          {/* Header */}
          <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: "0.75rem" }}>
            <div
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "14px",
                background: "linear-gradient(135deg, hsla(180, 100%, 45%, 0.1), hsla(265, 89%, 60%, 0.1))",
                border: "1px solid hsla(180, 100%, 45%, 0.25)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 0 25px hsla(180, 100%, 45%, 0.15)",
                marginBottom: "0.5rem",
              }}
            >
              <Shield size={28} className="text-cyan" style={{ color: "var(--accent-cyan)", filter: "drop-shadow(0 0 8px var(--accent-cyan))" }} />
            </div>
            
            <h1
              style={{
                fontSize: "1.75rem",
                fontWeight: 800,
                letterSpacing: "-0.03em",
                background: "linear-gradient(135deg, #fff 40%, var(--accent-cyan) 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              CHRONOSHIELD AI
            </h1>
            <p
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                letterSpacing: "0.2em",
                color: "var(--text-muted)",
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              Secured Decryption Gateway
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            
            {/* API Error Notification */}
            {apiError && (
              <div
                style={{
                  padding: "1rem",
                  borderRadius: "8px",
                  backgroundColor: "rgba(244, 63, 94, 0.08)",
                  border: "1px solid rgba(244, 63, 94, 0.25)",
                  display: "flex",
                  gap: "0.75rem",
                  alignItems: "flex-start",
                  color: "hsl(346, 100%, 65%)",
                  fontSize: "0.85rem",
                }}
              >
                <AlertCircle size={18} style={{ flexShrink: 0, marginTop: "0.1rem" }} />
                <div style={{ fontFamily: "var(--font-mono)" }}>{apiError}</div>
              </div>
            )}

            {/* Username Input */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <label
                style={{
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  color: "var(--text-secondary)",
                  fontFamily: "var(--font-mono)",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Operator Handle
              </label>
              <div style={{ position: "relative" }}>
                <User
                  size={18}
                  style={{
                    position: "absolute",
                    left: "12px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    color: "var(--text-muted)",
                  }}
                />
                <input
                  type="text"
                  placeholder="Enter operator handle..."
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                  style={{
                    width: "100%",
                    padding: "0.75rem 1rem 0.75rem 2.5rem",
                    background: "rgba(18, 24, 38, 0.6)",
                    border: `1px solid ${validationErrors.username ? "rgba(244, 63, 94, 0.5)" : "var(--border-card)"}`,
                    borderRadius: "8px",
                    color: "var(--text-primary)",
                    fontSize: "0.95rem",
                    fontFamily: "var(--font-sans)",
                    outline: "none",
                    transition: "var(--transition-smooth)",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "var(--accent-blue)";
                    e.target.style.boxShadow = "0 0 10px hsla(199, 89%, 48%, 0.2)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = validationErrors.username ? "rgba(244, 63, 94, 0.5)" : "var(--border-card)";
                    e.target.style.boxShadow = "none";
                  }}
                />
              </div>
              {validationErrors.username && (
                <span style={{ color: "hsl(346, 100%, 65%)", fontSize: "0.75rem", fontFamily: "var(--font-mono)" }}>
                  {validationErrors.username}
                </span>
              )}
            </div>

            {/* Password Input */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <label
                style={{
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  color: "var(--text-secondary)",
                  fontFamily: "var(--font-mono)",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Access Credential Key
              </label>
              <div style={{ position: "relative" }}>
                <Lock
                  size={18}
                  style={{
                    position: "absolute",
                    left: "12px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    color: "var(--text-muted)",
                  }}
                />
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter passcode..."
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  style={{
                    width: "100%",
                    padding: "0.75rem 2.5rem 0.75rem 2.5rem",
                    background: "rgba(18, 24, 38, 0.6)",
                    border: `1px solid ${validationErrors.password ? "rgba(244, 63, 94, 0.5)" : "var(--border-card)"}`,
                    borderRadius: "8px",
                    color: "var(--text-primary)",
                    fontSize: "0.95rem",
                    fontFamily: "var(--font-sans)",
                    outline: "none",
                    transition: "var(--transition-smooth)",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "var(--accent-blue)";
                    e.target.style.boxShadow = "0 0 10px hsla(199, 89%, 48%, 0.2)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = validationErrors.password ? "rgba(244, 63, 94, 0.5)" : "var(--border-card)";
                    e.target.style.boxShadow = "none";
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: "absolute",
                    right: "12px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "none",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {validationErrors.password && (
                <span style={{ color: "hsl(346, 100%, 65%)", fontSize: "0.75rem", fontFamily: "var(--font-mono)" }}>
                  {validationErrors.password}
                </span>
              )}
            </div>

            {/* Info notice */}
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.7rem",
                color: "var(--text-muted)",
                display: "flex",
                gap: "0.5rem",
                alignItems: "center",
                backgroundColor: "rgba(18, 24, 38, 0.4)",
                padding: "0.5rem 0.75rem",
                borderRadius: "6px",
                border: "1px solid var(--border-card)",
              }}
            >
              <Terminal size={14} style={{ color: "var(--accent-cyan)" }} />
              <span>Default system bypass keys: admin / chronoshield</span>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
              style={{
                width: "100%",
                padding: "0.85rem",
                borderRadius: "8px",
                justifyContent: "center",
                fontSize: "0.95rem",
                letterSpacing: "0.05em",
                fontFamily: "var(--font-mono)",
                textTransform: "uppercase",
                marginTop: "0.5rem",
                opacity: loading ? 0.7 : 1,
                cursor: loading ? "not-allowed" : "pointer",
                boxShadow: "0 0 15px hsla(265, 89%, 60%, 0.25)",
              }}
            >
              {loading ? (
                <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <div
                    style={{
                      width: "16px",
                      height: "16px",
                      border: "2px solid rgba(255,255,255,0.3)",
                      borderTopColor: "#fff",
                      borderRadius: "50%",
                      animation: "spin 0.8s linear infinite",
                    }}
                  />
                  Decrypting...
                </span>
              ) : (
                <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  Establish Session <ArrowRight size={16} />
                </span>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Inline styles for spinner keyframes */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
export default Login;
