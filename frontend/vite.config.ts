import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // Fix react-plotly.js CJS shim resolution in Vite
      "plotly.js/dist/plotly": "plotly.js-dist-min",
    },
  },
  optimizeDeps: {
    include: ["plotly.js-dist-min", "react-plotly.js"],
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    watch: {
      usePolling: true,
    },
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/health": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/version": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/status": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    minify: "esbuild",
    chunkSizeWarningLimit: 1600,
  },
});

