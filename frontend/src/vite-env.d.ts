/// <reference types="vite/client" />

// Declare missing types for react-plotly.js (no official @types package)
// Using loose any-based signature to avoid conflicts with plotly.js strict generics
declare module "react-plotly.js" {
  import * as React from "react";

  interface PlotParams {
    data?: any[];
    layout?: Record<string, any>;
    config?: Record<string, any>;
    frames?: any[];
    style?: React.CSSProperties;
    className?: string;
    useResizeHandler?: boolean;
    revision?: number;
    divId?: string;
    debug?: boolean;
    onInitialized?: (figure: any, graphDiv: HTMLElement) => void;
    onUpdate?: (figure: any, graphDiv: HTMLElement) => void;
    onPurge?: (figure: any, graphDiv: HTMLElement) => void;
    onError?: (err: Error) => void;
    onAfterPlot?: () => void;
    onClick?: (event: any) => void;
    onHover?: (event: any) => void;
    onRelayout?: (event: any) => void;
    onRestyle?: (event: any) => void;
    onSelected?: (event: any) => void;
    onLegendClick?: (event: any) => boolean;
    onLegendDoubleClick?: (event: any) => boolean;
    [key: string]: any;
  }

  class Plot extends React.Component<PlotParams> {}
  export default Plot;
}

// Declare leaflet.heat module (no official types)
declare module "leaflet.heat" {
  export {};
}
