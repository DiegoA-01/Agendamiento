import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // Detrás de Caddy el Host cambia; permitimos cualquiera en desarrollo.
    allowedHosts: true,
    // En Docker sobre Windows la carpeta compartida no avisa los cambios de archivos: sin polling
    // el navegador seguiría viendo código viejo. Docker Compose lo activa con VITE_USE_POLLING=1.
    watch: process.env.VITE_USE_POLLING === "1" ? { usePolling: true, interval: 300 } : undefined,
    proxy: {
      "/api": apiTarget,
      "/healthz": apiTarget,
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
