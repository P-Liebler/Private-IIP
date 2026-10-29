import { expect, test } from "@playwright/test";

test("PR9: unsigned style elements are blocked and nonce styles remain usable", async ({ page }) => {
  await page.route("**/login", async (route) => {
    if (route.request().resourceType() !== "document") {
      await route.continue();
      return;
    }
    const response = await route.fetch();
    const policy = response.headers()["content-security-policy"];
    const elementRule = policy.split(";").find((part) => part.trim().startsWith("style-src-elem "))!;
    expect(elementRule).not.toContain("'unsafe-inline'");
    expect(policy).toContain("style-src-attr 'unsafe-inline'");
    const nonce = /'nonce-([^']+)'/.exec(elementRule)![1];
    const body = (await response.text())
      .replace("</head>", `<style>#pr9-style-probe{display:none!important}</style><style nonce="${nonce}">#pr9-style-probe{outline-style:solid;outline-width:7px}</style></head>`)
      .replace("</body>", '<div id="pr9-style-probe" style="outline-color:rgb(4,5,6)">CSS-Probe</div></body>');
    await route.fulfill({ response, body });
  });
  await page.goto("/login");
  const probe = page.locator("#pr9-style-probe");
  await expect(probe).toBeVisible();
  await expect(probe).toHaveCSS("outline-width", "7px");
  await expect(probe).toHaveCSS("outline-color", "rgb(4, 5, 6)");
  await expect(page.getByRole("button", { name: /Anmelden/i })).toBeVisible();
  await page.unroute("**/login");
  // The injected parser probe ends here. Exercise authentication with an
  // ordinary fresh document and its actual response policy, without replay.
  await page.goto("/login");

  if (!process.env.E2E_USERNAME || !process.env.E2E_PASSWORD) throw new Error("Explicit synthetic login fixture required");
  await page.getByLabel("Benutzername", { exact: true }).fill(process.env.E2E_USERNAME);
  await page.getByLabel("Passwort", { exact: true }).fill(process.env.E2E_PASSWORD);
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 30000 });
  const errors: string[] = [];
  page.on("console", message => {
    if (message.type() === "error" && /style-src|inline style/i.test(message.text())) errors.push(message.text());
  });
  // A full document load establishes the exact policy nonce. Radix's real
  // scroll-lock stylesheet must inherit it through the client nonce bridge.
  const response = await page.goto("/dashboard");
  const documentNonce = /'nonce-([^']+)'/.exec(response!.headers()["content-security-policy"])![1];
  await page.setViewportSize({ width: 390, height: 960 });
  await page.getByRole("button", { name: "Navigation öffnen", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  // Text locators deliberately exclude style elements. Inspect textContent of
  // the actual emitted stylesheet and verify its DOM nonce property instead.
  await expect.poll(() => page.locator("style").evaluateAll(elements => elements
    .filter(element => element.textContent?.includes("data-scroll-locked"))
    .map(element => (element as HTMLStyleElement).nonce))).toEqual([documentNonce]);
  await expect(page.locator("body")).toHaveCSS("overflow", "hidden");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(errors).toEqual([]);
});
