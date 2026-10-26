import { test, expect } from "@playwright/test";

test("PR3 system status keeps operator and financial gates explicit", async ({ page }) => {
  test.skip(!process.env.E2E_USERNAME || !process.env.E2E_PASSWORD, "Explicit local fixture required");
  await page.goto("/login");
  await page.getByLabel("Benutzername", { exact: true }).fill(process.env.E2E_USERNAME!);
  await page.getByLabel("Passwort", { exact: true }).fill(process.env.E2E_PASSWORD!);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await page.waitForURL("**/dashboard", { timeout: 30000 });
  await page.goto("/system/status");
  if (process.env.E2E_OPERATIONS_OPERATOR === "true") {
    await expect(page.getByRole("heading", { name: "Systemstatus", exact: true })).toBeVisible();
    await expect(page.getByText(/Letztes erfolgreiches Backup:/)).toBeVisible();
    await expect(page.getByText("PRIVATE_CORE_DEPLOYMENT_NOT_VERIFIED", { exact: true })).toBeVisible();
    await expect(page.getByText("FORECASTS_SHADOW_ONLY", { exact: true })).toBeVisible();
    await expect(page.getByText("independent_backup: NOT_VERIFIED", { exact: true })).toBeVisible();
    await expect(page.getByText("RECOMMENDATIONS_GATED", { exact: true })).toBeVisible();
  } else {
    await expect(page.getByRole("heading", { name: "Dieser Bereich ist für Betreiberpersonen vorgesehen", exact: true })).toBeVisible();
    await expect(page.getByText("Dienste", { exact: true })).toHaveCount(0);
  }
});
