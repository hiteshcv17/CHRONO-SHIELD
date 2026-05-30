import React, { Component, ErrorInfo } from "react";
import { AlertOctagon, RefreshCw } from "lucide-react";

interface Props {
  children: React.ReactNode;
  /** Optional label for which view errored — shown in the fallback */
  viewLabel?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary] Render error caught:", error, info);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    const { viewLabel = "this view" } = this.props;

    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "300px",
          gap: "1.5rem",
          padding: "2rem",
        }}
      >
        <div
          className="card"
          style={{
            maxWidth: "480px",
            width: "100%",
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "1rem",
            borderColor: "rgba(239, 68, 68, 0.3)",
          }}
        >
          <div
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "50%",
              background: "rgba(239, 68, 68, 0.1)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <AlertOctagon size={28} color="var(--status-critical)" />
          </div>

          <div>
            <h3 style={{ marginBottom: "0.5rem" }}>Render Error in {viewLabel}</h3>
            <p style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
              An unexpected client-side error occurred while rendering this panel.
              Your data is safe — try reloading the view.
            </p>
          </div>

          {this.state.error && (
            <code
              style={{
                fontSize: "0.75rem",
                background: "rgba(239, 68, 68, 0.06)",
                border: "1px solid rgba(239, 68, 68, 0.2)",
                padding: "0.5rem 1rem",
                borderRadius: "6px",
                color: "var(--status-critical)",
                maxWidth: "100%",
                overflowX: "auto",
                display: "block",
                textAlign: "left",
              }}
            >
              {this.state.error.message}
            </code>
          )}

          <button className="btn-secondary" onClick={this.handleRetry}>
            <RefreshCw size={15} />
            Retry View
          </button>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
