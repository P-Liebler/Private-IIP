import { test, expect } from "@playwright/test";

const username = process.env.E2E_USERNAME;
const password = process.env.E2E_PASSWORD;
const dataset = process.env.E2E_DATASET_ID;

test.beforeEach(async ({ page }) => {
  test.skip(!username || !password, "Explicit local fixture required");
  await page.goto("/login");
  await page.getByLabel("Benutzername", { exact: true }).fill(username!);
  await page.getByLabel("Passwort", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await page.waitForURL("**/dashboard", { timeout: 30000 });
});

test("PR2 readiness exposes source prerequisites without granting rights", async ({ page }) => {
  await page.goto("/data-operations/readiness");
  await expect(page.getByRole("heading", { name: "Real Data Readiness", exact: true })).toBeVisible();
  await expect(page.getByText(/LIVE_SMOKE_BLOCKED_SOURCE_NOT_APPROVED/).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /ECB/ })).toContainText("Deaktiviert");
});

test("PR2 archived synthetic dataset explains real-data blockers", async ({ page }) => {
  test.setTimeout(120000);
  await page.goto("/data-operations/readiness");
  const selector = page.getByLabel("Gepinntes Dataset", { exact: true });
  await expect(selector.locator("option").nth(1)).toBeAttached();
  const identifier = dataset ?? await selector.locator("option").nth(1).getAttribute("value");
  expect(identifier).toBeTruthy();
  await selector.selectOption(identifier!);
  await page.getByRole("button", { name: "Readiness-Audit ausführen", exact: true }).click();
  await expect(page.locator("pre").filter({ hasText: "SYNTHETIC_OR_UNVERIFIED_INPUTS" }).first()).toBeVisible({ timeout: 90000 });
  await expect(page.locator("pre").filter({ hasText: '"eligible_oos_samples": null' }).first()).toBeVisible();
});

test("PR2 model comparison requires untouched chronological windows", async ({ page }) => {
  await page.goto("/models/validation");
  await expect(page.getByRole("heading", { name: "Model comparison", exact: true })).toBeVisible();
  await expect(page.getByText(/Bereits verwendete finale Fenster bleiben gesperrt/)).toBeVisible();
  await expect(page.getByText(/BLOCKED_BY_REAL_DATA/).first()).toBeVisible();
});

test("PR2 forward history is experimental and does not invent metrics", async ({ page }) => {
  await page.goto("/models/forward-validation");
  await expect(page.getByRole("heading", { name: "Forward Shadow History", exact: true })).toBeVisible();
  await expect(page.getByText(/FORWARD_ARCHIVED_SHADOW/).first()).toBeVisible();
  await expect(page.getByText(/INSUFFICIENT_MATURED_HISTORY/).first()).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Forward-Historie" })).toBeVisible();
});

test("PR2 strategy evaluation keeps V3 recommendations gated", async ({ page }) => {
  await page.goto("/recommendations/validation");
  await expect(page.getByRole("heading", { name: "Strategy evaluation", exact: true })).toBeVisible();
  await expect(page.getByText("V3 RECOMMENDATIONS GATED", { exact: true })).toBeVisible();
  await expect(page.getByText(/RESEARCH_BACKTEST und ARCHIVED_FORWARD_EVALUATION/)).toBeVisible();
});
