# Data Operations / PR1

Gemeinsame Dienste: `BackfillJobService`, `DataCoverageService`, `IRReportReviewService`; API und Celery verwenden dieselben Settings. Tabellen ab 0017: collector_jobs, provider_sync_states, source_review_evidence, data_coverage_snapshots. Migration 0018 ergänzt typisierte Action-Coverage, Ereignisdetails und optionale Macro-Metadaten. Bestehende rohe und kanonische Archive bleiben erhalten; [Hashvertrag](../decisions/ADR-024-versioned-pit-row-hashes.md).

## Ablauf

1. Rechte-Matrix und reale Operator-Review, danach separate Aktivierung.
2. Auftrag auf Quelle, Datentyp, Identität, Zeitraum und Umfang prüfen.
3. Vorschau zeigt begrenzte Fenster und maximale Requests inklusive Retry; manueller Import hat null Netzwerkrequests.
4. Job persistent QUEUED; Celery verarbeitet mit Prozesssperre. Fortschritt entsteht nach dauerhafter Raw-/Canonical-Verarbeitung.
5. Jede HTTP-Anfrage erneut gaten/limitieren, exakte Bytes archivieren, Parser ausführen, bestehende Writer verwenden.
6. Konflikte suspendieren oder quarantänisieren; bestehende gute Werte bleiben erhalten.
7. Coverage prüfen, neue Snapshots berechnen; keine Modell-/Strategie-Promotion.

Status: QUEUED/RUNNING/SUCCESS/PARTIAL/FAILED/SKIPPED, zusätzlich CANCELLED. Ein Fehlercode ist eine fachliche Zustandsangabe, kein fingierter Erfolg. Fortschritt und Rohdaten überleben Worker-Neustarts. Cancel entfernt keine bereits aufgenommenen Daten. Eine blockierte Quelle kann weder über UI/API noch über den Scheduler starten.

## Bedienung

`/settings/data-sources`: Rechte, Zeitpunkte, letzte Importe/Fehler und Limits; Operator-Review mit Beleg, separate Aktivierung, Entscheidungshistorie. `/data-operations`: gebundene Providerverträge, eigener CSV-Import, Vorschau/Start/Cancel/Resume/Ergebnisse und Instrumentensuche. Die Instrumentenseite zeigt Zeitraum-/PIT-/FX-/Action-/Fundamental-Coverage. `/data-quality` verknüpft die bisherigen P4–P10-Qualitätsanzeigen mit diesen Operations.

Rechte ändern nur konfigurierte `DATA_OPERATOR_USERNAMES`. Jobs sind eigentumsgeprüft. Externe Quellen brauchen aktuelle vollständige Review und passenden erlaubten Use. PDF-Prüfung ist ein separater manueller Weg unter `fundamentals` und `filings`; Original vor Extraktion, konkrete Fundstellen/Accounting-Basis, explizite Bestätigung, neuer versionierter menschlicher Prüfbeleg. Kein LLM und keine automatische Finanzzahlenannahme.

## Zeitpläne und Grenzen

`DATA_COLLECTION_ENABLED=false` bleibt Standard. Optional `DATA_COLLECTION_SCHEDULES` enthält höchstens zehn Operator-/Request-Verträge; keine URLs oder Keys im Vertrag. Beispielstruktur: `[{"operator":"<eigener Operator>","request":{"source_slug":"ECB","kind":"ECB_FX"}}]`. Scheduler wählt vergangene 32 Kalendertage für kleine inkrementelle Kontrollabrufe; Alpha verwendet die letzte laut Kalender einschließlich Publikationspuffer abgeschlossene Sitzung. Derselbe Tagesauftrag startet höchstens einmal pro 24h. Jobzustände verhindern parallele komplette Duplikate; Fehler müssen geprüft/fortgesetzt werden. Rechtsentzug und Operator-Deaktivierung gelten auch für alte Aufträge.

Das globale Valkey-Tagesbudget ist standardmässig 100 Requests; providerbezogene Minutenquoten sind gleitend, SEC zusätzlich global 5/s, OpenFIGI konservativ 25/min, Alpha höchstens 25 in rollenden 24h. Bei Valkey-Ausfall keine Requests. Kleine Überschneidungsfenster können Revisionen erkennen, beweisen aber keine Vollständigkeit ausserhalb ihres Intervalls. SNB unterstützt bedingte ETag-Abfragen; das dokumentierte lastUpdate ist eine alternative Metadatenprüfung, keine Pflicht zum Doppelabruf.

Für Aktien-EOD gelten P6-Kalender, Zeitzonen/Frühschlüsse und ein Publikationspuffer. Es gibt keinen unbegrenzten Marktscan. Priorität: eigene Positionen → Watchlists → Benchmarks → kleines geprüftes Universe. Mehrjährige Historie bleibt bei fehlenden freien Rechten manuell/rechtlich zu klären.

## Betrieb

Neue Tabellen liegen im PostgreSQL-Backup, Originale weiter in MinIO. Der isolierte Restore kann zusätzlich `--collections-history-hash` prüfen; der Checkpoint umfasst Source Registry, Rechteentscheidungen, Jobs, Sync, Coverage sowie Kurs-/FX-/Macro-/Fundamental-/Action-Versionen und Action-Reviews. P6–P10-Replays und CHF 10'180 bleiben eigenständige Restore-Gates. Keine Änderung numerischer Locks. Metriken verwenden feste Provider-/Statuslabels, keine Nutzer-/Instrumentlabels.
