import { test, expect } from "@playwright/test";

const username = process.env.E2E_USERNAME;
const password = process.env.E2E_PASSWORD;
const portfolio = process.env.E2E_PORTFOLIO_ID;

test("P9 profile version, gated evaluation and immutable history", async ({ page }) => {
  test.skip(!username || !password || !portfolio, "Explicit synthetic local fixture required");
  await page.goto("/login");
  await page.getByLabel("Benutzername").fill(username!);
  await page.getByLabel("Passwort", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await page.waitForURL("**/dashboard", { timeout: 30000 });
  // CI starts with fresh P4/P5/P6 fixtures; it has no saved P8 risk yet.
  await page.goto(`/portfolios/${portfolio}`);
  await expect(page.getByRole("navigation", { name: "Portfolio-Bereiche" })).toBeVisible({ timeout: 30000 });
  await page.getByRole("button", { name: "Risiko", exact: true }).click();
  const riskResponse = page.waitForResponse(response => response.url().endsWith(`/portfolios/${portfolio}/risk`) && response.request().method() === "POST");
  await page.getByRole("button", { name: "Risiko-Snapshot berechnen" }).click();
  expect((await riskResponse).status()).toBe(200);
  await page.goto("/recommendations");
  await expect(page.getByRole("heading", { name: "NO VALIDATED INVESTMENT RECOMMENDATIONS" })).toBeVisible();
  await expect(page.getByLabel("Profilparameter")).not.toHaveValue("", { timeout: 30000 });
  const preferences = JSON.parse(await page.getByLabel("Profilparameter").inputValue()) as Record<string, unknown>;
  preferences.confirmed = false;
  await page.getByLabel("Profilparameter").fill(JSON.stringify(preferences));
  await page.getByRole("button", { name: "Profilversion speichern" }).click();
  await expect(page.getByRole("status")).toContainText("Profilversion gespeichert");
  await page.getByLabel("Portfolio", { exact: true }).selectOption(portfolio!);
  await expect(page.getByRole("button", { name: "Eligibility prüfen und speichern" })).toBeEnabled({ timeout: 30000 });
  await page.getByRole("button", { name: "Eligibility prüfen und speichern" }).click();
  await expect(page.getByRole("status")).toContainText("Bewertungen gespeichert", { timeout: 120000 });
  await expect(page.getByLabel("Bewertungsdetails")).toContainText("NO_VALIDATED_PRODUCTION_FORECAST");
  await expect(page.getByRole("heading", { name: "Unveränderliche Bewertungshistorie" })).toBeVisible();
  await page.reload();
  await page.getByLabel("Portfolio", { exact: true }).selectOption(portfolio!);
  await expect(page.getByRole("button", { name: /INSUFFICIENT_DATA|INELIGIBLE/ }).first()).toBeVisible();
  await page.getByRole("button", { name: /INSUFFICIENT_DATA|INELIGIBLE/ }).first().click();
  await expect(page.getByLabel("Bewertungsdetails")).toContainText("NO_VALIDATED_PRODUCTION_FORECAST");
});
