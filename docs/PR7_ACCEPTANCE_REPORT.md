# PR7 – lokale Abnahme und offene Freigaben

Stand 27.10.2026, Basis26f701edce992be60a98c75c76eaa0c914245619.
**LOCAL_SYNTHETIC_ACCEPTANCE_VERIFIED / NOT_RELEASED**.

## Neuester belegter Stand

- 306 Backend-/67 Hosttests, Ruff/Format/Mypy, Frontend-Lint/Typecheck/Standalone-Build.
- Ein vollständiger Browserlauf **29/29 in4,0 Minuten ohne Skips**, normale
  Einstellungen danach verifiziert. Source-UI-Recovery, CSV-Drop/Mehrinstrument-
  Import, News-/Qualitäts-Retry per Tastatur und Assistentenabbruch enthalten.
- Alle 14 exakten Dienstprofile am 27.10. neu gescannt, alle 14 SBOMs formal
  validiert. DB UpdatedAt 27.10.07:13 UTC. **Security weiterhin nicht genehmigt.**
- Vollständige synthetische Migration683 Originalobjekte/Versionseinträge,
  323 DB-Referenzen, Wiederaufnahme/Idempotenz und unveränderte Quelle.
- Native gRPC-/PUT-/POST-/Retention-/Versionsprobes, tatsächliche Raw-/Modell-/
  PDF-Factory, MLflow und native RAG-Verträge bestanden.
- Neuer vollständiger Zielrestore mit **1372 Objektdateien inklusive Archivkopien,
  acht Evidenzdateien und DB-Dump:1381 Hashes**, Legacyprüfung ohne Netzwerk und
  Cleanup bestanden. Alle alten Archive und separaten PR6-Hashes erhalten.
- Vergleich des eingefrorenen Quelldumps mit späterem QA-Bestand: keine alte
  Collectionzeile entfernt/geändert; genau eine Testdokumentquelle und eine
  Kursversion ergänzt. Neuer globaler Checkpoint plus Delta im Backup.
- Golden CHF10’180 am expliziten Originalcutoff26.10.15:18 UTC; heute für den
  alten Bestand korrekt PARTIAL/STALE_PRICE und fehlender Gesamtwert. Ein
  frisches synthetisches Portfolio besteht die aktuelle HTTPS-Bewertung separat.
- Native, vorgewärmte Erklärung 28,8s, erstes Ereignis2,1s; gespeicherte
  Ersatzantwort mit gestopptem Modell 4,2s. Kein kalter Produktions-SLA.
- Prometheus/Grafana samt tatsächlichem API-Scrape, verweigerter anonymer
  Grafana-API und Datasourcehealth geprüft; eigene Stagingdienste gestoppt.

Die vorherigen fehlgeschlagenen Läufe bleiben getrennt erhalten. Weder alte
Hashes noch fehlgeschlagene Antworten, Modellmanifeste oder Originaldaten
wurden passend zum gewünschten Ergebnis umgeschrieben.

## Getrennte Entscheidungen

| Status | Belegter Zustand |
| --- | --- |
| REMOTE_CI_STATUS | FAILURE_AT_BASELINE / LOCAL_FIX_NOT_PUSHED |
| SECURITY_STATUS | NOT_APPROVED / FINAL_RC3_INVENTORY_SCANNED_WITH_OPEN_FINDINGS |
| POSTGRESQL_STATUS | ISOLATED_PG17_CONTRACTS_AND_FULL_TARGET_RESTORE_VERIFIED |
| OBJECT_STORAGE_STATUS | SYNTHETIC_MIGRATION_AND_RECOVERY_VERIFIED / PRODUCTION_APPROVAL_PENDING |
| UX_FUNCTIONAL_STATUS | FULL_LOCAL_29_CASE_REGRESSION_VERIFIED / BROADER_STATE_ACCEPTANCE_PARTIAL |
| REAL_PORTFOLIO_PILOT_STATUS | PENDING_REAL_ORIGINALS_AND_SECURITY |
| MANUAL_MARKET_DATA_STATUS | SYNTHETIC_MULTI_INSTRUMENT_WORKFLOW_VERIFIED / REAL_ORIGINALS_NOT_TESTED |
| LIVE_PROVIDER_STATUS | LIVE_TEST_BLOCKED_BY_SOURCE_APPROVAL |
| AUTOMATIC_REFRESH_STATUS | DISABLED / NOT_VALIDATED |
| TARGET_HOST_STATUS | NOT_AVAILABLE / LOCAL_PREPARATION_ONLY |
| PRIVATE_CORE_RELEASE_STATUS | NOT_RELEASED / SECURITY_SOURCE_USER_HOST_OPERATOR_GATES_OPEN |
| FORECAST_VALIDATION_STATUS | NOT_VALIDATED / SHADOW_ONLY |
| RECOMMENDATION_VALIDATION_STATUS | NOT_VALIDATED / HARD_GATES_RETAINED |

## Grenzen und nächste echte Abnahme

Backend/MLflow jeweils44 High, Grafana 8 High, bisheriges MinIO 9 Critical/
125 High. Keine automatisch akzeptierte Ausnahme. Native Paketabdeckung,
Buildattestation und CSP mit unsafe-inline bleiben ausdrücklich eingeschränkt.
HTTPS-Browser-QA verwendete eine ausgewiesene Ausnahme für die eigene Test-CA;
Python prüfte dieselbe CA separat strikt. Kein echtes OS-Client-CA-Vertrauen.

Keine externe Quelle aktiviert, kein Liveabruf und kein echter Brokerpilot.
Verschiedene ISINs sind als Identitäten möglich; allgemeine Kurs-/Börsen-/FX-/
Corporate-Action-Abdeckung ist nicht zugesagt. Reale zulässige Originale,
Quellenoperatorentscheidungen, unabhängige Anfängerperson und Zielhost/VPN/
Client-CA/unabhängiger Backup-/Schlüsselplan fehlen. Breite Routen-Smokes sind
keine Prüfung jedes Transport-/Rechtefehlers jeder Seite; Details im UX-Bericht.
Keine neue Forecast-/Strategievalidierung oder Promotion.

Die bestehende Nutzerentscheidung „Zielhost fehlt; lokal vorbereiten“ bleibt
gültig. C: ist das autorisierte QA-Laufwerk. Kein Push, Release, produktiver
DB-/Storagewechsel oder erneutes Freigabegesuch ausgeführt.

## Detailbelege

[Security](PR7A_SECURITY_CI_REPORT.md), [Storage](PR7B_STORAGE_READINESS_REPORT.md),
[Daten](PR7C_REAL_DATA_REPORT.md), [UX](PR7D_PRODUCT_USABILITY_REPORT.md),
[Pilot](PR7E_PRIVATE_PILOT_REPORT.md), [Checkliste](operations/PR7_RELEASE_CHECKLIST.md),
[aktuelles Inventar](security/pr7-20261027-rc3/inventory.json),
[Stagingablauf](operations/PR7_SYNTHETIC_STAGING.md).
