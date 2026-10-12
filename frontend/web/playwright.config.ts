import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90000,
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    actionTimeout: 15000,
  },
  reporter: "list",
});
