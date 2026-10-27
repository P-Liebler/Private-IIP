import { expect, test } from "@playwright/test";

for (const item of [
  { page: "/news", api: "/news?", pattern: "**/api/v1/news?**", region: "Archivierte Nachrichten" },
  { page: "/data-quality", api: "/data-quality/summary", pattern: "**/api/v1/data-quality/summary", region: "Marktdatenqualität" },
]) {
  test(`PR7 ${item.page} exposes a read failure and keyboard retry without losing filters`, async ({ page }) => {
    const username = process.env.E2E_USERNAME;
    const password = process.env.E2E_PASSWORD;
    if (!username || !password) throw new Error("Explicit synthetic fixture required");
    await page.goto("/login");
    await page.getByLabel("Benutzername").fill(username);
    await page.getByLabel("Passwort", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Anmelden", exact: true }).click();
    await page.waitForURL("**/dashboard", { timeout: 30000 });
    let blocked = true;
    await page.route(item.pattern, route => {
      if (route.request().method() !== "GET" || !blocked) return route.continue();
      return route.fulfill({ status: 503, headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": new URL(page.url()).origin,
        "Access-Control-Allow-Credentials": "true",
      }, body: JSON.stringify({ error: { code: "SYNTHETIC_TRANSPORT_OUTAGE", message: "Synthetic read outage" } }) });
    });
    await page.goto(item.page);
    if (item.page === "/news") await page.getByLabel("News ab Datum", { exact: true }).fill("2020-01-01");
    const region = page.getByRole("region", { name: item.region, exact: true });
    const error = region.getByRole("alert");
    await expect(error).toContainText("Dienst ist momentan nicht verfügbar");
    if (item.page === "/data-quality") await expect(page.getByRole("heading", { name: "Kursaktualität", exact: true })).toHaveCount(0);
    blocked = false;
    const response = page.waitForResponse(value => value.url().includes(item.api) && value.request().method() === "GET" && value.status() === 200);
    await error.getByRole("button", { name: "Erneut versuchen", exact: true }).focus();
    await page.keyboard.press("Enter");
    await response;
    await expect(region.getByRole("alert")).toHaveCount(0);
    if (item.page === "/news") await expect(page.getByLabel("News ab Datum", { exact: true })).toHaveValue("2020-01-01");
    else await expect(page.getByRole("heading", { name: "Kursaktualität", exact: true })).toBeVisible();
  });
}
