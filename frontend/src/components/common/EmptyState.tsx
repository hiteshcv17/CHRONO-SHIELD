/**
 * EmptyState — Reusable empty / no-data state component
 *
 * Replaces ad-hoc empty state divs in 5+ dashboard views.
 */
import React from "react";
import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  /** Lucide icon component to display */
  icon: LucideIcon;
  /** Primary heading */
  title: string;
  /** Secondary description */
  subtitle?: string;
  /** Optional action element (e.g. a button) */
  action?: React.ReactNode;
  /** Icon size in px. Default: 40 */
  iconSize?: number;
  /** Icon colour. Default: var(--text-muted) */
  iconColor?: string;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  subtitle,
  action,
  iconSize = 40,
  iconColor = "var(--text-muted)",
}) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "0.75rem",
        padding: "3rem 1.5rem",
        flex: 1,
        textAlign: "center",
      }}
    >
      <div
        style={{
          width: iconSize * 2,
          height: iconSize * 2,
          borderRadius: "50%",
          background: "hsla(223, 47%, 9%, 0.6)",
          border: "1px solid var(--border-card)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "0.25rem",
        }}
      >
        <Icon size={iconSize} color={iconColor} strokeWidth={1.5} />
      </div>

      <p
        style={{
          margin: 0,
          fontSize: "0.95rem",
          fontWeight: 600,
          color: "var(--text-secondary)",
        }}
      >
        {title}
      </p>

      {subtitle && (
        <p
          style={{
            margin: 0,
            fontSize: "0.8rem",
            color: "var(--text-muted)",
            maxWidth: "26rem",
            lineHeight: 1.5,
          }}
        >
          {subtitle}
        </p>
      )}

      {action && <div style={{ marginTop: "0.25rem" }}>{action}</div>}
    </div>
  );
};

export default EmptyState;
