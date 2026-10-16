import { test, expect, type Page } from "@playwright/test";
const username = process.env.E2E_USERNAME;
const password = process.env.E2E_PASSWORD;
const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Benutzername", { exact: true }).fill(username!);
  await page.getByLabel("Passwort", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await page.waitForURL("**/dashboard", { timeout: 30000 });
}

test("PR1 rights remain gated and unavailable history is explicit", async ({ page }) => {
  test.skip(!username || !password, "Explicit local fixture required");
  await login(page);
  await page.goto("/data-operations");
  await expect(page.getByRole("heading", { name: "Datenversorgung", exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: "Datentyp", exact: true }).selectOption("ECB_FX");
  await expect(page.getByRole("button", { name: "Umfang prüfen" })).toBeDisabled();
  await expect(page.getByText(/SOURCE_NOT_APPROVED/)).toBeVisible();
  await page.goto("/settings/data-sources");
  const yahoo = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name: /Yahoo/i }) });
  await expect(yahoo).toContainText("BLOCKED");
  await expect(yahoo).toContainText("Letzter erfolgreicher Import");
});

test("PR1 bounded synthetic CSV job shows provenance and unverified action coverage", async ({ page }) => {
  test.skip(!username || !password, "Explicit local fixture required");
  test.setTimeout(120000);
  await login(page);
  const ticker = `PR1${Date.now().toString(36).toUpperCase()}`;
  const created = await page.request.post(`${base}/instruments`, { data: { name: `SYNTHETIC PR1 ${ticker}`, ticker,
    asset_type: "STOCK", currency: "CHF", exchange: "SIX", country: "CH", listed_at: "2024-01-01" } });
  expect(created.status()).toBe(201);
  const instrument = await created.json();
  await page.goto("/data-operations");
  await page.getByRole("combobox", { name: "Datentyp", exact: true }).selectOption("MANUAL_PRICES");
  await page.getByLabel("Von", { exact: true }).fill("2024-01-03");
  await page.getByLabel("Bis", { exact: true }).fill("2024-01-05");
  await page.getByLabel(/Kursdatei/).setInputFiles({ name: "SYNTHETIC-pr1.csv", mimeType: "text/csv",
    buffer: Buffer.from(`date,ticker,open,high,low,close,volume,currency\n2024-01-03,${ticker},99,101,98,100,10,CHF\n`) });
  await expect(page.getByText(/Original archiviert/)).toBeVisible();
  await page.getByRole("button", { name: "Umfang prüfen" }).click();
  await expect(page.getByText(/höchstens 0 Anfragen/)).toBeVisible();
  await page.getByRole("button", { name: "Geprüften Auftrag starten" }).click();
  await expect(page.getByRole("article").filter({ hasText: "MANUAL_PRICES" }).first()).toContainText("SUCCESS", { timeout: 90000 });
  await page.goto(`/instrument/${instrument.id}`);
  await page.getByLabel("Abdeckung ab").fill("2024-01-03");
  await page.getByLabel("Abdeckung bis").fill("2024-01-05");
  await expect(page.getByText("CORPORATE_ACTION_COVERAGE_UNVERIFIED", { exact: true })).toBeVisible();
  await expect(page.getByText(/0 \/ 1 · fehlend: NO_FILL/)).not.toBeVisible();
  await expect(page.getByText(/1 \/ 1 · fehlend: NO_FILL/)).toBeVisible();
});
