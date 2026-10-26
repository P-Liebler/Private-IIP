"use client";

import Link from "next/link";
import type { Valuation } from "@/lib/api/portfolios";
import { EmptyState, FinancialMetric } from "@/components/ui/primitives";

export function PositionHighlights({ valuation }: { valuation: Valuation }) {
  const blocked = new Set(valuation.issues.filter(i => ["UNVERIFIED_CORPORATE_ACTION", "DELISTED_POSITION_REVIEW"].includes(i.code)).map(i => i.instrument_id));
  const ranked = valuation.holdings.filter(h => h.valuation_status === "CURRENT" && h.unrealized_pnl_base_at_valuation_fx != null && !blocked.has(h.instrument_id)).sort((a, b) => Number(b.unrealized_pnl_base_at_valuation_fx) - Number(a.unrealized_pnl_base_at_valuation_fx));
  return <section className="ui-panel space-y-4"><h2 className="text-xl font-semibold">Positionen mit der höchsten und niedrigsten Veränderung</h2><p className="text-xs ui-muted">Vorläufiger unrealisierter Wertunterschied gegenüber bekanntem Einstand in {valuation.base_currency}, umgerechnet mit Bewertungs-FX. Keine Tagesrendite oder Empfehlung. Unbewertbare Positionen werden ausgeschlossen; Dividenden-/Split-Vollständigkeit bleibt Voraussetzung belastbarer Renditen.</p>
    {ranked.length === 0 ? <EmptyState title="Noch kein belastbarer Positionsvergleich" description="Aktuelle Kurse, passende FX und bekannte Einstandswerte werden benötigt. Ungeprüfte bekannte Kapitalmaßnahmen sperren die betroffene Position." /> : <div className="grid gap-4 sm:grid-cols-2">{(ranked.length === 1 ? [ranked[0]] : [ranked[0], ranked[ranked.length - 1]]).map((h, i) => <article key={`${h.account_id}-${h.instrument_id}`} className="rounded-xl border border-zinc-800 p-4"><p className="text-xs ui-muted">{ranked.length === 1 ? "Einzige aktuell vergleichbare Position" : i === 0 ? "Höchster Wertunterschied" : "Niedrigster Wertunterschied"}</p><Link href={`/instrument/${h.instrument_id}`} className="mt-2 block font-semibold underline">{h.name}</Link><p className="mt-3 text-xl"><FinancialMetric value={h.unrealized_pnl_base_at_valuation_fx} currency={valuation.base_currency} semantic /></p><p className="text-xs ui-muted">Schlusskurs vom {h.price_date}</p></article>)}</div>}
  </section>;
}
