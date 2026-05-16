import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_TARGET = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/auth": API_TARGET,
      "/me": API_TARGET,
      "/batches": API_TARGET,
      "/predictions": API_TARGET,
      "/admin": API_TARGET,
      "/demo": API_TARGET,
      "/healthz": API_TARGET,
    },
  },
});
