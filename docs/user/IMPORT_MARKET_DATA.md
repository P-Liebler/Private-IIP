# Kurse, FX und Corporate Actions

Unter **CSV-Import** den Datentyp wählen und eine leere Vorlage herunterladen. Zulässige eigene Originaldateien verwenden: UTF-8, Komma, ISO-Datum, Dezimalpunkt. Das Original wird vor der kanonischen Verarbeitung unveränderlich mit Herkunft und Hash gespeichert.

| Typ | Benötigte Inhalte | Bedeutung |
|---|---|---|
| Tageskurse | Datum, passende ISIN/FIGI/eindeutiger Ticker, Schlusskurs, Währung | Schlusskurs des dokumentierten Handelstags; kein Livepreis. Open/High/Low/Volume nur ergänzen, wenn belegt |
| Wechselkurse | Datum, Basiswährung, Zielwährung, Rate | `1 × base_currency = rate × quote_currency`. Nur geeignete tägliche Referenzen; keine Monatswerte als Tagesfixing deklarieren |
| Corporate Actions | Datum, Kennung, SPLIT/DIVIDEND, Verhältnis bzw. Betrag je Aktie, belegte Zahlungs-/Herkunftsangaben | Eine eingelesene Action ist noch keine zusätzliche Dividendenbuchung; im Portfolio prüfen und ausdrücklich anwenden/adoptieren |

Vorschau, Zuordnung, Fehler und Warnungen prüfen. Erst nach Bestätigung übernehmen. Eine bewusste Konfliktentscheidung benötigt eine Begründung; korrigierte Originale/Versionen bleiben erhalten. Ungültige Werte werden nicht durch Quality Scores gerettet.

## Quellen und Aktualisierung

Die tägliche Versorgung konzentriert sich auf vorhandene Positionen und eine kleine Watchlist. **Datenquellen** zeigt tatsächliche Registry-Gates. **Datenbetrieb** zeigt verfügbare Collector-Aufträge, letzte Erfolge/Fehler, begrenzte Intervalle, Quoten und Wiederholungen. Nur ein berechtigter Operator kann nach belegter Rechteprüfung separat aktivieren und einen begrenzten Einzelauftrag starten. Globale Collection bleibt standardmäßig aus.

ECB ist ein vorbereiteter Kandidat für tägliche EUR-Referenzen; die vorhandene P3-Engine kann zulässige Kreuzkurse mit Herkunft ableiten. Es wurde noch kein realer ECB-Produktabruf abgenommen. SEC liefert Filings/Fundamentals, OpenFIGI Identitätsmetadaten – beides ersetzt keine Aktienkurse. SNB-Monatsserien ersetzen keine täglichen Portfolio-FX-Daten.

Yahoo bleibt gesperrt. Kostenlose technische Angebote anderer Anbieter beweisen weder CH-/ETF-Abdeckung noch unbegrenzte Speicherrechte. Ohne geeigneten freigegebenen Endpunkt gültige manuelle Originale importieren; Störungen und fehlende tägliche Aktualisierung bleiben sichtbar. Keine unerlaubten Scraper oder beliebigen unkontrollierten URL-Fallbacks.

Ein gültiger heutiger Import beweist keine historische lokale Verfügbarkeit. Ein einzelner Split, eine einzelne Dividende oder eine leere Liste beweist keine vollständige Action-Abdeckung.
