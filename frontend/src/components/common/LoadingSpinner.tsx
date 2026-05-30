/**
 * LoadingSpinner — Reusable sci-fi themed loading indicator
 *
 * Replaces 8+ ad-hoc inline spinner implementations across views.
 */
import React from "react";

interface LoadingSpinnerProps {
  /** Diameter in px. Default: 40 */
  size?: number;
  /** Optional label below the spinner */
  label?: string;
  /** If true, centres the spinner in a flex column container. Default: true */
  centered?: boolean;
  /** Override spinner colour (CSS colour string). Default: var(--accent-cyan) */
  color?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 40,
  label,
  centered = true,
  color = "var(--accent-cyan)",
}) => {
  const stroke = Math.max(2, size / 14);
  const r = (size - stroke * 2) / 2;
  const circ = 2 * Math.PI * r;

  const spinner = (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "0.5rem",
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ animation: "spin 1s linear infinite" }}
        aria-hidden="true"
      >
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          opacity={0.15}
        />
        {/* Arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={`${circ * 0.72} ${circ * 0.28}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>

      {label && (
        <span
          style={{
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            letterSpacing: "0.05em",
          }}
        >
          {label}
        </span>
      )}

      {/* Reuse existing global keyframe or define inline */}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  if (!centered) return spinner;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flex: 1,
        padding: "2rem",
      }}
    >
      {spinner}
    </div>
  );
};

export default LoadingSpinner;
