import { test, expect } from "@playwright/test";

const username = process.env.E2E_USERNAME;
const password = process.env.E2E_PASSWORD;
const portfolio = process.env.E2E_PORTFOLIO_ID;
const instrument = process.env.E2E_RESEARCH_INSTRUMENT_ID;

test.beforeEach(async ({ page }) => {
  test.skip(!username || !password || !portfolio || !instrument, "Explicit local synthetic fixture required");
  await page.goto("/login");
  await page.getByLabel("Benutzername").fill(username!);
  await page.getByLabel("Passwort", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await page.waitForURL("**/dashboard", { timeout: 30000 });
  await page.goto(`/portfolios/${portfolio}`);
  await expect(page.getByRole("navigation", { name: "Portfolio-Bereiche" })).toBeVisible({ timeout: 30000 });
});

test("risk dashboard exposes history gaps and nets actual FX scenario", async ({ page }) => {
  await page.getByRole("button", { name: "Risiko", exact: true }).click();
  await page.getByRole("button", { name: "Risiko-Snapshot berechnen" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Risiko: PARTIAL" })).toBeVisible({ timeout: 30000 });
  await expect(page.getByText("INCOMPLETE_VALIDATED_RETURN_SERIES", { exact: false })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Konzentration und Portfolio Health" })).toBeVisible();
  await page.getByRole("button", { name: "Korrelationen", exact: true }).click();
  await expect(page.getByText("CORRELATION_UNAVAILABLE").first()).toBeVisible();
  await page.getByRole("button", { name: "Szenarien", exact: true }).click();
  await page.getByLabel("Szenario", { exact: true }).selectOption("usdchf-minus10-v1");
  await page.getByRole("button", { name: "Szenario berechnen", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Szenario: AVAILABLE" })).toBeVisible();
  await expect(page.getByText("Gesamtwirkung: -18.00 CHF", { exact: false })).toBeVisible();
  await page.getByLabel("Szenario", { exact: true }).selectOption("custom-direct");
  await page.getByLabel("Eigener Schock").fill("-0.25");
  await page.getByRole("checkbox").last().check();
  await page.getByRole("button", { name: "Szenario berechnen", exact: true }).click();
  await expect(page.getByText("Gesamtwirkung: -270.00 CHF", { exact: false })).toBeVisible();
});

test("what-if changes the hypothetical valuation and preserves real ledger", async ({ page }) => {
  const before = await page.request.get(`http://localhost:8000/api/v1/portfolios/${portfolio}/transactions`);
  expect(before.ok()).toBeTruthy();
  const ledger = await before.json();
  await page.getByRole("button", { name: "What-if", exact: true }).click();
  await page.getByRole("button", { name: "Risiko-Snapshot berechnen" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Risiko: PARTIAL" })).toBeVisible({ timeout: 30000 });
  await page.getByLabel("What-if Instrument", { exact: true }).selectOption(instrument!);
  await page.getByLabel("What-if Betrag oder Verkaufsanteil").fill("100");
  await page.getByRole("button", { name: "Hypothese hinzufügen", exact: true }).click();
  await page.getByRole("button", { name: "What-if berechnen", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "What-if: PARTIAL" })).toBeVisible();
  await expect(page.getByText("Kosten: 1.10", { exact: false })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Nachher: hypothetische konstante Gewichte" })).toBeVisible();
  const after = await page.request.get(`http://localhost:8000/api/v1/portfolios/${portfolio}/transactions`);
  expect(await after.json()).toEqual(ledger);
  const valued = await page.request.get(`http://localhost:8000/api/v1/portfolios/${portfolio}/valuation`);
  expect(Number((await valued.json()).total_value_base)).toBe(10180);
});
