/**
 * src/constants/design.ts — Platform-wide design tokens
 *
 * Single source of truth for all colour maps used across components.
 * Import from here instead of defining inline ad-hoc colour strings.
 */

// ==============================================================================
// Severity colours (CRITICAL / WARNING / INFO)
// ==============================================================================
export const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL:  "#ef4444",   // red-500
  WARNING:   "#f59e0b",   // amber-500
  INFO:      "#06b6d4",   // cyan-500
  LOW:       "#22c55e",   // green-500
};

export const SEVERITY_BG: Record<string, string> = {
  CRITICAL: "hsla(0,   84%, 60%, 0.15)",
  WARNING:  "hsla(38,  92%, 50%, 0.15)",
  INFO:     "hsla(188, 94%, 43%, 0.15)",
  LOW:      "hsla(142, 71%, 45%, 0.15)",
};

// ==============================================================================
// Infrastructure category colours
// ==============================================================================
export const CATEGORY_COLORS: Record<string, string> = {
  POWER:                  "#f59e0b",
  TRAFFIC:                "#ef4444",
  WATER:                  "#06b6d4",
  INTERNET:               "#a855f7",
  PUBLIC_INFRASTRUCTURE:  "#22c55e",
  // lower-case aliases
  power:                  "#f59e0b",
  traffic:                "#ef4444",
  water:                  "#06b6d4",
  internet:               "#a855f7",
  public:                 "#22c55e",
};

// ==============================================================================
// Risk level colours (infrastructure health)
// ==============================================================================
export const RISK_COLORS: Record<string, string> = {
  NOMINAL:  "#22c55e",
  LOW:      "#84cc16",
  MEDIUM:   "#f59e0b",
  HIGH:     "#f97316",
  CRITICAL: "#ef4444",
};

export const RISK_BG: Record<string, string> = {
  NOMINAL:  "hsla(142, 71%, 45%, 0.15)",
  LOW:      "hsla(84,  81%, 44%, 0.15)",
  MEDIUM:   "hsla(38,  92%, 50%, 0.15)",
  HIGH:     "hsla(24,  95%, 53%, 0.15)",
  CRITICAL: "hsla(0,   84%, 60%, 0.15)",
};

// ==============================================================================
// Forecasting model colours
// ==============================================================================
export const MODEL_COLORS: Record<string, string> = {
  Prophet: "#06b6d4",   // cyan
  ARIMA:   "#a855f7",   // purple
  ETS:     "#22c55e",   // green
  Actual:  "#f59e0b",   // amber
};

// ==============================================================================
// Chart palette (general-purpose sequential colours)
// ==============================================================================
export const CHART_PALETTE = [
  "#06b6d4",  // cyan
  "#a855f7",  // purple
  "#f59e0b",  // amber
  "#22c55e",  // green
  "#ef4444",  // red
  "#3b82f6",  // blue
  "#f97316",  // orange
  "#ec4899",  // pink
];

// ==============================================================================
// Animation durations
// ==============================================================================
export const TRANSITION = {
  FAST:   "0.15s ease",
  NORMAL: "0.25s ease",
  SLOW:   "0.45s ease",
} as const;
