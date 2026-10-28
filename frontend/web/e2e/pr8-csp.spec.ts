import { expect, test } from "@playwright/test";

test("PR8: request nonces differ and unsigned inline scripts are blocked", async ({ page, request }) => {
  const first = await request.get("/login", { headers: { "x-nonce": "attacker-controlled" } });
  const second = await request.get("/login");
  const policy = first.headers()["content-security-policy"];
  const scripts = policy.split(";").find((part) => part.trim().startsWith("script-src "))!;
  expect(scripts).toContain("'strict-dynamic'");
  expect(scripts).not.toContain("'unsafe-inline'");
  expect(scripts).not.toContain("'unsafe-eval'");
  expect(policy).not.toContain("attacker-controlled");
  expect(second.headers()["content-security-policy"]).not.toBe(policy);
  const nonce = /'nonce-([^']+)'/.exec(scripts)![1];
  expect(await first.text()).toContain(`nonce="${nonce}"`);
  // Inject through the HTML parser. DevTools page.evaluate is privileged and
  // cannot establish that a browser enforces CSP against injected markup.
  await page.route("**/login", async (route) => {
    const response = await route.fetch();
    const body = (await response.text()).replace(
      "</head>",
      "<script>window.__pr8_unsigned_script = true</script></head>",
    );
    await route.fulfill({ response, body });
  });
  await page.goto("/login");
  await expect(page.getByRole("button", { name: /Anmelden/i })).toBeVisible();
  expect(await page.evaluate(() => "__pr8_unsigned_script" in window)).toBe(false);
});
