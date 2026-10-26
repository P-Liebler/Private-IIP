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
    <ul className="space-y-3">{valuation.issues.map((issue, n) => {
      const holding = valuation.holdings.find(h => h.instrument_id === issue.instrument_id);
      const fx = issue.code.includes("FX");
      const price = issue.code.includes("PRICE");
      return <li key={n} className="rounded-lg border border-zinc-800 p-4"><strong>{holding?.name ?? issue.currency ?? "Portfolio"}</strong><p className="mt-1">{issue.code === "STALE_PRICE" && holding ? `Der letzte Kurs ist ${holding.price_age_days ?? "unbekannt viele"} Tage alt (vom ${holding.price_date ?? "unbekannten Datum"}). Deshalb ist die aktuelle Bewertung nicht vollständig.` : explanations[issue.code] ?? `Dieser Sachverhalt erfordert eine Prüfung: ${issue.code}.`}</p><p className="mt-2 text-xs text-zinc-400">Betroffener Bewertungsstichtag: {valuation.on_date}. {fx ? "Historische Ereignisse benötigen ihre jeweilige damalige FX-Referenz." : price ? "Ein neuer Abruf kann nur bei passender freigegebener Quelle helfen; ein Kaufpreis ersetzt keinen Marktkurs." : "Bestand und Beleg manuell prüfen; eine fehlende Buchung oder Kapitalmaßnahme wird nicht automatisch erfunden."}</p><div className="mt-3 flex flex-wrap gap-3">{(fx || price) && <Link href={`/imports?kind=${fx ? "fx" : "prices"}`} className="ui-button">{fx ? "FX-Datei importieren" : "Kursdatei importieren"}</Link>}{(fx || price) && <Link href="/data-operations" className="ui-button">Aktualisierung prüfen</Link>}{!fx && !price && <button onClick={transactions} className="ui-button">Buchung / Beleg prüfen</button>}</div><details className="mt-3 text-xs text-zinc-400"><summary>Technischer Prüfcode</summary>{issue.code}</details></li>;
    })}</ul>
    <div className="flex flex-wrap gap-4"><Link className="text-emerald-400 underline" href="/imports">Kurse / FX / Corporate Actions importieren</Link><Link className="text-emerald-400 underline" href="/instruments">Instrument zuordnen</Link><button className="text-emerald-400 underline" onClick={transactions}>Buchung oder Startbestand prüfen</button><Link className="text-emerald-400 underline" href="/settings/data-sources">Quellenrechte und Aktualisierung prüfen</Link></div>
    <p className="text-sm text-zinc-400">Eine leere Action-Liste beweist keine vollständige Split-/Dividendenabdeckung. Automatische tägliche Versorgung ist ohne freigegebenen, tatsächlich getesteten Endpunkt nicht abgenommen. Bei Quellenstörung gültige manuelle Originale importieren; nichts schätzen.</p>
  </section>;
}
