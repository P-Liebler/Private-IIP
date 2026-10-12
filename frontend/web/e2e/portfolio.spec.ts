import { expect, test } from "@playwright/test";

const username = process.env.E2E_USERNAME;
const password = process.env.E2E_PASSWORD;
const portfolioId = process.env.E2E_PORTFOLIO_ID;
let cleanupPortfolioId: string | undefined;
let cleanupInstrumentId: string | undefined;

test.afterEach(async ({ page }) => {
  const apiBase = process.env.E2E_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const headers = { Origin: process.env.E2E_BASE_URL ?? "http://localhost:3000" };
  if (cleanupPortfolioId) expect((await page.request.delete(`${apiBase}/portfolios/${cleanupPortfolioId}`, { headers })).ok()).toBeTruthy();
  if (cleanupInstrumentId) await page.request.patch(`${apiBase}/instruments/${cleanupInstrumentId}`, { headers, data: { active: false } });
  cleanupPortfolioId = cleanupInstrumentId = undefined;
});

test("login and inspect a valued portfolio", async ({ page }) => {
  test.skip(!username || !password || !portfolioId, "Set E2E_USERNAME, E2E_PASSWORD and E2E_PORTFOLIO_ID");

  await page.goto("/login");
  await page.getByLabel("Benutzername").fill(username!);
  await page.getByLabel("Passwort").fill(password!);
  await page.getByRole("button", { name: "Anmelden" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.goto(`/portfolios/${portfolioId}`);
  await expect(page.getByRole("heading", { name: "Disposable restore test" })).toBeVisible();
  await expect(page.getByText(/10.?180\.00 CHF/).first()).toBeVisible();
  await page.getByRole("button", { name: "Positionen" }).click();
  await expect(page.getByRole("heading", { name: "Disposable restore test instrument" })).toBeVisible();
  await page.getByRole("button", { name: "Transaktionen" }).click();
  await expect(page.getByText(/DEPOSIT/).last()).toBeVisible();
  await expect(page.getByText(/BUY/).last()).toBeVisible();
  await page.getByRole("button", { name: "Datenqualität" }).click();
  await expect(page.getByRole("heading", { name: /Bewertungsstatus: COMPLETE/ })).toBeVisible();
});

test("create portfolio, account, deposit and buy; show missing price explicitly", async ({ page }) => {
  test.skip(!username || !password, "Set credentials for an explicit disposable local test user");
  const apiBase = process.env.E2E_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const origin = process.env.E2E_BASE_URL ?? "http://localhost:3000";
  await page.goto("/login");
  await page.getByLabel("Benutzername").fill(username!);
  await page.getByLabel("Passwort").fill(password!);
  await page.getByRole("button", { name: "Anmelden" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
    const name = `Browser acceptance ${Date.now()}`;
    await page.goto("/portfolios");
    await page.getByLabel("Portfolio-Name", { exact: true }).fill(name);
    await page.getByRole("button", { name: "Erstellen", exact: true }).click();
    await page.getByRole("link", { name, exact: true }).click();
    await expect(page).toHaveURL(/\/portfolios\/[0-9a-f-]{36}$/);
    cleanupPortfolioId = page.url().split("/").pop();
    await page.getByRole("button", { name: "Transaktionen", exact: true }).click();
    await page.getByLabel("Account-Name").fill("Browser broker");
    await page.getByRole("button", { name: "Account anlegen", exact: true }).click();
    await expect(page.getByRole("button", { name: "Buchen", exact: true })).toBeEnabled();
    await page.getByLabel("Betrag", { exact: true }).fill("10000");
    await page.getByRole("button", { name: "Buchen", exact: true }).click();
    await expect(page.getByRole("listitem").filter({ hasText: "DEPOSIT" })).toBeVisible();
    await page.getByRole("combobox", { name: "Typ", exact: true }).selectOption("BUY");
    await page.getByLabel("Instrument suchen").fill("Disposable restore test instrument");
    await page.getByRole("button", { name: "Suchen", exact: true }).click();
    await page.getByRole("button", { name: /Disposable restore test instrument/ }).click();
    await page.getByLabel("Stückzahl", { exact: true }).fill("10");
    await page.getByLabel("Preis je Stück").fill("100");
    await page.getByLabel("Gebühr", { exact: true }).fill("2");
    await page.getByLabel("Steuer / Quellensteuer").fill("1");
    await page.getByRole("button", { name: "Buchen", exact: true }).click();
    await expect(page.getByRole("listitem").filter({ hasText: "BUY" })).toBeVisible();
    await page.getByRole("button", { name: "Übersicht", exact: true }).click();
    await expect(page.getByText(/10.?177\.30 CHF/).first()).toBeVisible();
    await expect(page.getByText("177.30 CHF").first()).toBeVisible();
    await page.getByRole("button", { name: "Allokation", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Anlageklasse", exact: true })).toBeVisible();
    await expect(page.getByText("STOCK", { exact: true })).toBeVisible();

    const missingName = `Explicit browser test without price ${Date.now()}`;
    const missingTicker = `E${Date.now()}`;
    const today = new Date().toISOString().slice(0, 10);
    const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    const purchaseDay = new Date(Date.now() - 2 * 86400000).toISOString().slice(0, 10);
    const instrument = await page.request.post(`${apiBase}/instruments`, { headers: { Origin: origin }, data: {
      name: missingName, asset_type: "STOCK", currency: "CHF", ticker: missingTicker,
      listed_at: purchaseDay,
    } });
    expect(instrument.status()).toBe(201);
    cleanupInstrumentId = (await instrument.json()).id;
    await page.getByRole("button", { name: "Transaktionen", exact: true }).click();
    await page.getByLabel("Instrument suchen").fill(missingName);
    await page.getByRole("button", { name: "Suchen", exact: true }).click();
    await page.getByRole("button", { name: new RegExp(missingName) }).click();
    await page.getByLabel("Stückzahl", { exact: true }).fill("1");
    await page.getByLabel("Preis je Stück").fill("1");
    await page.getByLabel("Handelsdatum").fill(purchaseDay);
    await page.getByRole("button", { name: "Buchen", exact: true }).click();
    await expect(page.getByRole("listitem").filter({ hasText: "BUY" })).toHaveCount(2);
    await page.getByRole("button", { name: "Übersicht", exact: true }).click();
    await expect(page.getByRole("status")).toContainText("Portfolio PARTIAL");
    await expect(page.getByText("DATA_UNAVAILABLE").first()).toBeVisible();
    await page.getByRole("button", { name: "Datenqualität", exact: true }).click();
    await expect(page.getByText("MISSING_PRICE", { exact: false })).toBeVisible();
    await page.getByRole("button", { name: "Transaktionen", exact: true }).click();
    await page.getByRole("combobox", { name: "Typ", exact: true }).selectOption("DIVIDEND");
    await page.getByLabel("Handelsdatum").fill(yesterday);
    await page.getByLabel("Betrag", { exact: true }).fill("1");
    await page.getByLabel("Gebühr", { exact: true }).fill("0");
    await page.getByLabel("Steuer / Quellensteuer").fill("0.25");
    await page.getByRole("button", { name: "Buchen", exact: true }).click();
    await expect(page.getByRole("listitem").filter({ hasText: "DIVIDEND" })).toHaveCount(1);
    const actionCsv = `date,ticker,action_type,value,currency\n${yesterday},${missingTicker},DIVIDEND,1,CHF\n${today},${missingTicker},SPLIT,2,\n`;
    const preview = await page.request.post(`${apiBase}/market-data/imports/actions/preview`, { headers: { Origin: origin, "Content-Type": "text/csv" }, data: actionCsv });
    expect(preview.status()).toBe(200);
    const imported = await preview.json();
    const commit = await page.request.post(`${apiBase}/market-data/imports/actions/commit`, { headers: { Origin: origin }, data: { raw_ingestion_id: imported.raw_ingestion_id, mapping: imported.mapping } });
    expect(commit.status()).toBe(200);
    await page.reload();
    await page.getByRole("button", { name: "Datenqualität", exact: true }).click();
    await expect(page.getByRole("button", { name: "Corporate Action prüfen", exact: true })).toHaveCount(2);
    for (const review of await page.getByRole("button", { name: "Corporate Action prüfen", exact: true }).all()) await review.click();
    const feeInput = page.getByLabel("Bestätigte Dividenden-Gebühr");
    await expect(feeInput).toHaveValue("");
    await expect(feeInput).toHaveAttribute("required", "");
    await feeInput.fill("0");
    await page.getByLabel("Bestätigte Quellensteuer").fill("0.25");
    await page.getByRole("checkbox", { name: /Vorhandene manuelle Buchung/ }).check();
    const dividendForm = page.locator("form").filter({ has: feeInput });
    await dividendForm.getByRole("button", { name: "Geprüften Effekt buchen" }).click();
    await expect(page.getByLabel("Bestätigte Dividenden-Gebühr")).toHaveCount(0);
    await page.getByRole("button", { name: "Geprüften Effekt buchen", exact: true }).click();
    await expect(page.getByRole("button", { name: "Corporate Action prüfen", exact: true })).toHaveCount(0);
    await page.getByRole("button", { name: "Dividenden", exact: true }).click();
    await expect(page.getByText(/Basis netto: 0.75 CHF/)).toBeVisible();
});
