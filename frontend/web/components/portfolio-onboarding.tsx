"use client";

import Link from "next/link";
import type { Account, Transaction, Valuation } from "@/lib/api/portfolios";

export function PortfolioOnboarding({ accounts, transactions, valuation, navigate }: {
  accounts: Account[]; transactions: Transaction[]; valuation?: Valuation;
  navigate: (tab: string, anchor?: string) => void;
}) {
  const active = accounts.filter(a => !a.archived_at);
  return <section className="rounded-xl border border-zinc-800 p-5">
    <p className="text-sm text-amber-400">Lokaler Beta-Workflow · Nutzung mit echten privaten Finanzdaten noch nicht freigegeben.</p>
    <h2 className="mt-2 text-xl font-semibold">Portfolio einrichten</h2>
    <p className="mt-2 text-sm text-zinc-400">Auch ohne externe Datenquelle nutzbar. Eigene zulässige Dateien verwenden; fehlende Kurse und FX bleiben sichtbar. Prognosen sind SHADOW, Empfehlungen gesperrt.</p>
    <ol className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <li>1. Portfolio erstellt<br /><span className="text-sm text-zinc-400">Basiswährung: {valuation?.base_currency ?? "wird geladen"}</span></li>
      <li>2. Konto oder Depot<br /><button className="text-emerald-400 underline" onClick={() => navigate("Transaktionen", "account-setup")}>{active.length ? `${active.length} Konto/Konten prüfen` : "Konto einrichten"}</button></li>
      <li>3. Startbestand oder Historie<br /><button className="text-emerald-400 underline" onClick={() => navigate("Transaktionen", "transaction-entry")}>Cash / Eröffnungsposition erfassen</button></li>
      <li>4. Transaktionen<br /><button className="text-emerald-400 underline" onClick={() => navigate("Transaktionen", "transaction-import")}>CSV-Vorschau öffnen</button><p className="text-xs text-zinc-400">{transactions.filter(t => t.status === "ACTIVE").length} aktive Buchungen</p></li>
      <li>5. Instrumente<br /><Link className="text-emerald-400 underline" href="/instruments">ISIN, Börse/MIC und Währung prüfen</Link></li>
      <li>6. Kurse und FX<br /><Link className="text-emerald-400 underline" href="/imports">Kurs- oder FX-Datei importieren</Link></li>
      <li>7. Qualität und Auszug<br /><button className="text-emerald-400 underline" onClick={() => navigate("Datenqualität")}>Offene Datenprobleme</button><br /><button className="text-emerald-400 underline" onClick={() => navigate("Depotabgleich")}>Mit Auszug vergleichen</button></li>
      <li>8. Portfolioübersicht<br /><button className="text-emerald-400 underline" onClick={() => navigate("Übersicht")}>Bewertung öffnen</button><p className="text-xs text-zinc-400">{valuation?.status ?? "Bewertung wird geladen"}</p></li>
    </ol>
  </section>;
}
