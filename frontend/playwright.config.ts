import { defineConfig, devices } from "@playwright/test";

/** Pruebas de punta a punta (M10, spec §14): navegador real contra el sistema levantado con
 *  `docker compose up` (Caddy en :8080). Cada corrida crea su propio negocio con `seed_demo`. */
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    locale: "es-CO",
    timezoneId: "America/Bogota",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    // En local el video necesita descargar ffmpeg; solo se graba en el CI.
    video: process.env.CI ? "retain-on-failure" : "off",
  },
  projects: [
    {
      name: "chromium",
      // PW_CHANNEL=chrome usa el Chrome instalado en el equipo, sin descargar Chromium.
      use: { ...devices["Desktop Chrome"], channel: process.env.PW_CHANNEL || undefined },
    },
  ],
});
