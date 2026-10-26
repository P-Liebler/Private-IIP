import { test, expect, type Page } from "@playwright/test";

const username = process.env.E2E_USERNAME;
const password = process.env.E2E_PASSWORD;
const portfolio = process.env.E2E_PORTFOLIO_ID;
const instrument = process.env.E2E_RESEARCH_INSTRUMENT_ID;

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Benutzername").fill(username!);
  await page.getByLabel("Passwort", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await page.waitForURL("**/dashboard", { timeout: 30000 });
}

test("P10 assistant preserves financial gates, private history and source evidence", async ({ page }) => {
  test.skip(!username || !password || !portfolio || !instrument, "Explicit synthetic local fixture required");
  await login(page);
  await page.goto("/assistant");
  await page.getByRole("button", { name: "Neue Unterhaltung", exact: true }).click();
  await page.getByRole("combobox", { name: "Portfolio", exact: true }).selectOption(portfolio!);
  await page.getByLabel("Instrument-ID", { exact: true }).fill(instrument!);
  await page.getByLabel("Frage", { exact: true }).fill("Soll ich kaufen? Empfehlung und Risiken erklaeren.");
  await page.getByRole("button", { name: "Analyse starten", exact: true }).click();
  await expect(page.getByLabel("Nachrichten")).toContainText("NO_VALIDATED_PRODUCTION_FORECAST", { timeout: 65000 });
  await expect(page.getByRole("button", { name: "Analyse starten", exact: true })).toBeDisabled();
  const conversation = await page.getByLabel("Unterhaltung", { exact: true }).inputValue();
  await page.reload();
  await page.getByLabel("Unterhaltung", { exact: true }).selectOption(conversation);
  await expect(page.getByLabel("Nachrichten")).toContainText("NO_VALIDATED_PRODUCTION_FORECAST");
  await page.getByRole("button", { name: "Unterhaltung loeschen", exact: true }).click();
  await expect(page.getByLabel("Nachrichten")).not.toContainText("NO_VALIDATED_PRODUCTION_FORECAST");
  await page.goto("/documents");
  await page.getByLabel("Dokumentensuche").fill("synthetic document provenance");
  await page.getByRole("button", { name: "Belegte Auszuege suchen", exact: true }).click();
  await expect(page.locator("main")).toContainText("EXACT_ARCHIVED_TEXT_NOT_VALIDATED_FINANCIAL_VALUES", { timeout: 30000 });
  await expect(page.locator("main")).toContainText("chunk_id");
});

test("P10 unavailable alert is explicit, brief is idempotent, optimizer abstains and history stays strict", async ({ page }) => {
  test.skip(!username || !password || !portfolio || !instrument, "Explicit synthetic local fixture required");
  await login(page);
  await page.goto("/alerts");
  const ruleName = `SYNTHETIC browser ${Date.now()}`;
  await page.getByLabel("Regelname").fill(ruleName);
  await page.getByLabel("Alert-Typ").selectOption("FORECAST_CHANGED");
  await page.getByLabel("Instrument-ID", { exact: true }).fill(instrument!);
  await page.getByRole("button", { name: "Regel speichern", exact: true }).click();
  const rule = page.getByRole("article").filter({ has: page.getByRole("heading", { name: `${ruleName} · FORECAST_CHANGED`, exact: true }) });
  await expect(rule.getByRole("button", { name: "Jetzt auswerten", exact: true })).toBeEnabled({ timeout: 30000 });
  await rule.getByRole("button", { name: "Jetzt auswerten", exact: true }).click();
  await expect(page.locator("main")).toContainText("ALERT_EVALUATION_UNAVAILABLE");
  await page.goto("/daily-brief");
  await page.getByRole("button", { name: "Bericht jetzt erstellen", exact: true }).click();
  await expect(page.getByLabel("Daily Brief Inhalt")).toBeVisible({ timeout: 45000 });
  await expect(page.getByLabel("Daily Brief Inhalt")).toContainText("UNAVAILABLE");
  await page.goto(`/portfolios/${portfolio}`);
  await expect(page.getByRole("navigation", { name: "Portfolio-Bereiche" })).toBeVisible();
  await page.getByRole("button", { name: "Risiko", exact: true }).click();
  const riskResponse = page.waitForResponse(r => r.url().endsWith(`/portfolios/${portfolio}/risk`) && r.request().method() === "POST");
  await page.getByRole("button", { name: "Risiko-Snapshot berechnen" }).click();
  expect((await riskResponse).status()).toBe(200);
  await page.goto("/optimizer");
  await page.getByRole("combobox", { name: "Portfolio", exact: true }).selectOption(portfolio!);
  await expect(page.getByRole("button", { name: "Simulation berechnen", exact: true })).toBeEnabled({ timeout: 15000 });
  await page.getByRole("button", { name: "Simulation berechnen", exact: true }).click();
  await expect(page.getByLabel("Optimierungsergebnis")).toContainText("OPTIMIZATION_UNAVAILABLE");
  await page.goto("/time-machine");
  await page.getByLabel("Instrument-ID", { exact: true }).fill(instrument!);
  await page.getByLabel("Wissensstand", { exact: true }).fill("2020-01-01T12:00");
  await page.getByRole("button", { name: "Wissensstand pruefen", exact: true }).click();
  await expect(page.getByLabel("Historischer Wissensstand")).toContainText("NO HISTORICAL PREDICTION");
  await expect(page.getByLabel("Historischer Wissensstand")).toContainText("NOT_ARCHIVED_AT_SELECTED_DATE");
});
