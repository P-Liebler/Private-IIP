import { test, expect } from "@playwright/test";

const username=process.env.E2E_USERNAME;
const password=process.env.E2E_PASSWORD;
const instrument=process.env.E2E_RESEARCH_INSTRUMENT_ID;
const missing=process.env.E2E_MISSING_INSTRUMENT_ID;
const apiBase=process.env.E2E_API_BASE_URL??"http://localhost:8000/api/v1";

test("research financials valuation scores and owned watchlist",async({page})=>{
  test.skip(!username||!password||!instrument,"Use explicit local synthetic research fixture");
  await page.goto("/login");await page.getByLabel("Benutzername").fill(username!);await page.getByLabel("Passwort").fill(password!);await page.getByRole("button",{name:"Anmelden"}).click();await page.waitForURL("**/dashboard", {timeout:30000});
  await page.goto("/watchlists");const name=`P5 acceptance ${Date.now()}`;await page.getByLabel("Watchlist Name").fill(name);await page.getByRole("button",{name:"Watchlist erstellen"}).click();await expect(page.getByRole("option",{name})).toBeAttached();
  let watchId:string|undefined;
  try {
    await page.goto("/research");await page.getByLabel("Instrument suchen").fill("Disposable restore test instrument");await page.locator(`a[href="/instrument/${instrument}"]`).click();await expect(page).toHaveURL(new RegExp(`/instrument/${instrument}$`),{timeout:30000});
    await page.getByRole("button",{name:"Financials",exact:true}).click();await expect(page.getByText("revenue",{exact:true}).first()).toBeVisible();await expect(page.getByRole("cell",{name:"1000.000000000000 USD",exact:true})).toBeVisible();
    await page.getByRole("button",{name:"Valuation",exact:true}).click();const peRow=page.getByRole("row").filter({has:page.getByRole("cell",{name:"P/E",exact:true})});await expect(peRow.getByRole("cell").nth(1)).toHaveText(/^12(?:\.0+)?$/);
    await page.getByRole("button",{name:"Scores",exact:true}).click();await expect(page.getByRole("heading",{name:/Quality: /})).toBeVisible();await expect(page.getByText(/Absolute fixed rubric/).first()).toBeVisible();
    await page.getByLabel("Watchlist wählen").selectOption({label:name});await page.getByRole("button",{name:"Zur Watchlist hinzufügen"}).click();await expect(page.getByRole("status")).toHaveText("Zur Watchlist hinzugefügt.");
    await page.goto("/watchlists");await page.getByLabel("Watchlist öffnen").selectOption({label:name});watchId=await page.getByLabel("Watchlist öffnen").inputValue();await expect(page.getByRole("link",{name:"Disposable restore test instrument"})).toBeVisible();
  } finally {const lists=await page.request.get(`${apiBase}/watchlists`);const rows=await lists.json() as {id:string;name:string}[];watchId??=rows.find(row=>row.name===name)?.id;if(watchId)await page.request.patch(`${apiBase}/watchlists/${watchId}`,{data:{archived:true},headers:{Origin:process.env.E2E_BASE_URL??"http://localhost:3000"}});}
});

test("missing fundamentals and disabled sources remain explicit",async({page})=>{
  test.skip(!username||!password||!missing,"Use explicit missing-data instrument");
  await page.goto("/login");await page.getByLabel("Benutzername").fill(username!);await page.getByLabel("Passwort").fill(password!);await page.getByRole("button",{name:"Anmelden"}).click();await page.waitForURL("**/dashboard", {timeout:30000});
  await page.goto(`/instrument/${missing}`);await expect(page.getByText(/Keine validierten Fundamentals/)).toBeVisible();await page.getByRole("button",{name:"Scores",exact:true}).click();await expect(page.getByRole("heading",{name:"Quality: INSUFFICIENT_DATA"})).toBeVisible();
  await page.goto("/research");await expect(page.getByText("SEC_EDGAR: UNKNOWN · deaktiviert")).toBeVisible();
});
