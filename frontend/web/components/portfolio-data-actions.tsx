import Link from "next/link";
import type { Holding, Valuation } from "@/lib/api/portfolios";

const explanations: Record<string, string> = {
  MISSING_PRICE: "Es fehlt ein gültiger Schlusskurs.", STALE_PRICE: "Der letzte Kurs ist für eine vollständige Bewertung zu alt.",
  MISSING_FX: "Es fehlt ein ausreichend aktueller Währungsreferenzkurs.", MISSING_EVENT_FX: "Für ein früheres Ereignis fehlt die passende FX-Referenz.",
  MISSING_EVENT_PRICE: "Nach einem Split oder einer Dividende wird ein Kurs in der passenden Einheit benötigt.",
  UNVERIFIED_CORPORATE_ACTION: "Eine bekannte Corporate Action ist noch nicht geprüft oder angewandt.",
  UNKNOWN_COST_BASIS: "Der Einstand ist unbekannt. Ohne Beleg wird kein Gewinn errechnet.",
  UNKNOWN_REALIZED_COST_BASIS: "Der realisierte Gewinn ist wegen unbekannter historischer Kosten nicht verfügbar.",
  NEGATIVE_CASH: "Der gebuchte Cashbestand ist negativ. Finanzierung oder fehlende Buchungen mit dem Auszug prüfen.",
};

export function HoldingProvenance({ holding }: { holding: Holding }) {
  return <div className="mt-3 space-y-1 text-sm text-zinc-400">
    <p>{holding.market_data_state ?? holding.valuation_status} · Tages-Schlusskurs, kein handelbarer Livepreis. Quelle: {holding.price_source_name ?? "nicht verfügbar"} · Kurswährung {holding.currency}.</p>
    <p>Lokale Kurserfassung: {holding.price_observed_at ?? "nicht verfügbar"} · Aktualisierung: {holding.collection_state ?? "Quellenfreigabe prüfen"}.</p>
    <p>FX {holding.fx.rate ?? "nicht verfügbar"} · Referenz {holding.fx.rate_date ?? "nicht verfügbar"} · Quelle {holding.fx.derived === "IDENTITY" ? "Identität, keine Umrechnung" : holding.fx.source_names?.join(", ") || "nicht verfügbar"} · {holding.fx.derived ?? "Umrechnung fehlt"}.</p>
  </div>;
}

export function PortfolioDataActions({ valuation, transactions }: { valuation: Valuation; transactions: () => void }) {
  return <section className="space-y-3 rounded-xl border border-zinc-800 p-5">
    <h2 className="text-xl font-semibold">Nächste Schritte zur Datenqualität</h2>
    <p className="text-sm text-zinc-400">Bewertung berechnet: {valuation.as_of ?? "nicht verfügbar"} · Bewertungsstichtag {valuation.on_date}. Kursstände stehen je Position; die Berechnungszeit ist kein neuer Börsenkurs.</p>
    <ul className="space-y-2">{valuation.issues.map((issue, n) => <li key={n}><strong>{issue.instrument_id ? valuation.holdings.find(h => h.instrument_id === issue.instrument_id)?.name ?? "Instrument prüfen" : issue.currency ?? "Portfolio"}</strong>: {explanations[issue.code] ?? issue.code}</li>)}</ul>
    <div className="flex flex-wrap gap-4"><Link className="text-emerald-400 underline" href="/imports">Kurse / FX / Corporate Actions importieren</Link><Link className="text-emerald-400 underline" href="/instruments">Instrument zuordnen</Link><button className="text-emerald-400 underline" onClick={transactions}>Buchung oder Startbestand prüfen</button><Link className="text-emerald-400 underline" href="/settings/data-sources">Quellenrechte und Aktualisierung prüfen</Link></div>
    <p className="text-sm text-zinc-400">Eine leere Action-Liste beweist keine vollständige Split-/Dividendenabdeckung. Automatische tägliche Versorgung ist ohne freigegebenen, tatsächlich getesteten Endpunkt nicht abgenommen. Bei Quellenstörung gültige manuelle Originale importieren; nichts schätzen.</p>
  </section>;
}
