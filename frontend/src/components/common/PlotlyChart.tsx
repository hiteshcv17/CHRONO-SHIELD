import React, { useEffect, useRef, useState } from "react";
import Plot from "react-plotly.js";

interface PlotlyChartProps {
  xData: string[] | number[];
  yData: number[];
  anomalyIndices?: number[];
  title: string;
  yLabel?: string;
  metricColor?: string;
}

export const PlotlyChart: React.FC<PlotlyChartProps> = ({
  xData,
  yData,
  anomalyIndices = [],
  title,
  yLabel = "Values",
  metricColor = "#0284c7" // --accent-blue
}) => {
  const [parentWidth, setParentWidth] = useState(600);
  // Use a ref instead of getElementById so multiple instances don't collide
  const containerRef = useRef<HTMLDivElement>(null);

  // Responsive resizing handler
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        setParentWidth(containerRef.current.clientWidth);
      }
    };

    window.addEventListener("resize", handleResize);
    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  // Isolate anomaly points
  const xAnomalies = anomalyIndices.map((idx) => xData[idx]);
  const yAnomalies = anomalyIndices.map((idx) => yData[idx]);

  return (
    <div ref={containerRef} style={{ width: "100%", minHeight: "350px" }}>
      <Plot
        data={[
          // Baseline Metric Line
          {
            x: xData,
            y: yData,
            type: "scatter",
            mode: "lines",
            name: "Telemetry Feed",
            line: {
              color: metricColor,
              width: 2,
              shape: "spline"
            }
          },
          // Highlight Anomalies
          {
            x: xAnomalies,
            y: yAnomalies,
            type: "scatter",
            mode: "markers",
            name: "Anomalous Spikes",
            marker: {
              color: "#ef4444", // --status-critical
              size: 10,
              symbol: "circle",
              line: {
                color: "#ffffff",
                width: 1
              }
            }
          }
        ]}
        layout={{
          width: parentWidth - 32, // Padding offset
          height: 350,
          transition: {
            duration: 400,
            easing: "cubic-in-out"
          },
          frame: {
            duration: 400
          },
          title: {
            text: title,
            font: {
              family: "Outfit, sans-serif",
              size: 16,
              color: "#f8fafc" // --text-primary
            },
            x: 0.05
          },
          paper_bgcolor: "transparent",
          plot_bgcolor: "rgba(30, 41, 59, 0.15)", // Subtle overlay
          margin: { l: 50, r: 20, t: 60, b: 50 },
          xaxis: {
            gridcolor: "rgba(71, 85, 105, 0.15)",
            tickfont: { color: "#94a3b8", family: "Outfit, sans-serif" },
            zeroline: false
          },
          yaxis: {
            title: {
              text: yLabel,
              font: { color: "#94a3b8", family: "Outfit, sans-serif", size: 12 }
            },
            gridcolor: "rgba(71, 85, 105, 0.15)",
            tickfont: { color: "#94a3b8", family: "Outfit, sans-serif" },
            zeroline: false
          },
          legend: {
            font: { color: "#94a3b8", family: "Outfit, sans-serif" },
            orientation: "h",
            x: 0.05,
            y: -0.2
          },
          hovermode: "x unified",
          dragmode: "pan"
        }}
        config={{
          responsive: true,
          displayModeBar: false
        }}
      />
    </div>
  );
};
export default PlotlyChart;
