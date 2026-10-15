# Structured Recommendations (P9)

## Vertrag und Gates

Quantitative, deterministische Regeln entscheiden. Es gibt keinen LLM-Entscheidungspfad und keinen Transaktionsaufruf. `RecommendationEligibilityService` trennt `permitted` und fachliche Kategorie. Fehlende Pflichtdaten ergeben `INSUFFICIENT_DATA`; harte Ausschlüsse beziehungsweise Grenzverletzungen `INELIGIBLE`. Beide Zustände enthalten keine freigegebene Handlungsempfehlung. Ein Score wird erst nach bestandenen Gates berechnet.

Die Engine verlangt bestätigte Präferenzen, handelbares Instrument mit Börse, aktuelle Kurse/FX, verifizierte Actions, mindestens 252 vollständige Risiko-Beobachtungen, vollständige Quality-/Value-Rubriken, Produktionsforecast, separate Strategieabnahme, vollständige Portfolio-NAV, aktuellen passenden P8-Snapshot, Volatilität/Drawdown/VaR/CVaR, benötigte Korrelationen, sieben belegte Szenariovergleiche, Liquidität und prüfbare Limits. P7 erzeugt den Forecast neu und prüft damit aktuelle Membership, Features, Kalibrierung und Artefakte. P9 prüft zusätzlich aktuelle PRODUCTION-Reviews aller verwendeten Modelle, reale Strict-PIT-Promotionsevidenz, maximal 24 Stunden Alter, Intervallbreite maximal 0.50 und OOS-Deckung mindestens 0.85. Das sind konservative Ausgangsgrenzen, keine bewiesenen optimalen Werte.

Ohne Produktionsforecast wird `NO_VALIDATED_PRODUCTION_FORECAST` gespeichert. SHADOW-, synthetische oder rekonstruierte Modellnachweise ersetzen dieses Gate nicht. Risikoanalysen dürfen unabhängig davon verfügbar bleiben.

## Kandidaten und Kontext

Maximal 20 Kandidaten einschließlich Beständen; private Watchlists und Universes werden auf Eigentum geprüft. Ein Kandidat ist noch keine Empfehlung. Keine globale Providerliste, keine externe Finanzabfrage. Profilpräferenzen, P4-NAV, P8-Risiko, P5-Research und P7-Prognose werden referenziert. `RiskMarket.liquidity` wird von P8 und neuen What-if-Kandidaten gemeinsam verwendet. Fehlende Daten bleiben null und sind kein Durchschnittswert.

Hypothesen verwenden `RiskSimulationService.whatif`, einschließlich Cashprüfung, FX, Gebühren, Spread, Slippage und sieben Szenarien. Modi: fixer Basiswährungsbetrag, NAV-Anteil, Zielgewicht. Hypothetische Ergebnisse sind ausdrücklich keine realisierte Performance und verändern keine P4-Buchung. Die Vergleichsprüfung berücksichtigt aktuelle Transaktions-IDs, native Bestände/Cash, Preisversionen, Basiswerte und FX-Raten; ein nicht mehr passender Risiko-Snapshot sperrt die Bewertung.

## Feste Bewertungsregel v1

Alle Komponenten werden auf 0–100 begrenzt. Gewichte: Excess Return 0.25, Forecast-Konfidenz 0.15, Quality 0.20, Value 0.15, Momentum 0.05; Abzüge Risiko 0.08, Konzentration 0.05, Korrelation 0.04 und Kosten 0.03. Excess Return wird als `50+500*r` skaliert, Outperformance-Wahrscheinlichkeit mit 100 multipliziert, Jahresvolatilität mit 200, größte Positionskonzentration und maximale positive Peer-Korrelation mit 100. Kostenkomponente: `10000*Kosten/Betrag`. Keine Peer-Marktperzentile und keine Optimierungsbehauptung.

Nur Momentum ist optional; ohne Momentum entfällt sein Beitrag ohne Umgewichtung. Fehlende Pflichtkomponenten setzen den Score aus. Kategorien: Score ≥55 `CONSIDER_INCREASE`; vorhandener Bestand und Score ≥35 `HOLD`; Score ≥20 `WATCH`; darunter für Bestand `REVIEW_REDUCE`, sonst `AVOID_NEW_EXPOSURE`. Harte Grenzen haben Vorrang vor sämtlichen Kategorien.

Regelname, Gewichte, Missing Policy und Gates stehen in einem unveränderlichen Registry-Record. Eine Änderung erfordert eine neue Regelversion und eigene historische Abnahme. Profil- und Regeländerungen überschreiben niemals bestehende Bewertungen.

## Speicherung und API

Migration 0015 ergänzt fünf Tabellen. Recommendations speichern auch Abstentions mit Zeitpunkt, Instrument, Portfolio/P4-/P8-/P5-/P7-/Profil-/Regelreferenzen, vollständigem Inputmanifest und SHA-256, Gate-Ergebnis, Komponenten, Kategorie und maschinenlesbarer Erklärung. PostgreSQL blockiert UPDATE. Replay nutzt ausschließlich das gespeicherte Manifest und prüft den ursprünglichen Ergebnisinhalt; Listen werden stabil sortiert.

Geschützt: GET/PATCH `/investment-profile`; GET `/recommendations`, `/history`, `/eligibility`, `/strategies`, `/{id}`; POST `/recommendations/evaluate`, `/backtests`, `/strategy-reviews`, `/{id}/replay`. Private Daten sind nutzergebunden. Historie: maximal 100 Zusammenfassungen pro Seite; Details einzeln. Bewertungen maximal 120 Sekunden, maximal 20 Kandidaten. Kein Endpoint schreibt Transaktionen.

Die geschützte Seite `/recommendations` zeigt Freigabestatus, Profilversion/Einheiten, Bestände, Kandidatenbetrag, Eligibility, fehlende Eingaben, Risiko/Kosten, Referenzen und unveränderliche Historie. Ohne Strategieabnahme bleibt der Hinweis `NO VALIDATED INVESTMENT RECOMMENDATIONS` sichtbar.
