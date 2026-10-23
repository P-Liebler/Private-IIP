"use client";

import type { Allocation, Transaction, Valuation } from "@/lib/api/portfolios";
import { money, ratio } from "@/lib/portfolio-format";

export function PortfolioOverviewDetails({ valuation, transactions, allocation }: {
  valuation: Valuation; transactions: Transaction[]; allocation?: Allocation;
}) {
  const recent = [...transactions].sort((a, b) => b.trade_date.localeCompare(a.trade_date)).slice(0, 8);
  return <section className="grid gap-4 sm:grid-cols-2">
    <p className="text-sm text-zinc-400 sm:col-span-2">Bewertungsstichtag {valuation.on_date} · Wissensstand {valuation.as_of ?? "nicht verfügbar"}. Die einzelnen Kurs- und FX-Zeitpunkte stehen bei den Positionen.</p>
    <article className="rounded-xl border border-zinc-800 p-5"><h2 className="font-semibold">Positionen im Überblick</h2>
      {valuation.holdings.length ? <ul className="mt-3 space-y-2">{valuation.holdings.map(h => <li key={`${h.account_id}-${h.instrument_id}`}>{h.name} · {h.quantity} Stück · {money(h.market_value_base, valuation.base_currency)} · {h.valuation_status}</li>)}</ul> : <p>Keine offenen Positionen.</p>}
    </article>
    <article className="rounded-xl border border-zinc-800 p-5"><h2 className="font-semibold">Allokation nach Anlageklasse</h2>
      {allocation?.status === "COMPLETE" ? <ul className="mt-3">{allocation.by_asset_type?.map(a => <li key={a.asset_type}>{a.asset_type}: {ratio(a.weight)} · {money(a.value, valuation.base_currency)}</li>)}</ul> : <p>Keine vollständige Allokation verfügbar; fehlende Bewertungsdaten zuerst prüfen.</p>}
    </article>
    <article className="rounded-xl border border-zinc-800 p-5 sm:col-span-2"><h2 className="font-semibold">Letzte Transaktionen</h2>
      {recent.length ? <ul className="mt-3 space-y-2">{recent.map(t => <li key={t.id}>{t.trade_date} · {t.type} · {t.instrument_name ?? "Cash-Ereignis"} · {t.quantity ? `${t.quantity} Stück · ` : ""}{t.amount !== null ? money(t.amount, t.currency) : t.price !== null ? `${money(t.price, t.currency)} je Stück` : "Betrag nicht verfügbar"} · {t.status}</li>)}</ul> : <p>Noch keine Transaktionen.</p>}
    </article>
  </section>;
}
