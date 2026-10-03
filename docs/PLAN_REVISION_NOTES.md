# Änderungsnotizen zum Master Development Plan

**Stand:** 2026-10-03  
**Ausgangsfassung:** `Investment_Intelligence_Master_Development_Plan_aktualisiert.md` aus dem Downloads-Ordner; der eingefügte Text ist nach Vereinheitlichung der Zeilenenden inhaltlich identisch.  
**Ergebnis:** [`MASTER_DEVELOPMENT_PLAN.md`](../MASTER_DEVELOPMENT_PLAN.md) mit weiterhin 212 nummerierten Hauptabschnitten.

## Wesentliche Korrekturen

| Thema | Überarbeitete Regel | Abschnitte |
| --- | --- | --- |
| Eine Roadmap | P0–P10 in Abschnitt 158 ist normativ; 204 und 206–211 stimmen damit überein. V1 endet nach Portfolio, Kursen, Corporate Actions, FX und Datenqualität; Research beginnt P5. | 1, 15, 54, 66–69, 158, 171–172, 204, 206–211 |
| Rohdaten und Point-in-Time | MinIO, `raw_ingestion`, Provenienz und Canonical-Versionierung sind vor dem ersten Collector verfügbar. Jede neue Quelle beginnt ihre Snapshot-Historie ab ihrer ersten Nutzung; nicht beobachtete frühere Zustände werden nicht behauptet. | 30–31, 38, 41, 132–133, 158, 189–191 |
| Quellenfreigabe | Yahoo bleibt bevorzugt, ist aber bis zur dokumentierten Prüfung der geltenden Nutzungsrechte gesperrt. Die gleiche Prüfung gilt für Stooq und andere automatisierte Quellen. V1 kann mit einem zulässigen Provider oder validiertem manuellem CSV-Import abgeschlossen werden. | 17–18, 28, 158, 204, 206 |
| Rendite und FX | Rohe Kurse plus validierte Corporate Actions sind die verbindliche Total-Return-Policy; `adjusted_close` ist nur Plausibilitätskontrolle. Fehlende Split-/Dividenden- oder FX-Daten erzeugen einen sichtbaren unvollständigen Zustand. | 38, 59, 153, 158, 189 |
| ML und Empfehlungen | Point-in-Time-Datensatz, Baselines und Backtest-Ausführungsvertrag kommen vor komplexen Modellen. V2 erfordert ein bestandenes Modellgate. Risiko/Szenarien kommen vor Empfehlungen; der Assistent erklärt danach strukturierte Ergebnisse. | 75, 85, 92, 98, 115, 121, 153, 157–158, 192–194, 204, 208–209 |
| Produktionsfreigabe | Caddy/VPN-Zugriff, Grundmonitoring, getrennte Backups und ein erfolgreicher isolierter Restore sind V1-Produktionskriterien. MLflow, Ollama und Loki folgen mit ihrem tatsächlichen Bedarf. | 15, 148, 150, 152, 158, 201, 206 |

## Quellenprüfung am 2026-10-03

- [Yahoo-Nutzungsbedingungen, US-Fassung](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html): automatisiertes Sammeln ohne vorherige ausdrückliche Erlaubnis ist dort untersagt. Vor Aktivierung werden die für den konkreten Einsatz geltende regionale Fassung sowie Abruf- und Speicherrechte geprüft. `yfinance` ist keine eigenständige Datenfreigabe.
- [SEC-Daten-APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) und [SEC Fair Access](https://www.sec.gov/about/developer-resources): Submissions/Company Facts benötigen laut Dokumentation keinen API-Key; die derzeitige Fair-Access-Grenze liegt bei höchstens zehn Anfragen pro Sekunde pro Nutzer über alle Maschinen.
- [OpenFIGI-API](https://www.openfigi.com/api/documentation): die API ist öffentlich und kostenlos; ein Schlüssel erhöht die dokumentierten Limits. Mehrdeutige Identifier-Mappings brauchen fachliche Prüfung.
- [FRED/ALFRED-Dokumentation](https://fred.stlouisfed.org/docs/api/fred/overview.html), [API-Key](https://fred.stlouisfed.org/docs/api/fred/v2/api_key.html): historische Datenstände sind über die API adressierbar; Zugang und Serienrechte werden vor Nutzung geprüft.
- [ECB Data Portal API](https://data.ecb.europa.eu/help/api/overview) und [Datenhistorie](https://data.ecb.europa.eu/help/api/data): SDMX-Webservice; frühere Versionen sind nur insoweit verwendbar, wie die jeweilige Reihe sie tatsächlich bereitstellt.

Diese Angaben sind ein Prüfstand, keine dauerhafte Freigabe. Das Source-Gate in Abschnitt 18 hält die spätere anwendungsspezifische Entscheidung und ihr Prüfdatum fest.

## Abgleich der Fehlerszenarien

Die neue Roadmap nennt einen sichtbaren Zustand für fehlende oder widersprüchliche Kurse, rückwirkende Korrekturen, Split/Dividende, fehlende FX-Werte, unbekannte historische Universe-Membership, Datenleckage und Ausfall von Quelle oder LLM. Für jedes Szenario sind Tests beziehungsweise Freigabegates in den Abschnitten 153, 158 und 206–209 festgelegt.

„0 CHF verpflichtende API-Kosten“ bezeichnet nur API-Gebühren. Hardware, Strom, Betrieb und Sicherungsspeicher sind darin nicht enthalten.
