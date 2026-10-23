# PR5 – Abnahmeprotokoll

Stand: 22.10.2026. **BETA_IMPLEMENTED / REAL_PRIVATE_DATA_USE_NOT_APPROVED / SECURITY_BLOCKED.**

## Ausgangslage und Remote

## Getrennte Abschlusszustände

| Statusschlüssel | Ergebnis |
| --- | --- |
| PR5A_SECURITY_STATUS | PARTIAL / SECURITY_BLOCKED |
| PR5B_PORTFOLIO_WORKFLOW_STATUS | TECHNICALLY_VERIFIED_SYNTHETIC |
| PR5C_MARKET_DATA_STATUS | MANUAL_WORKFLOW_VERIFIED / SOURCE_APPROVAL_REQUIRED |
| PR5D_PRIVATE_BETA_STATUS | BETA_IMPLEMENTED / REAL_PRIVATE_DATA_USE_NOT_APPROVED |
| REMOTE_CI_STATUS | VERIFY_SUCCESS / SECURITY_FAILURE; kein PR5-Remote-Lauf |
| TARGET_HOST_STATUS | NOT_AVAILABLE / NOT_VERIFIED |
| REAL_PORTFOLIO_VALIDATION | REAL_ORIGINALS_NOT_PROVIDED |
| REAL_DATA_READINESS | SOURCE_APPROVAL_REQUIRED / REAL_COVERAGE_NOT_VERIFIED |
| FORECAST_VALIDATION | SHADOW / NOT_FINANCIALLY_VALIDATED |
| RECOMMENDATION_VALIDATION | GATED / NOT_REAL_VALIDATED |

## Repository und Remote-Nachweis

HEAD und erneut gefetchtes `origin/main`: `2c563e9dd7de1bb211728b0132170ef038b01c9e`. Die PR5-Arbeit liegt lokal; kein Commit, Push oder Release durch diesen Arbeitslauf. GitHub-Run [39603225713](https://github.com/P-Liebler/Private-IIP/actions/runs/39603225713) erneut am 22.10. geprüft: `verify` erfolgreich, Security-Job im Dependency-Audit fehlgeschlagen; nachfolgende Imagegates übersprungen. Die lokale Behebung ist kein neuer Remote-CI-Pass.

Baseline am 21.10. erneut ausgeführt: 266 Backendtests, 21 Browserfälle ohne Skips, 32 ursprüngliche Hosttests; Frontend-Lint/Typecheck/Standalone-Build bestanden. Ein fehlerhafter Runner ließ zunächst zwei P6-Fälle aus; der korrigierte vollständige Lauf ist gesondert erhalten. PowerShell-Dateiausführungsrichtlinien wurden nicht verändert.

## Teilabnahmen

| Teil | Ergebnis | Nachweis |
| --- | --- | --- |
| PR5A | Core-/Parser-Patches und Legacy-Verifikation implementiert; PG17- und S3-Kandidaten geprüft; Sicherheitsfreigabe bleibt gesperrt | [Security Closure](PR5A_SECURITY_CLOSURE_REPORT.md) |
| PR5B | Vorhandener Ledger mit Opening-Position, überprüftem CSV-Import, Onboarding und read-only Auszugsvergleich erweitert | [Workflow](PR5B_PORTFOLIO_WORKFLOW_REPORT.md) |
| PR5C | Manueller Marktdatenweg und Provenienz verbessert; Rechteprüfung dokumentiert; reale tägliche Versorgung nicht abgenommen | [Marktdaten](PR5C_MARKET_DATA_REPORT.md) |
| PR5D | Benutzeranleitungen und getrenntes Pilotprotokoll vorhanden; echter Pilot mangels Daten/Sicherheitsfreigabe offen | [Beta](PR5D_PRIVATE_BETA_REPORT.md) |

Die Teilabnahmen sind technische Nachweise mit Grenzen. Insbesondere ist PR5A keine abgeschlossene Securityfreigabe und PR5D keine real angenommene Beta.

## Prüfung des Workflows

Der zusätzliche synthetische Browserfall führt über Portfolio/CHF/Konto und zwei gleichnamige Ticker an verschiedenen MICs zur bewusst geprüften Zuordnung. Deposit 1.000 USD, Kauf 2 × 100 USD, Gebühr 1 USD, Steuer 1 USD ergeben 798 USD Cash. Schlusskurs 120 USD und 0,9 CHF/USD ergeben zusammen **934,20 CHF**. Ein zweiter identischer Import erzeugt keine Buchung. Manuell eingegebene Auszugswerte stimmen überein; unbekannter Einstand im zweiten Konto bleibt unverfügbar. Keine dieser Zahlen stammt aus einem echten Depot.

Fehlende/stale Kurse und FX, ungeprüfte Actions, Korrekturen und voidierte Originale werden in den Backendverträgen geprüft. Ein fehlender Wert wird nicht durch Null ersetzt. Startbestände erzeugen keine erfundene historische Rendite. Ein LLM oder eine unfreigegebene Quelle ist für den manuellen Ablauf nicht erforderlich.

## Regression und Restore

Der erste vollständige PR5-Lauf bestand 280 Backendtests, 22 Browserfälle ohne Skips und 35 Hosttests. Der nachträgliche aktuelle Audit fand einen zusätzlichen pypdf-Befund; der gezielte Patch auf 6.21.1 und ein eigener V2-Runtime-/Dokumentpipelinevertrag wurden ergänzt. **Danach vollständig erneut bestanden: 281 Backendtests** (eine bestehende Starlette/httpx-Deprecation-Warnung), **22 Browserfälle ohne Skips**, **35 Hosttests**. Ruff/Format, Mypy (199 App-Dateien), Frontend-Lint/Typecheck und abgeschlossener Standalone-Build bestanden. Die Browserfälle liefen ausschließlich gegen diesen Build über `ops/docker-compose.e2e.yml`; keine parallelen Backendintegrationstests.

Core+Assistant-, MLflow- und Frontend-Dependency-Audit ohne bekannte Befunde. Fünf finale exakte Imageeinträge/SBOMs sind neu mit Scanner-DB vom 22.10. geprüft und formal validiert: [Inventar](security/pr5-20261022/inventory-final.json), [SBOM-Validierung](security/pr5-20261022/sbom-validation-final.json). Dieser Scope umfasst die geänderten Kandidaten und bestehendes MinIO, keinen neuen Gesamtscan aller unveränderten PR4-Komponenten. Der Security-Gate verweigert die Freigabe erwartungsgemäß. [Restrisiken](security/PR5_RESIDUAL_RISKS.md).

Der abschließende Build rc6 synchronisiert zusätzlich `requirements-assistant.txt` mit dem bereits geprüften Lock. [Anwendungscode und Runtime-Locks sind identisch](security/pr5-20261022/build-equivalence.json) zum vollständig grünen rc5-Testlauf; eigener rc6-Scan/SBOM und der unten beschriebene rc6-Restore sind zusätzlich bestanden.

Frische Migration: `0019_validation`, 76 erforderliche Tabellen. Keine Schemaänderung für den zusätzlichen Transaktionstyp; das vorhandene Stringfeld und die bestehende Historie werden verwendet. Die 212 nummerierten Masterabschnitte bleiben erhalten.

Finales konsistentes Backup `20261022T125200Z-67708`: **410 Raw-Objekte / 411 Dateihashes**. Tatsächlicher isolierter Restore auf finalem gepatchtem Backend, PostgreSQL 17.11/pgvector 0.8.6 und SeaweedFS 4.48 bestanden, **13:04:46–13:06:04 UTC**, Cleanup erfolgreich bis **13:06:11 UTC**. JSONB, Numeric, Vektor- und JSON-Indizes sowie abgewiesenes Update einer unveränderlichen PIT-Version geprüft. Vorhandene Archive P6/P7 sowie aktuelle P8/P9/P10/PR1/PR2-Verträge und Golden CHF 10'180 bestanden; Netzwerk-isolierter Legacyprozess prüft das originale Modell. Die beiden zuvor fehlgeschlagenen Prüfversuche sind aufbewahrt. Originalvolumes wurden nicht ersetzt; ein libc-/Collationwechsel benötigt weiterhin einen konkreten Migrationsreview.

Der synthetische S3-Prototyp prüft Multipart-Abbruch/Wiederaufnahme, TLS/Auth, Metadaten, Range und Mirror/Restore. Zusätzlich schaltet die tatsächliche konfigurierte App-Storagefactory für drei Originaltypen von Testquelle zu Testziel und zurück und verifiziert die Bytes erneut. Keine produktive Endpointkonfiguration verändert.

Lokales Staging mit finalen Backend-/Webimages: 13 gesunde Dienste; tatsächliches privates HTTPS, Securityheaders, Secure-/HttpOnly-Login, Goldenwert, blockierte öffentliche Metrics, Prometheus und Grafana bestanden. Browser ohne Seiten-/CSP-Fehler; Auth-/S3-/Bild-Roundtrip in MLflow bestanden, Serverjobs deaktiviert. Temporärer Browser-SPKI-Pin ist kein Nachweis systemweiter Client-CA-Installation. Staging verwendet seine bisherigen separaten PostgreSQL-/MinIO-Testvolumes; der Alpine-/Seaweed-Restore läuft in einem anderen kurzlebigen Projekt.

Dev-/Prod-Compose syntaktisch gültig. Offline-Preflight mit separat generierter sicherer CI-Konfiguration bestanden, ohne einen Zielhost zu behaupten. Der vorhandene Loopback-Staging-Name `localhost` wird vom strikten Domain-Preflight abgewiesen; ein Produktionscheck desselben Labors weist zusätzlich Umgebung/VPN/Projekt zurück. Diese negativen Befunde wurden erhalten und der Validator nicht gelockert. TLS-Laborproben ersetzen diese Produktionsgates nicht.

## Offene Freigaben

Reproduzierbare Hashverweise und Restoreverträge: [Abnahmenachweis](security/pr5-20261022/acceptance-evidence-final.json). Git-sichtbarer Quellbestand ohne bekannte Secret-Funde: [Quellenprüfung](security/pr5-20261022/source-security.json). Private Testlogs und Backupbytes bleiben im ignorierten lokalen Bestand; keine echten Brokerdaten oder Secretwerte veröffentlicht. Normalbetrieb wiederhergestellt: `APP_ENV=local`, `ASSISTANT_TEST_MODE=false`, `DATA_COLLECTION_ENABLED=false`, `FORWARD_SHADOW_ENABLED=false`. Lokales Staging und S3-Prototyp gestoppt, ihre Volumes erhalten.

MinIO im normalen Bestand hat weiterhin neun Critical-Paketbefunde. Der funktionsfähige Seaweed-Prototyp ersetzt keine Security- oder Migrationsfreigabe; High-Befunde und die Filer-/TUS-Exposition sind offen. Weitere Backend-Highs und native Ollama-/CSP-Reviews bleiben prüfpflichtig. Keine genehmigten Exceptions.

Kein bestätigter Zielhost und keine echten Brokerdaten liegen vor. Keine vollständige CH-/US-/ETF-Abdeckung oder tägliche automatische Versorgung nachgewiesen. Reale Modell-/Strategievalidierung und Empfehlungen bleiben gesperrt. Ohne diese separaten Nachweise wird weder `PRODUCTION_READY` noch ein real akzeptierter Portfolio-Pilot erklärt.
