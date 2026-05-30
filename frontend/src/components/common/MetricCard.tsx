/**
 * MetricCard — Reusable KPI metric display card
 *
 * Replaces repeated inline metric chips across BenchmarkDashboard,
 * InfrastructureHealth, ExplainableAI and other views.
 */
import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export type TrendDirection = "up" | "down" | "flat";

interface MetricCardProps {
  /** Metric label (e.g. "MAE", "Health Score") */
  label: string;
  /** Primary value to display */
  value: string | number;
  /** Optional unit suffix (e.g. "ms", "%", "MW") */
  unit?: string;
  /** Accent colour for the left border and value */
  color?: string;
  /** Optional trend direction — shows a small trend icon */
  trend?: TrendDirection;
  /** Whether an upward trend is positive (default) or negative */
  trendPositiveIsUp?: boolean;
  /** Optional subtitle / description below the value */
  subtitle?: string;
  /** Makes the card take up more vertical space */
  tall?: boolean;
}

const TREND_ICONS: Record<TrendDirection, React.ElementType> = {
  up:   TrendingUp,
  down: TrendingDown,
  flat: Minus,
};

function getTrendColor(
  trend: TrendDirection,
  positiveIsUp: boolean
): string {
  if (trend === "flat") return "var(--text-muted)";
  const isGood = positiveIsUp ? trend === "up" : trend === "down";
  return isGood ? "#22c55e" : "#ef4444";
}

const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  color = "var(--accent-cyan)",
  trend,
  trendPositiveIsUp = true,
  subtitle,
  tall = false,
}) => {
  const TrendIcon = trend ? TREND_ICONS[trend] : null;
  const trendColor = trend ? getTrendColor(trend, trendPositiveIsUp) : undefined;

  return (
    <div
      style={{
        padding: tall ? "1rem 1.1rem" : "0.75rem 1rem",
        background: "hsla(223, 47%, 9%, 0.7)",
        backdropFilter: "blur(12px)",
        border: "1px solid var(--border-card)",
        borderLeft: `3px solid ${color}`,
        borderRadius: "10px",
        display: "flex",
        flexDirection: "column",
        gap: "0.25rem",
        minWidth: 0,
      }}
    >
      {/* Label */}
      <span
        style={{
          fontSize: "0.7rem",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: "var(--text-muted)",
        }}
      >
        {label}
      </span>

      {/* Value row */}
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: "0.35rem",
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontSize: tall ? "1.6rem" : "1.2rem",
            fontWeight: 700,
            color,
            lineHeight: 1,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {value}
        </span>

        {unit && (
          <span
            style={{
              fontSize: "0.7rem",
              color: "var(--text-muted)",
              fontWeight: 500,
            }}
          >
            {unit}
          </span>
        )}

        {TrendIcon && (
          <TrendIcon
            size={13}
            color={trendColor}
            strokeWidth={2.5}
            style={{ marginLeft: "auto" }}
          />
        )}
      </div>

      {/* Subtitle */}
      {subtitle && (
        <span
          style={{
            fontSize: "0.7rem",
            color: "var(--text-muted)",
            lineHeight: 1.3,
          }}
        >
          {subtitle}
        </span>
      )}
    </div>
  );
};

export default MetricCard;
