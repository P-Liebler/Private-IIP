# PR6D – Dashboard und lokale Prüfnachweise

Abgleich 26.10.2026. **LOCALLY_TESTED_WITH_DATA_LIMITS**. Vollständige Regression vom 23.10.; zusätzliche Normalmodus-Sichtprüfung vom 26.10. Keine reale Portfolioabnahme.

## Berechnungsvertrag

Die additive `chf_summary` der bestehenden Dashboard-API bewertet die ursprünglichen Ledgerdaten mit CHF als Berichtswährung neu. Native Gruppen bleiben erhalten. Aktuelle Positionen/Cash verwenden Bewertungs-FX; Geldflüsse und Ereignisse behalten ihre jeweiligen historischen Referenzen. Ein gemeinsam gesetzter Wissensstichtag gilt für die Aggregation. Es wird weder eine native Fremdwährungssumme als CHF ausgegeben noch ein heutiger FX-Kurs auf einen gesamten historischen Gewinn angewendet. Bei keinem Portfolio bleibt die CHF-Zusammenfassung `null`; bei fehlenden Daten bleiben betroffene Summen `null`.

Integrationstest mit isolierten synthetischen Buchungen und FX: 100 USD Einzahlung bei 0.80 CHF/USD, Vortagsreferenz 0.85 und Bewertungsreferenz 0.90 ergeben 90 CHF Cashwert, 10 CHF Gesamtertrag und 5 CHF Tagesveränderung. Die native USD-Sicht bleibt 100 USD und 0 USD Ertrag. Diese Zahlen sind ausschließlich Testwerte.

## Oberfläche

Vier priorisierte CHF-Kennzahlen, Datenstand, expliziter Teilwert, Portfolioauswahl, Verlauf, Aufteilung, filter-/sortierbare Positionen mit mobiler Kartenansicht, Herkunftsdrawer, vorläufiger Positionsvergleich, letzte Buchungen, archivierte Benachrichtigungen und konkrete Datenaktionen sind verbunden. Unbekannte Einstandswerte erzeugen keinen Gewinn. Vergleiche schließen unbewertbare Positionen und bekannte ungeprüfte Kapitalmaßnahmen aus; vorläufiger unrealisierter Wertunterschied ist keine Tagesrendite oder Empfehlung.

TradingView ersetzt die einfachen Linien-SVGs; explizite Nullbeobachtungen trennen Segmente. Auf Instrumentseiten ergänzt der bestehende Börsenkalender abgeschlossene Handelstage ohne Kurs als Lücke; Wochenenden und eine noch offene Sitzung werden nicht als fehlender Schlusskurs erfunden. Bei unbekanntem Kalender sind nur beobachtete Punkte zulässig. Ein Unitfall für SIX bestätigt diese Unterscheidung. Eine Datentabelle bleibt erreichbar; Themefarben werden berechnet übernommen.

## Analysen, Messungen und Grenzen

Rendite, Benchmark und Drawdown werden inzwischen mit `P8_PINNED_RETURN_CHARTS_V1` ausschließlich aus gespeicherten P8-Beobachtungen mit Decimal abgeleitet. Unvollständige Renditen sperren die Kurven; fehlende Benchmark bleibt fehlend. Originalsnapshots werden nicht verändert. Zwei zusätzliche Unitfälle prüfen kumulierte Rendite, Drawdown, Benchmark, Eingabeimmutabilität und die Sperre bei Lücken. Instrumentseiten verbinden kanonische Dividenden/Splits und vorhandene Nachrichten; ein visuelles Prognoseintervall erscheint ausschließlich bei validiertem Forecast. Diese Anzeige erteilt keine Modellfreigabe.

Standalone-Build, 26 unterschiedliche Browserfälle einschließlich tatsächlicher Canvas, Zeitraum-/Themewechsel, Positiondetails und mobile Karten bestanden. Tokenkontrast und Tastaturdialog sind geprüft, keine vollständige WCAG-/Screenreaderabnahme behauptet. 23.10.: Login bis geladenes Dashboard mit Historie 3’843 ms; kleiner CH-CSV-Request 86–92 ms Vorschau / 83 ms Commit. Nach Docker-Wiederanlauf am 26.10. benötigte Login bis Dashboard mit Historie 24’060 ms und Öffnen des Risikopanels samt vorhandener Historienauswahl 6’900 ms. Diese Einzelmessungen unter wechselnder lokaler Last sind keine SLA und kein isolierter Nachweis einer einzelnen langsamen Datenbankabfrage. Reale Aktualisierung, größere Depotlast und unbekannter Zielhost bleiben ungemessen. Ein kostenloser universeller Kursdienst oder echte Portfoliohistorie werden nicht behauptet.
