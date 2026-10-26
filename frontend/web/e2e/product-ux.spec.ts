import { test, expect, type Request, type TestInfo } from "@playwright/test";
import { writeFile } from "node:fs/promises";

async function preserveMeasurement(info: TestInfo, name: string, value: unknown) {
  const path = info.outputPath(name);
  await writeFile(path, JSON.stringify(value, null, 2));
  await info.attach(name, { path, contentType: "application/json" });
}

const measurementFinishers = new Map<string, () => Promise<void>>();

test.beforeEach(async ({ page }, testInfo) => {
  const timings: { action: string; milliseconds: number; status: number }[] = [];
  const statuses = new WeakMap<Request, number>();
  page.on("response", response => statuses.set(response.request(), response.status()));
  page.on("requestfinished", request => {
    const path = new URL(request.url()).pathname;
    const action = path.endsWith("/auth/login") ? "login" : path.endsWith("/portfolio-dashboard") ? "dashboard_api" : path.includes("/preview") ? "csv_preview" : path.includes("/commit") ? "csv_commit" : /\/prices$/.test(path) ? "price_chart_api" : /\/risk(?:\/[^/]+\/charts)?$/.test(path) ? "risk_api" : /\/instruments(?:\/search)?$/.test(path) ? "instrument_search_api" : /\/portfolios\/[^/]+\/(summary|valuation|holdings)$/.test(path) ? "portfolio_api" : null;
    if (!action) return;
    const timing = request.timing();
    const status = statuses.get(request);
    if (status !== undefined && timing.responseEnd >= 0) timings.push({ action, milliseconds: timing.responseEnd, status });
  });
  measurementFinishers.set(testInfo.testId, async () => {
    await preserveMeasurement(testInfo, "local-action-timings.json", { scope: "LOCAL_SYNTHETIC_REQUEST_DURATION_NOT_PRODUCTION_SLA", timings });
  });
});

test.afterEach(async ({}, testInfo) => {
  await measurementFinishers.get(testInfo.testId)?.();
  measurementFinishers.delete(testInfo.testId);
});

test("PR6 existing routes remain accessible on mobile and desktop", async ({ page }, testInfo) => {
  test.setTimeout(180000);
  if (!process.env.E2E_USERNAME || !process.env.E2E_PASSWORD || !process.env.E2E_PORTFOLIO_ID || !process.env.E2E_RESEARCH_INSTRUMENT_ID) throw new Error("Explicit synthetic fixture required");
  await page.goto("/login");
  await page.getByLabel("Benutzername", { exact: true }).fill(process.env.E2E_USERNAME);
  await page.getByLabel("Passwort", { exact: true }).fill(process.env.E2E_PASSWORD);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 30000 });
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(`${page.url()}: ${error.stack ?? error.message}`));
  const routes = ["/", "/dashboard", "/alerts", "/analyses", "/assistant", "/backtests", "/daily-brief", "/data-operations", "/data-operations/readiness", "/data-quality", "/documents", "/imports", `/instrument/${process.env.E2E_RESEARCH_INSTRUMENT_ID}`, "/instruments", "/models/forward-validation", "/models", "/models/validation", "/news", "/optimizer", `/portfolios/${process.env.E2E_PORTFOLIO_ID}`, "/portfolios/new", "/portfolios", "/recommendations", "/recommendations/validation", "/research", "/settings/data-sources", "/settings", "/system/status", "/time-machine", "/watchlists"];
  const observations = [];
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 960 });
    for (const route of routes) {
      const started = Date.now();
      const response = await page.goto(route);
      expect(response?.status(), route).toBeLessThan(400);
      await expect(page.locator("#main-content")).toBeVisible();
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), { message: `${route} at ${width}` }).toBe(true);
      observations.push({ route, width, shell_ready_ms: Date.now() - started });
    }
  }
  await preserveMeasurement(testInfo, "route-smoke-timing.json", { scope: "SYNTHETIC_ROUTE_SHELL_NOT_ALL_ACTIONS_OR_PRODUCTION_SLA", observations });
  expect(errors).toEqual([]);
});

test("PR6 six areas, responsive themes and keyboard navigation", async ({ page }, testInfo) => {
  test.setTimeout(150000);
  if (!process.env.E2E_USERNAME || !process.env.E2E_PASSWORD) throw new Error("Explicit synthetic fixture required");
  const errors: string[] = [];
  const dashboardStarted = Date.now();
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/login");
  await page.getByLabel("Benutzername", { exact: true }).fill(process.env.E2E_USERNAME);
  await page.getByLabel("Passwort", { exact: true }).fill(process.env.E2E_PASSWORD);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 30000 });
  await expect(page.getByRole("heading", { name: "Ihre Positionen", exact: true })).toBeVisible({ timeout: 30000 });
  await expect(page.getByRole("status", { name: "Wertentwicklung wird geladen", exact: true })).toHaveCount(0, { timeout: 60000 });
  const periods = page.getByRole("group", { name: "Zeitraum: Portfoliowert", exact: true });
  await expect(periods).toBeVisible();
  await periods.getByRole("button", { name: "1W", exact: true }).click();
  await expect(periods.getByRole("button", { name: "1W", exact: true })).toHaveAttribute("aria-pressed", "true");
  await periods.getByRole("button", { name: "MAX", exact: true }).click();
  await expect(page.getByRole("img", { name: /^Portfoliowert,/ }).locator("canvas").first()).toBeVisible();
  await preserveMeasurement(testInfo, "local-dashboard-timing.json", { scope: "LOCAL_SYNTHETIC_STANDALONE_NOT_PRODUCTION_SLA", login_and_dashboard_ms: Date.now() - dashboardStarted, navigation: await page.evaluate(() => performance.getEntriesByType("navigation").map(entry => entry.toJSON())) });
  const areas = ["Übersicht", "Portfolio", "Entdecken", "Analysen", "Aktivitäten", "Einstellungen"];
  for (const width of [360, 390, 768, 1024, 1440, 1920]) {
    await page.setViewportSize({ width, height: 960 });
    for (const theme of ["light", "dark"]) {
      await page.getByRole("combobox", { name: "Darstellung", exact: true }).selectOption(theme);
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
      const contrasts = await page.evaluate(() => {
        const probe = document.createElement("span"); document.body.append(probe);
        const color = (variable: string) => { probe.style.color = `var(${variable})`; return getComputedStyle(probe).color; };
        const luminance = (rgb: string) => rgb.match(/[\d.]+/g)!.slice(0, 3).map(v => Number(v) / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
        const surface = luminance(color("--surface"));
        const result = Object.fromEntries(["--ink", "--muted", "--accent", "--positive", "--negative", "--warning", "--border-strong"].map(variable => { const value = luminance(color(variable)); return [variable, (Math.max(surface, value) + .05) / (Math.min(surface, value) + .05)]; }));
        probe.remove(); return result;
      });
      for (const [token, contrast] of Object.entries(contrasts)) expect(contrast, `${theme}: ${token}`).toBeGreaterThanOrEqual(token === "--border-strong" ? 3 : 4.5);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: "instant" }));
      await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
      await page.screenshot({ path: testInfo.outputPath(`dashboard-${width}-${theme}.png`), fullPage: true });
    }
    if (width < 768) {
      await page.getByRole("button", { name: "Navigation öffnen", exact: true }).focus();
      await page.keyboard.press("Enter");
      const dialog = page.getByRole("dialog");
      await expect(dialog).toBeVisible();
      for (const area of areas) await expect(dialog.getByRole("link", { name: area, exact: true })).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(dialog).toHaveCount(0);
      await expect(page.getByRole("button", { name: "Navigation öffnen", exact: true })).toBeFocused();
    } else {
      const nav = page.getByRole("navigation", { name: "Primärnavigation" });
      await expect(nav.getByRole("link")).toHaveCount(6);
      for (const area of areas) await expect(nav.getByRole("link", { name: area, exact: true })).toBeVisible();
    }
  }
  await page.getByRole("combobox", { name: "Darstellung", exact: true }).selectOption("system");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "system");
  await page.reload();
  await expect(page.getByRole("combobox", { name: "Darstellung", exact: true })).toHaveValue("system");
  expect(errors).toEqual([]);
});

test("PR6 guided setup and explicit Swiss CSV interpretation", async ({ page }) => {
  if (!process.env.E2E_USERNAME || !process.env.E2E_PASSWORD) throw new Error("Explicit synthetic fixture required");
  const headers = { Origin: process.env.E2E_BASE_URL ?? "http://localhost:3000" };
  const base = process.env.E2E_API_BASE_URL ?? "http://localhost:8000/api/v1";
  await page.goto("/login");
  await page.getByLabel("Benutzername", { exact: true }).fill(process.env.E2E_USERNAME);
  await page.getByLabel("Passwort", { exact: true }).fill(process.env.E2E_PASSWORD);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 30000 });
  await page.goto("/portfolios/new");
  await page.getByLabel("Portfolio-Name", { exact: true }).fill(`SYNTHETIC PR6 ${Date.now()}`);
  await page.getByRole("button", { name: "Portfolio anlegen und weiter", exact: true }).click();
  await expect(page).toHaveURL(/portfolio=.+step=1/);
  const id = new URL(page.url()).searchParams.get("portfolio")!;
  try {
    await page.getByLabel("Neues Konto benennen", { exact: true }).fill("SYNTHETIC PR6 Broker");
    await page.getByRole("button", { name: "Konto anlegen und weiter", exact: true }).click();
    await page.getByRole("button", { name: "Ohne Cash-Buchung weiter", exact: true }).click();
    await page.getByLabel("Importkonto", { exact: true }).selectOption({ label: "SYNTHETIC PR6 Broker" });
    await page.getByLabel("Transaktionsdatei", { exact: true }).setInputFiles({ name: "SYNTHETIC-CH.csv", mimeType: "text/csv", buffer: Buffer.from("\uFEFFtype;date;currency;amount;external_id\nDEPOSIT;01/02/2026;CHF;1'234.50;SYNTHETIC-CH-1\n") });
    await page.getByRole("button", { name: "Vorschau prüfen", exact: true }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Format nicht eindeutig" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Import übernehmen", exact: true })).toBeDisabled();
    await page.getByLabel("CSV-Trennzeichen", { exact: true }).selectOption(";");
    await page.getByLabel("CSV-Datumsformat", { exact: true }).selectOption("DMY");
    await page.getByLabel("CSV-Zahlenformat", { exact: true }).selectOption("CH");
    await page.getByRole("button", { name: "Vorschau prüfen", exact: true }).click();
    await expect(page.getByRole("status").filter({ hasText: "1 importierbar" })).toBeVisible();
    await page.getByRole("checkbox", { name: /Ich habe Konto, Instrumente/ }).check();
    await page.getByRole("button", { name: "Import übernehmen", exact: true }).click();
    await expect(page.getByRole("status").filter({ hasText: "1 Buchungen übernommen" })).toBeVisible();
    await page.getByRole("button", { name: "Weiter zu Kursen und Währungen", exact: true }).click();
    await page.getByRole("button", { name: "Bewertung prüfen", exact: true }).click();
    await expect(page.getByText("CHF", { exact: false }).filter({ hasText: /1.234/ }).first()).toBeVisible();
    const transactions = await page.request.get(`${base}/portfolios/${id}/transactions`);
    expect(transactions.ok()).toBe(true);
    const rows = await transactions.json();
    expect(rows).toHaveLength(1);
    expect(Number(rows[0].amount)).toBe(1234.5);
    expect(rows[0].trade_date).toBe("2026-02-01");
  } finally {
    expect((await page.request.delete(`${base}/portfolios/${id}`, { headers })).ok()).toBe(true);
  }
});

test("PR6 document withdrawal is confirmed and remains idempotent", async ({ page }) => {
  if (!process.env.E2E_USERNAME || !process.env.E2E_PASSWORD) throw new Error("Explicit synthetic fixture required");
  const base = process.env.E2E_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const headers = { Origin: process.env.E2E_BASE_URL ?? "http://localhost:3000" };
  await page.goto("/login");
  await page.getByLabel("Benutzername", { exact: true }).fill(process.env.E2E_USERNAME);
  await page.getByLabel("Passwort", { exact: true }).fill(process.env.E2E_PASSWORD);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 30000 });
  const sources = await (await page.request.get(`${base}/data-sources`)).json() as { slug: string; enabled: boolean; allowed_uses: string[] }[];
  const source = sources.find(s => s.slug.startsWith("TEST_P10_") && s.enabled && s.allowed_uses.includes("RAG_METADATA"));
  expect(source, "Existing explicitly synthetic document fixture required; do not approve a real source").toBeTruthy();
  const title = `SYNTHETIC PR6 removable metadata ${Date.now()}`;
  const response = await page.request.post(`${base}/research-documents/metadata`, { headers, data: { title, source_slug: source!.slug } });
  expect(response.status()).toBe(201);
  const document = await response.json();
  await page.goto("/documents");
  const card = page.getByRole("article").filter({ has: page.getByRole("heading", { name: title, exact: true }) });
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "Aus Bibliothek entfernen", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("keine physische Löschung");
  await dialog.getByRole("button", { name: "Abbrechen", exact: true }).click();
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "Aus Bibliothek entfernen", exact: true }).click();
  const removal = page.waitForResponse(r => r.url().endsWith(`/research-documents/${document.id}`) && r.request().method() === "DELETE");
  await dialog.getByRole("button", { name: "Ausdrücklich bestätigen", exact: true }).click();
  expect((await removal).status()).toBe(200);
  await expect(dialog).toHaveCount(0);
  await expect(card).toHaveCount(0);
  expect((await page.request.get(`${base}/research-documents/${document.id}`)).status()).toBe(410);
  expect((await page.request.delete(`${base}/research-documents/${document.id}`, { headers })).status()).toBe(200);
});
