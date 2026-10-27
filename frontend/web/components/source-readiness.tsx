import type { DataSource } from "@/lib/api/market-foundation";

const catalog: Record<string, { markets: string; key: string; limits: string; review: string; documentation: string }> = {
  ECB: { markets: "EUR-Referenzwechselkurse; keine Aktien oder ETFs", key: "Kein API-Key", limits: "Begrenzte Reihen-/Datumsfenster; keine feste Quote hier nachgewiesen", review: "EXR-Reihen, Attribution, Originalarchiv und Ableitungen im Scope dokumentieren.", documentation: "https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html" },
  SEC_EDGAR: { markets: "US-Filer und XBRL/Fundamentals; keine Börsenkurse", key: "Identifizierbarer User-Agent mit Kontakt; kein API-Key", limits: "Herstellermaximum 10 Requests/s je Nutzer über alle Geräte; lokale Grenze kann strenger sein", review: "CIK und Dokumentumfang bestätigen; Rechte an konkreten Drittinhalten und Aufbewahrung prüfen.", documentation: "https://www.sec.gov/about/developer-resources" },
  OPENFIGI: { markets: "Internationale Identifier-/Listingkandidaten; keine Kurse", key: "Optionaler API-Key für höhere Quote", limits: "Mapping 25/min ohne Key, 250/min mit Key; 10/100 Jobs je Request. Search 5/20 pro Minute", review: "Mapping-/Metadatenscope und Lizenzbelege dokumentieren; MIC/Währung und Mehrfachtreffer einzeln prüfen.", documentation: "https://www.openfigi.com/api/documentation" },
  SNB: { markets: "Unterstützte monatliche Referenzreihen; kein täglicher Portfolio-FX-Ersatz", key: "Kein API-Key", limits: "ETag/304 oder Update-Endpunkt verwenden; keine regelmäßigen Vollabrufe zum Polling", review: "Cube, Dimensionen, Frequenz, Attribution, Drittquellen und Analysezweck festhalten.", documentation: "https://data.snb.ch/en/help_api" },
  ALPHAVANTAGE: { markets: "Tägliche Kurse explizit zugeordneter Symbole; CH-/EU-/ETF-Abdeckung nicht pauschal bestätigt", key: "Persönlicher API-Key erforderlich; nur lokal hinterlegen", limits: "Kostenlos regulär 25 Requests/Tag; Endpoint-/Planumfang gesondert prüfen", review: "Persönliche Berechtigung, Langzeitarchiv, Aufbewahrung nach Vertragsende und konkrete Listings bestätigen.", documentation: "https://www.alphavantage.co/terms_of_service/" },
  COMPANY_IR: { markets: "Einzeln freigegebene Emittentenberichte; kein universeller Crawler", key: "Vom konkreten Dienst abhängig", limits: "Je Host und Dokumentvertrag festzulegen", review: "Automatik, Originalspeicherung, Aufbewahrung und Analyse/RAG je Host und Dokument belegen.", documentation: "" },
  NEWS_RSS: { markets: "Metadaten/Links einzeln freigegebener Feeds; kein pauschales Artikelarchiv", key: "Vom konkreten Feed abhängig", limits: "Feedvertrag und Updatefrequenz einzeln prüfen", review: "Metadaten und Volltextrechte, Retention, Attribution und Ableitungen getrennt prüfen.", documentation: "" },
};

function gateReason(source: DataSource) {
  if (source.gate_status === "BLOCKED") return "Diese Quelle ist gesperrt. Passenden Nutzungsbeleg durch eine autorisierte Betreiberperson prüfen lassen oder eine zulässige Datei importieren.";
  if (source.gate_status !== "APPROVED") return "Die Rechteentscheidung fehlt. Belege und konkreten Scope dokumentieren; anschließend getrennt über die Aktivierung entscheiden.";
  if (!source.enabled) return "Die Rechteentscheidung ist vorhanden, die Quelle aber deaktiviert. Vor einer separaten Aktivierung Scope und Prüffrist kontrollieren.";
  if (source.gate_reason) return "Die aktivierte Quelle erfüllt derzeit nicht alle Nutzungsbedingungen ihres lokalen Gates. Prüffrist, Scope und erlaubte Datennutzung kontrollieren.";
  return "Der aktuelle Quellenstatus ersetzt nicht die Prüfung von Scope, Instrumentidentität und Datenqualität für jeden einzelnen Auftrag.";
}

export function SourceReadiness({ source }: { source: DataSource }) {
  const facts = catalog[source.slug];
  return <section className="mt-4 space-y-3 rounded border border-zinc-700 p-4" aria-label={`Bereitschaft ${source.slug}`}>
    <p>{gateReason(source)}</p>
    {facts && <>
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div><dt className="ui-muted">Märkte und Grenzen</dt><dd>{facts.markets}</dd></div>
        <div><dt className="ui-muted">Zugang</dt><dd>{facts.key}</dd></div>
        <div><dt className="ui-muted">Herstellerlimits</dt><dd>{facts.limits}</dd></div>
        <div><dt className="ui-muted">Technischer Adapter</dt><dd>Implementiert und mit lokalen Fixtures geprüft. Ein echter Abruf ist separat nachzuweisen.</dd></div>
      </dl>
      <p className="text-sm"><strong>Nächster Rechteprüfpunkt:</strong> {facts.review}</p>
      <p className="text-xs ui-muted">Dokumentationsstand 26.10.2026; keine Operatorfreigabe. {facts.documentation && <a className="underline" href={facts.documentation} target="_blank" rel="noreferrer">Primärdokumentation</a>}</p>
    </>}
    <p className="text-sm ui-muted">Ein erfolgreicher Importzeitpunkt ist ein Betriebsbeleg. Er bestätigt allein weder vollständige Live-Abnahme noch tägliche Markt- oder Corporate-Action-Abdeckung.</p>
    {source.gate_reason && <details className="text-xs"><summary>Gate-Code</summary>{source.gate_reason}</details>}
  </section>;
}
