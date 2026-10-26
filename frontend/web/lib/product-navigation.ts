export type OperatorRole = "data_operator" | "ml_operator" | "operations_operator";
export type Destination = { href: string; label: string; description: string; operator?: OperatorRole };
export type NavigationArea = { id: string; label: string; href: string; destinations: Destination[] };

export const navigation: NavigationArea[] = [
  { id: "overview", label: "Übersicht", href: "/dashboard", destinations: [
    { href: "/dashboard", label: "Persönliche Übersicht", description: "Vermögen, Veränderungen und Ihre nächsten Schritte." },
  ] },
  { id: "portfolio", label: "Portfolio", href: "/portfolios", destinations: [
    { href: "/portfolios", label: "Meine Portfolios", description: "Depots, Positionen, Buchungen und Renditen an einem Ort." },
    { href: "/portfolios/new", label: "Portfolio einrichten", description: "Schritt für Schritt zum ersten Depot." },
  ] },
  { id: "discover", label: "Entdecken", href: "/instruments", destinations: [
    { href: "/instruments", label: "Instrumente", description: "Wertpapiere finden und ihre Identität prüfen." },
    { href: "/watchlists", label: "Watchlists", description: "Eigene Beobachtungslisten mit Notizen." },
    { href: "/research", label: "Research", description: "Fundamentaldaten und nachvollziehbare Bewertungen." },
    { href: "/news", label: "Nachrichten", description: "Archivierte Nachrichten mit ihrer Originalquelle." },
  ] },
  { id: "analysis", label: "Analysen", href: "/analyses", destinations: [
    { href: "/analyses", label: "Analyseübersicht", description: "Risiko, Szenarien und experimentelle Werkzeuge mit ihren Voraussetzungen." },
    { href: "/backtests", label: "Historische Vergleiche", description: "Strategien mit damals verfügbaren Daten vergleichen." },
    { href: "/models", label: "Modelle & Prognosen", description: "Experimentelle Modelle und ihre Grenzen verstehen." },
    { href: "/models/validation", label: "Modellprüfung", description: "Prüfung mit bisher ungesehenen Daten.", operator: "ml_operator" },
    { href: "/models/forward-validation", label: "Prognosen im Testbetrieb", description: "Ab tatsächlicher Erstellung archivierte Testprognosen." },
    { href: "/recommendations", label: "Portfolioentscheidungen", description: "Strukturierte Bewertungen unter strengen Freigaben." },
    { href: "/recommendations/validation", label: "Strategieprüfung", description: "Unabhängige finanzielle Strategievalidierung.", operator: "ml_operator" },
    { href: "/optimizer", label: "Portfolio simulieren", description: "Hypothesen prüfen, ohne Buchungen zu verändern." },
  ] },
  { id: "activity", label: "Aktivitäten", href: "/alerts", destinations: [
    { href: "/alerts", label: "Benachrichtigungen", description: "Hinweise, Regeln und ungelesene Ereignisse." },
    { href: "/imports", label: "Daten importieren", description: "Eigene Kurse, Wechselkurse und Kapitalmaßnahmen prüfen." },
    { href: "/data-operations", label: "Daten aktualisieren", description: "Aufträge, letzte Aktualisierung und Quellenprobleme." },
    { href: "/data-operations/readiness", label: "Historische Datenqualität", description: "Welche Daten für historische Analysen fehlen." },
    { href: "/data-quality", label: "Datenqualität", description: "Fehlende oder widersprüchliche Daten bearbeiten." },
    { href: "/daily-brief", label: "Tagesüberblick", description: "Belegte Zusammenfassung, auch ohne Sprachmodell." },
    { href: "/documents", label: "Meine Dokumente", description: "Eigene zulässige Quellen archivieren und durchsuchen." },
    { href: "/time-machine", label: "Historische Ansicht", description: "Nachweislich verfügbare frühere Datenstände." },
  ] },
  { id: "settings", label: "Einstellungen", href: "/settings", destinations: [
    { href: "/settings", label: "Konto & Darstellung", description: "Konto, Sicherheit, Zeitzone und Erscheinungsbild." },
    { href: "/settings/data-sources", label: "Datenquellen", description: "Verfügbarkeit, Herkunft und benötigte Freigaben." },
    { href: "/system/status", label: "Betriebsstatus", description: "Geschützter Systemzustand und Betreiberfreigaben.", operator: "operations_operator" },
  ] },
];

export function areaFor(path: string): NavigationArea {
  if (path.startsWith("/instrument/")) return navigation[2];
  return navigation.find(area => area.destinations.some(d => path === d.href || (d.href !== "/settings" && path.startsWith(d.href + "/")))) ?? navigation[0];
}

export function destinationFor(path: string): Destination | undefined {
  return navigation.flatMap(a => a.destinations).filter(d => path === d.href).at(0);
}
