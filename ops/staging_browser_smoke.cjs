/* Local CSP/hydration test only. A temporary SPKI pin is not OS/client CA trust. */
const { createRequire } = require("node:module");
const { resolve } = require("node:path");
const { readFileSync } = require("node:fs");
const { X509Certificate, createHash } = require("node:crypto");
const tls = require("node:tls");
const playwrightRequire = createRequire(resolve("backups/p6-browser-runner/package.json"));
const { chromium } = playwrightRequire("@playwright/test");

async function main() {
  if (!process.env.RESTORE_TEST_PASSWORD) throw new Error("Explicit fixture password required");
  const bytes = readFileSync("backups/pr3-staging-fixture.json");
  const fixture = JSON.parse(bytes.toString(bytes[0] === 255 ? "utf16le" : "utf8").replace(/^\uFEFF/, ""));
  if (!fixture.username.startsWith("restore_")) throw new Error("Disposable fixture required");
  const leaf = await new Promise((resolveCertificate, reject) => {
    const socket = tls.connect({ host: "localhost", port: 443, servername: "localhost", ca: readFileSync("backups/pr3-staging-ca.crt"), rejectUnauthorized: true }, () => {
      resolveCertificate(new X509Certificate(socket.getPeerCertificate().raw));
      socket.end();
    });
    socket.on("error", reject);
    socket.setTimeout(10000, () => socket.destroy(new Error("TLS timeout")));
  });
  const pin = createHash("sha256").update(leaf.publicKey.export({ type: "spki", format: "der" })).digest("base64");
  const browser = await chromium.launch({ headless: true, args: [`--ignore-certificate-errors-spki-list=${pin}`] });
  let pageErrors = 0;
  let cspErrors = 0;
  try {
    const page = await browser.newPage({ ignoreHTTPSErrors: false });
    page.on("pageerror", () => pageErrors++);
    page.on("console", message => {
      if (message.type() === "error" && /content.security.policy|violates.*directive/i.test(message.text())) cspErrors++;
    });
    const response = await page.goto("https://localhost/login");
    if (!response?.headers()["content-security-policy"]?.includes("object-src 'none'")) throw new Error("CSP missing");
    await page.getByLabel("Benutzername", { exact: true }).fill(fixture.username);
    await page.getByLabel("Passwort", { exact: true }).fill(process.env.RESTORE_TEST_PASSWORD);
    await page.getByRole("button", { name: "Anmelden", exact: true }).click();
    await page.waitForURL("**/dashboard", { timeout: 30000 });
    await page.goto(`https://localhost/portfolios/${fixture.portfolio_id}`);
    await page.goto(`https://localhost/instrument/${fixture.instrument_id}`);
    await page.getByRole("button", { name: "Abmelden", exact: true }).click();
    await page.waitForURL("**/login", { timeout: 30000 });
    if (pageErrors || cspErrors) throw new Error("Browser/CSP error");
    console.log(JSON.stringify({ passed: true, scope: "LOCAL_STAGING_CSP_AND_HYDRATION", trust_scope: "TEMPORARY_SPKI_PIN_ONLY_NOT_CLIENT_OS_TRUST", page_errors: pageErrors, csp_errors: cspErrors }));
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.log(JSON.stringify({ passed: false, error_type: error.constructor.name, diagnostic: error.message.split("\n")[0], scope: "LOCAL_STAGING_CSP_AND_HYDRATION" }));
  process.exitCode = 1;
});
