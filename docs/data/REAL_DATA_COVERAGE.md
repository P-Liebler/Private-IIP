# Reale Datenabdeckung

Stand 2026-10-16. PR1 importiert keine ungefragt freigegebenen externen Daten. Vorhandene synthetische Akzeptanzbestände bleiben von echter Marktcoverage getrennt. **Kein quantitatives reales Coverage-Prozent wird aus Testbeständen berechnet.**

Die geschützte Instrumentenseite und `/data-operations` zeigen über `DataCoverageService` instrument-/zeitraumbezogene erwartete und gültige Sitzungen, Lücken, OHLC/Open/Volumen, Quarantäne, Action-Review, FX-Anforderungen, Fundamentalperioden, Restatements, historische Membership und zeitgerechte Verfügbarkeit. Unbekannter Kalender bedeutet unbekannte erwartete Sitzungen, nicht null fehlende Daten. Status: UNAVAILABLE, PARTIAL, RECONSTRUCTED_RESEARCH_ONLY oder STRICT_PIT_READY nach dokumentierten Regeln; zusätzliche Dataset-/Modellgates bleiben bestehen.

Priorität für künftige reale Proben: eigene Bestandsinstrumente, eigene Watchlists, explizite Benchmarks, kleine geprüfte Universes. Kein globaler unkontrollierter Backfill. Für jede reale Probe Quelle, Instrument/Serie, verlangter/erhaltener Zeitraum, Requestzahl, SHA-256, Original-IDs, neue/korrigierte Versionen, Fehler/Quarantäne und Coverage-Bericht archivieren. Ein knappes Providerfenster zählt nicht als vollständige verlangte Historie.

Aktuelle reale Produkt-Smokes:

| Datentyp | Ergebnis | Alternative |
| --- | --- | --- |
| US-Filing/Facts | SOURCE_NOT_APPROVED | Geprüfter lokaler Research-Import nach eigenem Rechte-Gate |
| ECB-FX | SOURCE_NOT_APPROVED | Rechtmässige manuelle FX-Datei |
| SNB-Makro | SOURCE_NOT_APPROVED | Eigener manueller Makroimport nach MANUAL_PIT-Freigabe |
| OpenFIGI | SOURCE_NOT_APPROVED | Explizit geprüfte interne Identifierpflege |
| Aktienkurse | SOURCE_NOT_APPROVED | Eigene zulässige CSV-Datei; keine gefälschten Ersatzkurse |

Ein Operator kann nach tatsächlicher Rechteentscheidung einen begrenzten Backfill über Vorschau → Start → Fortschritt → Qualitätsprüfung ausführen. Ein solcher Auftrag ist zugleich der kontrollierte Produkt-Smoke; normale CI führt ihn nie gegen einen realen Provider aus.
