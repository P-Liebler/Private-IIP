import { test, expect } from "@playwright/test";
const username = process.env.E2E_USERNAME;
const password = process.env.E2E_PASSWORD;
const universe = process.env.E2E_P6_UNIVERSE_ID;
const unverified = process.env.E2E_P6_UNVERIFIED_UNIVERSE_ID;
const benchmark = process.env.E2E_P6_BENCHMARK_ID;

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("Benutzername").fill(username!);
  await page.getByLabel("Passwort").fill(password!);
  await page.getByRole("button", { name: "Anmelden" }).click();
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 30000 });
  await page.goto("/backtests");
}
async function build(page: import("@playwright/test").Page, id: string) {
  await page.getByRole("combobox", { name: "Universe", exact: true }).selectOption(id);
  await page.getByLabel("Start", { exact: true }).fill("2024-01-02");
  await page.getByLabel("Ende", { exact: true }).fill("2024-01-05");
  await page.getByLabel("Benchmark Instrument ID").fill(benchmark!);
  await page.getByLabel("Basiswährung").selectOption("USD");
  await page.getByRole("button", { name: "Dataset bauen", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Dataset:" })).toBeVisible({ timeout: 60000 });
}
test("synthetic PIT baseline run has independently expected metrics and fill provenance", async ({ page }) => {
  test.skip(!username || !password || !universe || !benchmark, "Explicit local synthetic P6 fixture required");
  await login(page); await build(page, universe!);
  await expect(page.getByRole("status").filter({ hasText: "Dataset:" })).toContainText("4 gültig, 0 ausgeschlossen");
  await page.getByLabel("Startkapital").fill("1000");
  await page.getByLabel("Kommission").fill("1");
  await page.getByLabel("Spread bps").fill("0");
  await page.getByLabel("Slippage bps").fill("0");
  await expect(page.getByRole("button", { name: "Backtest starten" })).toBeEnabled({ timeout: 45000 });
  await page.getByRole("button", { name: "Backtest starten" }).click();
  await expect(page.getByRole("heading", { name: "Ergebnis: STRICT_PIT_VALID" })).toBeVisible();
  const row = page.getByRole("row").filter({ has: page.getByRole("cell", { name: "Total Return", exact: true }) });
  await expect(row.getByRole("cell").nth(1)).toHaveText(/^0\.0989(?:0*)$/);
  await expect(page.getByRole("img", { name: "Equity curve" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "BUY", exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "2024-01-03T14:30:00+00:00", exact: true })).toBeVisible();
});
test("unverified historical membership cannot pass STRICT_PIT", async ({ page }) => {
  test.skip(!username || !password || !unverified || !benchmark, "Explicit unverified P6 fixture required");
  await login(page); await build(page, unverified!);
  await expect(page.getByRole("status").filter({ hasText: "Dataset:" })).toContainText("0 gültig");
  await page.getByRole("button", { name: "Backtest starten" }).click();
  await expect(page.getByRole("heading", { name: "Ergebnis: REJECTED" })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "HISTORICAL_AVAILABILITY_UNVERIFIED" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "BUY", exact: true })).toHaveCount(0);
});
