# PR4-0 – CI Recovery

Stand: 21.10.2026. **PR3 CI FAILURE: FIXED LOCALLY. REMOTE SUCCESS: NOT VERIFIED.**

## Ausgangspunkt

Git-Fetch bestätigt lokalen HEAD und `origin/main` auf `8004ea39eeeb5628bf90cef9c86567a2d3af33ff`. Der genannte PR3-Commit `581a13c415d20ff8594d5ecf97b98226b8b5c74e` ist dessen Vorgänger. PR4-Images, Scanner-/SBOM-/Policy-/Manifestwerkzeuge und die lokale Abnahme vom 20.10. wurden bereits übernommen. Diese Komponenten werden nicht erneut entwickelt.

Am 21.10. wurden die tatsächlichen Jobs/Steps und Logs von Run `39242444587`, Job `118026254378`, erneut über den GitHub-Connector geprüft: **completed/failure**. Compose, Backend (264), Frontend und Fixturevorbereitung bestanden; Browser 20/21. Die Commit-Workflow-Abfrage lieferte keine zugeordneten Runs; daraus wird kein Erfolg für den neuen Commit abgeleitet. Kein neuer Push/Release oder Workflowlauf aus diesem Auftrag.

## Root Cause und gezielter Fix

Der unqualifizierte `getByRole('alert')` traf sowohl `<p role="alert">Operations access required</p>` als auch Next.js' `__next-route-announcer__`. Die semantische Filterung auf `Operations access required` ist bereits in `8004ea3` vorhanden. API-Berechtigung, Operations-Allowlist und 403-Vertrag bleiben unverändert.

Neuer gezielter Systemstatus-E2E-Lauf auf abgeschlossenem Standalone-Build: **1 passed**, 28,8 s insgesamt, Fall 14,0 s. Artefakt `backups/pr4r-focused.txt`. Kein Entwicklerserver lief während des Builds.

## Weitere Locatorprüfung

Dataset-Statusprüfungen sind jetzt auf den tatsächlichen `Dataset:`-Status eingeschränkt. Der Recommendation-Historientest wählt nicht mehr den ersten beliebigen passenden Button: er bindet die neue POST-Antwort an Instrument, Zeitstempel, Kategorie und gespeicherte ID und lädt genau diesen Archiveintrag erneut. Dadurch kann ein älterer erfolgreicher Testeintrag den aktuellen Persistenztest nicht ersetzen.

Weitere `.first()`-Vorkommen dienen reinen Sichtbarkeitsprüfungen wiederholter Hinweise, nicht einer Freigabe oder Auswahl einer historischen Operation. Der Systemstatus-Fehler wird nicht durch DOM-Reihenfolge, Berechtigungsänderungen oder unterdrückte Assertions umgangen. Die vollständige Regression des abschließenden Quellstands wird im neuen Abnahme-Nachweis festgehalten.

Die Einzahlungsprüfung wartet zusätzlich auf die tatsächliche erfolgreiche POST-Antwort (201) und anschließend die neu geladene Ledgerliste. Ein früherer Lauf blieb vor dem asynchronen Refetch bei fünf Sekunden stehen (20/21); dieser Fehlversuch bleibt erhalten. Ein erster zusätzlicher Archive-ID-Assert erwartete eine nicht angezeigte interne ID im UI. Der korrigierte Test bestätigt sie in der genau zugeordneten GET-Antwort und prüft danach weiterhin die sichtbaren fachlichen Gates, ohne Implementierungsdetails ins Produkt einzubauen.

Abschließender betroffener E2E-Lauf: **6 passed, 58,8 s**. Danach **21 passed, 2,5 Minuten, keine Skips**, `backups/pr4r-browser-v3.txt`. Die alten fehlgeschlagenen Läufe wurden nicht überschrieben. Backend/Frontend/Compose-/Schema-/Security-Gesamtnachweise werden separat im aktuellen PR4-Abnahmebericht gebunden.

## Grenzen

Erste kontrollierte Neustarts überschritten unter erheblichem Speicher-/I/O-Druck die bestehenden Healthcheck-Zeitfenster. Die Fehlversuche bleiben erhalten; danach wurden API, Worker und Scheduler gesund beobachtet. Keine Produktions-Healthchecks oder fachlichen Gates wurden abgeschwächt. Optionale eigene ML-/LLM-Dienste wurden zur Entlastung vorübergehend gestoppt; kein Host-/Docker-Neustart und keine fremden Anwendungen beendet.

Eine lokale Korrektur ist kein Remote-Pass. Die neue Security-CI darf offene Critical-Befunde weiterhin blockieren. [Bisherige Gesamtabnahme](PR4_ACCEPTANCE_REPORT.md), [Security-Matrix](security/PR4_REMEDIATION_MATRIX.md).
