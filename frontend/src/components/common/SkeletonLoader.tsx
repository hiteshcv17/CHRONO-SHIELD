import React from "react";

interface SkeletonLoaderProps {
  variant?: "card" | "chart" | "table-row" | "text-line";
  height?: string;
  width?: string;
  count?: number;
}

export const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  variant = "card",
  height,
  width = "100%",
  count = 1
}) => {
  const getStyle = (): React.CSSProperties => {
    const baseStyle: React.CSSProperties = { width };
    if (height) {
      baseStyle.height = height;
      return baseStyle;
    }

    switch (variant) {
      case "card":
        baseStyle.height = "120px";
        break;
      case "chart":
        baseStyle.height = "350px";
        break;
      case "table-row":
        baseStyle.height = "48px";
        break;
      case "text-line":
        baseStyle.height = "16px";
        break;
    }
    return baseStyle;
  };

  const renderSingle = (index: number) => {
    const classes = `skeleton-shimmer`;
    const style = getStyle();

    // Adjust margins for repeating elements
    const margin = variant === "table-row" || variant === "text-line" ? "0.5rem 0" : "0";

    return (
      <div
        key={index}
        className={classes}
        style={{ ...style, margin, borderRadius: variant === "text-line" ? "4px" : "12px" }}
      />
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", width }}>
      {Array.from({ length: count }).map((_, i) => renderSingle(i))}
    </div>
  );
};

export default SkeletonLoader;
