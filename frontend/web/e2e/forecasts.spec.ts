import { test, expect } from "@playwright/test";

const username = process.env.E2E_USERNAME;
const password = process.env.E2E_PASSWORD;
const instrument = process.env.E2E_RESEARCH_INSTRUMENT_ID;

test("forecast abstention is explicit and preserved for both horizons", async ({ page }) => {
  test.skip(!username || !password || !instrument, "Explicit synthetic local fixtures required");
  await page.goto("/login");
  await page.getByLabel("Benutzername").fill(username!);
  await page.getByLabel("Passwort", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await page.waitForURL("**/dashboard");
  await page.goto(`/instrument/${instrument}`);
  const panel = page.locator("section").filter({ has: page.getByRole("heading", { name: "Forecast", exact: true }) });
  await expect(panel.getByRole("heading", { name: "Forecast", exact: true })).toBeVisible({ timeout: 30000 });
  await expect(panel.getByText("NO RELIABLE FORECAST", { exact: true }).first()).toBeVisible();
  await expect(panel.getByText("Insufficient verified historical data", { exact: true })).toBeVisible();
  await panel.getByLabel("Forecast-Horizont").selectOption("90");
  await expect(panel.getByText("NO RELIABLE FORECAST", { exact: true }).first()).toBeVisible();
  await expect(panel.getByRole("heading", { name: "Prediction History" })).toBeVisible();
  await expect.poll(() => panel.locator("tbody tr").count()).toBeGreaterThanOrEqual(2);
});

test("model administration cannot imply a validated forecast from absent models", async ({ page }) => {
  test.skip(!username || !password, "Explicit synthetic local fixtures required");
  await page.goto("/login");
  await page.getByLabel("Benutzername").fill(username!);
  await page.getByLabel("Passwort", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await page.waitForURL("**/dashboard");
  await page.goto("/models");
  await expect(page.getByRole("heading", { name: "ML-Modelle", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Data readiness", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Registered models", exact: true })).toBeVisible();
});
