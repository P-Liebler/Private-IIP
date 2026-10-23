# PR5C – Praktische Marktdatenversorgung

Prüfdatum: 22.10.2026. **Manueller Workflow implementiert; automatische Echtdatenversorgung nicht freigegeben.**

## Nutzbarer Weg

Die vorhandene Importseite bietet leere Vorlagen für Tageskurse, tägliche FX und Corporate Actions sowie Hinweise zu Datum, Währung, Schlusskursen, FX-Richtung und rechtmäßiger Herkunft. Sie verwendet die bestehenden Preview-/Commit-APIs und den Quellen-Gate. Fehlende oder veraltete Daten bleiben sichtbar; monatliche SNB-Referenzen werden niemals als tägliche Portfolio-FX verwendet.

Positionen zeigen Quelle, Beobachtungszeitpunkt, Kursdatum, Alter, Tages-Schlusskurscharakter und FX-Herkunft. Zustände unterscheiden fehlend, veraltet, historisch und verzögerten Tageskurs. Ein Kurs wird nicht als handelbarer Livepreis dargestellt. Quelle gesperrt und manueller Import sind getrennte Zustände. Datenqualitätsprobleme verlinken die passende Korrektur im bestehenden Workflow.

Vorhandene begrenzte Collector-Jobs, Holdings-Coverage und Fehleranzeigen bleiben die Automatisierungsgrundlage. Aktivierung benötigt weiterhin dokumentiertes Nutzungsrecht, separate Aktivierung und passenden Datenumfang. Globale regelmäßige Sammlung bleibt aus. PR5 aktiviert keine reale Quelle und führt keine Finanzprovider-API-Abfrage in Tests aus.

## Primärquellenprüfung

Dokumentation am 21./22.10.2026 geprüft. Bedingungen können sich ändern; dieser Review ersetzt keine Freigabe im versionierten Source-Gate. Das reale Portfolio und seine Instrumentliste liegen nicht vor. Vollständige CH-/US-/ETF-Abdeckung ist deshalb nicht nachgewiesen.

| Quelle | Eignung und Rechteprüfung | Entscheidung |
| --- | --- | --- |
| Yahoo | Priorisierte Kursquelle unter Freigabevorbehalt. Automatisierte Sammlung verlangt ausdrückliche Erlaubnis gemäß [Nutzungsbedingungen](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html). Historie, Splits/Dividenden und Archivierung benötigen zusätzlich passende Rechte. | Weiterhin BLOCKED/aus; keine Voraussetzung für manuellen Betrieb. |
| ECB | Tägliche EUR-Referenzkurse für unterstützte Währungen, keine Aktien-/ETF-Kurse. [Copyright](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html): Quellenangabe, unverfälschte Darstellung und Drittparteirechte beachten. API-Hilfeseite lieferte beim Review HTTP 503; die Schnittstellenprüfung ist daher unvollständig. | Bestehender Adapter, UNKNOWN/aus; kein aktueller Live-Abrufnachweis. |
| SNB | Makro-/Referenzdaten. [Nutzungsbedingungen](https://www.snb.ch/en/srv/disclaimer_copyright): zweckgebundene nichtkommerzielle Nutzung mit Quelle und Drittparteirechten. Bestehende monatliche Beobachtungen sind keine tägliche Bewertungs-FX. | UNKNOWN/aus; keine Substitution täglicher FX. |
| SEC EDGAR | US-Unternehmensmeldungen/Fundamentals, keine Aktienkurse oder Portfolio-FX. [Zugriff](https://www.sec.gov/about/developer-resources): identifizierbarer Bot und höchstens 10 Requests/Sekunde über alle Rechner, effizient abfragen. | Bestehender Fundamentals-Adapter, UNKNOWN/aus. |
| OpenFIGI | [Mapping-API](https://www.openfigi.com/api/documentation): keyless 25 Requests/Minute, bis 10 Jobs/Request; Identität, keine Kurse. Mehrdeutige Treffer werden nicht automatisch akzeptiert. | UNKNOWN/aus; keine Marktdatenversorgung. |
| Alpha Vantage | [Terms](https://www.alphavantage.co/terms_of_service/): persönliche nichtkommerzielle Nutzung nur im passenden Lizenzumfang. Kostenlose Quoten, Märkte, Historie, Adjustments und dauerhafte unveränderliche Speicherung sind nicht pauschal nachgewiesen. | Vorhandener Adapter bleibt UNKNOWN/aus; kein neuer Schlüssel oder Tarif. |
| Twelve Data | [Terms](https://twelvedata.com/terms), [Tarife](https://twelvedata.com/pricing), [Credits](https://support.twelvedata.com/en/articles/5615854-credits): Märkte, Non-Display, Speicherung und Abrufgewicht hängen vom Tarif ab. §16 erlaubt Aufbewahrung nur im Lizenzumfang und verlangt nach Vertragsende grundsätzlich Löschung binnen 30 Tagen. Unbegrenzte immutable Archivierung wird nicht unterstellt. | Kein Adapter oder Konto hinzugefügt; ungeklärte Archiv-/CH-/ETF-Rechte verhindern Freigabe. |
| Eigene CSV | Eigener rechtmäßig bereitgestellter Export mit dokumentierter Herkunft; keine implizite Übernahme von Rechten eines Datenverkäufers. Originalbytes und Versionen bleiben erhalten. | Praktischer Fallback; MANUAL_CSV bleibt unter seinem bestehenden Gate. |

## Abnahme

Synthetische API-/Browserdaten prüfen echte Import-, Bewertungs- und Fehlerpfade, keine reale Marktabdeckung. Ein täglicher Scheduler-Pass, echte Corporate-Action-Abdeckung, Ausfallbeobachtung im Dauerbetrieb und ein realer Portfoliovergleich bleiben offen. Für das erste echte Depot müssen Instrumentliste, zulässige Quellen, Aufbewahrungsrecht, Quote, Zeitzone/Kalender und tägliche FX einzeln bestätigt werden. „0 CHF verpflichtende API-Kosten“ betrifft API-Gebühren; Hardware und Betrieb sind nicht kostenlos.
