# Implementation status

## PR6 – lokale Regression und Restore bestanden (Abgleich 26.10.2026)

Basis f05cb70; Remote verify SUCCESS, Security Dependency-Audit FAILURE. Originales CI-Artefakt per SHA256 verifiziert: opentelemetry-api1.45.0/CVE-2026-114603. Gezielter Patch1.45.1 mit separatem PR5-Lockarchiv und neuem Runtimeguard; numerische Pins unverändert. Core-/Assistant- und npm-Produktionsaudit vom 23.10. ohne bekannte Befunde. Next16.4.2; fünf Highs im Entwicklungsbaum bleiben offen. **297 Backendtests / 35 Hosttests / 26 unterschiedliche Browserfälle**, Ruff/Format/Mypy und Frontend-Lint/Typecheck/Standalone-Build bestanden. Browser: 25 im Gesamtlauf plus gezielte erfolgreiche Chart-/Theme-Nachprüfung bei unverändertem Anwendungsbuild. Frische Migration **0021_ui_requests / 78 Tabellen**, keine Drift. 31 Routen/215 API-Deklarationen inventarisiert. Diese vollständigen Nachweise stammen vom 23.10.; kein neuer Remote-Pass.

Backup `20261023T131714Z-50868`: **502 Raw-Objekte / 503 erneut geprüfte Dateihashes**, isolierter Restore, Golden CHF10’180, P6–P10/PR1/PR2-Archive und separate Dokumentrückzugs-/UI-Anfragehashes bestanden. Networklose exakte Legacyprüfung und Cleanup erfolgreich. Am 26.10. normalen lokalen Modus geprüft: Testmodus aus, temporäre Daten-/ML-Rollen leer, Collection/Forward aus; Sichtlauf auf 390/1440 px ohne Seitenfehler oder finanzielle Mutation. Image-/Vulnerability-Nachweise vom 23.10. sind keine neue Securityfreigabe vom 26.10.

PR6B–D: sechs Hauptbereiche, Light/Dark/System, gemeinsame Dialoge/Drawer/Tabs/Suche/Tabellen/Karten, CHF-Übersicht, Originalledger-Neubewertung, geführter Portfolio-/CSV-Ablauf und explizite Datenlücken. P8-Kurven ausschließlich aus gespeicherten Beobachtungen; alte Snapshots unverändert. PR6F: append-only Dokumentrückzug und atomare technische Wiederholungsbelege mit separaten Restorehashes; stabile Buchungsschlüssel und Bestätigungen. Alte unvollständige Datasetqualität wird als nicht archiviert angezeigt.

Echte lokale Chat-/Embedding-/Retrievalfunktion mit synthetischer Evidenz und Ollama-Ausfall geprüft. Größerer Assistentenkontext benötigt lokal 120 s Timeout (101.562 s gemessen); der 60-s-Timeout bleibt dokumentiert. Finale fünf Teilimage-SBOMs gültig; Backend 0 Critical/44 High, Web rc6 0/0, PG17-Kandidat 0/0, MinIO 9/125, Seaweed 0/5. **SECURITY_BLOCKED / REAL_DATA_LIMITED / TARGET_HOST_NOT_VERIFIED**. Allgemeine ISIN-Quellenprüfung gemäß Nutzerentscheidung, keine neue Aktivierung, kein echter Pilot, kein Produktiv-Cutover, keine Modell-/Strategiepromotion, kein Push/Release. Anfängerabnahme **PENDING_USER_TEST**. [Gesamtbericht](PR6_ACCEPTANCE_REPORT.md), [Produktaudit](PR6A_PRODUCT_AUDIT.md), [Funktionsmatrix](ux/FUNCTIONAL_MATRIX.md).

## PR5 – technisch implementierte lokale Beta (22.10.2026)

**BETA_IMPLEMENTED / REAL_PRIVATE_DATA_USE_NOT_APPROVED / SECURITY_BLOCKED.** Basis/erneut gefetchtes origin/main `2c563e9dd7de1bb211728b0132170ef038b01c9e`; Remote verify erfolgreich, Security im Dependency-Audit fehlgeschlagen. Baseline 266 Backend/21 Browser/32 Host erneut bestanden. Finale Runtime nach certifi2026.10.19 und gezieltem pypdf6.21.1-Patch: **281 Backendtests, 22 Browserfälle ohne Skips, 35 Hosttests**, Ruff/Format/Mypy und Frontend-Lint/Typecheck/Standalone-Build bestanden. Numerische Pins und Originalartefakte bleiben erhalten; alte Modelle werden separat ohne Netzwerk exakt verifiziert. Neue Parser-/Runtimeverträge ändern keine alten Dokumente oder Modellmanifeste.

Vorhandener P4-Ledger erweitert: explizite Opening-Position mit unbekanntem Einstand, sichere CSV-Zuordnung/Bestätigung/Idempotenz, Korrekturhistorie, Onboarding, Positions-/FX-Provenienz, handlungsbezogene Datenqualität und read-only Auszugsvergleich. Übersicht zeigt Positionen, Allokation und letzte Transaktionen. Benutzeranleitungen und echter Pilotablauf liegen vor; keine echten Brokeroriginale geliefert, keine reale Quellenaktivierung oder tägliche Versorgung abgenommen.

Finaler isolierter Restore `20261022T125200Z-67708`: **410 Raw-Objekte/411 Dateihashes**, alte P6/P7 und aktuelle P8/P9/P10/PR1/PR2, Golden CHF10'180, PG17/pgvector/JSONB/Numeric/Indizes/PIT-Trigger sowie networklose Legacyprüfung bestanden; Cleanup erfolgreich. S3-Prototyp besteht bestätigten Multipart-Abbruch/Wiederaufnahme, TLS/Auth, Mirror/Restore und synthetische Rückschaltung der tatsächlichen App-Storagefactory. Finales HTTPS-Staging/Auth/CSP/Monitoring und MLflow-S3-Roundtrip bestanden. Keine Originalvolumes ersetzt.

Fünf exakte neue Kandidaten-/MinIO-SBOMs formal gültig; Core-/MLflow-/npm-Dependency-Audits ohne bekannte Befunde. Backend 0 Critical/44 High, Web 0/0, PG17-Kandidat 0/0, Seaweed 0/5; bestehendes MinIO weiterhin 9 Critical/125 High. Dies ist kein neuer Gesamtscan unveränderter PR4-Images. DB-/Storage-Cutover, Security-/High-/native-/CSP-Review, Zielhost/VPN/CA/Backupzeitplan/Recovery und echter Pilot bleiben offen. Keine produktive Migration, kein Push/Release, keine Finanzfreigabe. [Gesamtabnahme](PR5_ACCEPTANCE_REPORT.md), [PR5A](PR5A_SECURITY_CLOSURE_REPORT.md), [PR5B](PR5B_PORTFOLIO_WORKFLOW_REPORT.md), [PR5C](PR5C_MARKET_DATA_REPORT.md), [PR5D](PR5D_PRIVATE_BETA_REPORT.md).

## PR4-Wiederprüfung vom 21.10.2026 – lokal abgenommen, Security gesperrt

Basis/Remote `8004ea39eeeb5628bf90cef9c86567a2d3af33ff`; bisherige PR4-Arbeiten übernommen. **PR4-0 FIXED LOCALLY**, neuer Remote-Pass nicht verifiziert. **266 Backendtests, 21 Browserfälle ohne Skips und 32 Host-/Security-Verträge bestanden**; Ruff/Format/Mypy, Frontend lint/typecheck/Standalone-Build, frische Migration 0019/76 Tabellen und Compose/Offline-Preflight bestanden. Publisher verweigert geänderte Originalbytes, andere Scanner-DBs und unvollständige Originalläufe. Zehn exakte Images mit DB vom 21.10. gescannt, zehn originale SBOMs formal gültig. PostgreSQL ohne unbenötigtes SQLite: drei statt vier Criticals; separater MLflow-Lock mit certifi 2026.10.19/Pillow 13.0.0: null Criticals und tatsächlicher Tracking-/S3-/Bild-Roundtrip bestanden. Backend-Core-/Assistant-/Frontend-Locks und 212 Masterabschnitte erhalten. Neuer Core-certifi-Befund bleibt wegen des exakten historischen Modellvertrags ein Critical-Blocker. Insgesamt **13 Critical / 366 High**, keine Exceptions; native/CSP-Reviews offen.

Frisches Backup mit **355 Raw-Objekten** und isolierter Restore auf neuen PostgreSQL-/Backenddigests bestanden: CHF 10’180, alte P6-/P7-Verträge und neue P8/P9/P10/PR1/PR2-Checkpointverträge unverändert, Cleanup erfolgreich. Staging prüft private TLS/Auth/Monitoring/CSP sowie Core- und optionale Ausfälle. Neuer unveränderlicher lokaler Kandidat **PR4-LOCAL-20261021-01: RC_TESTED / RC_SECURITY_BLOCKED**. Zielhost fehlt weiterhin; keine produktive Migration, kein Push/Release, keine Finanzfreigabe. [Neue Gesamtabnahme und Restarbeit](PR4_ACCEPTANCE_20261021.md), [PR4-0](PR4_0_CI_RECOVERY_REPORT.md), [Runtimekonflikt](operations/MODEL_RUNTIME_COMPATIBILITY.md), [vorbereiteter S3-Migrationsablauf](operations/OBJECT_STORAGE_MIGRATION.md). Die folgenden Abschnitte dokumentieren die frühere Abnahme vom 20.10.

## PR4 – lokal verifiziert, Freigaben offen (2026-10-20)

**PR4A ASSESSMENT COMPLETE; PR4B LOCAL COMPATIBILITY VERIFIED; PR4C LOCAL RC VERIFIED. SECURITY_BLOCKED; TARGET_HOST_NOT_VERIFIED.** Zehn exakte Images mit Trivy 0.76.0/DB vom 20.10.2026 gescannt; zehn originale CycloneDX-SBOMs formal validiert. Endbestand: vier rohe Critical-Befunde in PostgreSQL und neun in MinIO; keine genehmigten Exceptions. Weitere High-/native/CSP-Reviews bleiben offen. Die Ollama-Paketprüfung ist vollständig, die beliebige native Library-Abdeckung bleibt unvollständig.

Abschluss: **264 Backendtests**, **21 Browserfälle ohne Skips**, **30 Host-/Security-Vertragsfälle** bestanden; Ruff/Format/Mypy, Frontend lint/typecheck/Standalone-Build und frische Migration `0019_validation`/76 Tabellen bestanden. Produktions-Staging mit 13 gesunden Diensten, CA-Export und bestehender CA besteht HTTPS/Auth/CSRF/Golden/Monitoring; Browser ohne CSP-/Seitenfehler. MLflow-Auth und echter S3-Artefakt-Roundtrip sowie Core-/optionale Ausfälle und Backup-Unterbrechung geprüft. S3-Alternative nur isoliert mit synthetischen SDK-Daten getestet; keine Migration. Numerische/Assistant-/MLflow-/Frontend-Locks und 212 Master-Hauptabschnitte unverändert.

Unverändertes PR3-Backup mit ersten Kandidaten erfolgreich separat restauriert (06:20:27–06:23:44 UTC). Danach frisches Backup `20261020T145904Z-5272` mit 342 Raw-Objekten; finaler isolierter Restore **14:59:43–15:00:41 UTC**, 343 Dateihashes, alte P6-/P7-Verträge, aktuelle P8/P9/P10/PR1/PR2-Checkpoint-Hashes und exakt CHF 10'180 bestanden. Cleanup erfolgreich bis 15:00:48 UTC. Neue synthetische Testversionen werden als neue Checkpoints geführt; alte Nachweise/Modelle bleiben unverändert. Lokaler Normalbetrieb wiederhergestellt, Testmodus/Collection/Forward aus.

Basiscommit `581a13c415d20ff8594d5ecf97b98226b8b5c74e`, Änderungen lokal/uncommitted. PR3-CI `39242444587` tatsächlich fehlgeschlagen (mehrdeutiger Systemstatus-Selektor); lokal korrigiert und alle 21 Browserfälle bestanden. Keine neue Remote-CI, kein Push/Release. Die neue CI prüft Dependency-/Image-/SBOM-/Secret-/Konfigurationsverträge und blockiert die offenen Criticals. Lokaler RC `PR4-LOCAL-20261020-01` bindet Quellbytes, Locks, Images/SBOMs und Nachweise; Produktionsstart verlangt geschlossene Security-/Zielhost-/Operator-Gates und Digest-Images ohne Build. Kein Rollout, keine Finanzfreigabe. [Gesamtabnahme](PR4_ACCEPTANCE_REPORT.md), [PR4A](PR4A_SECURITY_ASSESSMENT_REPORT.md), [PR4B](PR4B_REMEDIATION_REPORT.md), [PR4C/Manifest](PR4C_RELEASE_CANDIDATE_REPORT.md), [S3-Entscheid](operations/S3_COMPATIBILITY_REVIEW.md).

## PR3 – lokale Vorbereitung, Zielhost nicht verfügbar (2026-10-19)

**PR3 LOKAL VORBEREITET UND GETESTET; KEINE PRODUKTIONSFREIGABE.** PR3A implementiert/lokal geprüft, Sicherheitsreview wegen konkreter Image-High-/Critical-Befunde offen. PR3B lokale Recovery abgenommen; PR3C lokale Akzeptanz bestanden, Zielhost fehlt ausdrücklich laut Nutzer. **264 Backendtests**, zwölf Hostgoldens, **21 Browserfälle**, Ruff/Format/Mypy, Frontend und bestehende/frische Migration 0019/76 Tabellen bestanden. Separates lokales Staging: HTTPS/Cookie/Golden CHF 10'180, CSP-Hydration-Browserprobe, Prometheus/Grafana, 14 Alertregeln und kontrollierte Containerfaults geprüft. Kein Client-OS-Trustnachweis aus dem temporären CSP-Testpin.

Frisches Backup mit 320 Rohobjekten/2.914.753 Bytes und isolierter Restore **19.10.2026 10:32:03–10:33:48 UTC** bestanden, alte P6-/P7-Hashes und P8/P9/P10/PR1/PR2-Historien unverändert geprüft, Golden exakt CHF 10'180. Kein echtes VPN-/Clienttrust-/NAS-/Tagesjob-/Secret-/CA-Recovery-/Alarmzustellgate geschlossen. Keine Source-/Modell-/Strategiefreigabe; Finanzsammlung/Forward aus. 212 Masterabschnitte und numerische/Assistant-Locks erhalten. Änderungen lokal/uncommitted, keine neue Remote-CI oder Release. [PR3-Bericht](PR3_ACCEPTANCE_REPORT.md), [Operatornachweise](operations/OPERATOR_ACCEPTANCE_CHECKLIST.md).

## PR2 technisch abgenommen; reale Validierung gesperrt (2026-10-19)

**PR2A TECHNICAL FUNCTIONAL · BLOCKED_BY_SOURCE_APPROVAL. PR2B TECHNICAL FUNCTIONAL · BLOCKED_BY_REAL_DATA. V2 FORECASTS NOT VALIDATED · V3 RECOMMENDATIONS GATED · V3+ PRODUCTION NOT RELEASED.** Baseline/main `cfa8c51230d42f6a1d3cc0b766a8c2449dd04ec4`, PR1-CI `38889975378` tatsächlich completed/success. PR2 verwendet PR1/P6/P7/P9 und eine append-only Evidenztabelle: Readiness, Rechte-Checklisten, kontrollierter Pilot, Originalnachweise, OOS-Verträge, Kosten-/Regimevergleiche, Forward Shadow/Outcomes und Strategieprüfung. Keine reale Quelle aktiviert, kein reales ML-Modell oder Strategie freigegeben.

Abnahme: **257 Backendtests und 20 Browserfälle**, Ruff/Format (283 Dateien), Mypy (197 App-Dateien), Frontend lint/typecheck/Standalone-Build, Compose/Images, pip check, Celery, MinIO und MLflow-Health bestanden. Alembic ohne Drift, frisch **0019_validation / 76 Tabellen**. Gefundene JSON-Gruppierung, private Jobdeduplizierung, P7-Quality-Payload und Restore-Checkpoint-Verdrahtung korrigiert. Veraltete lokale Testbeobachtungen wurden ausschließlich als neue explizite SYNTHETIC-Versionen ergänzt; Produkt-Stale-/Split-Basis-Gates bleiben unverändert.

Isolierter Restore **19.10.2026, 05:31:39–05:32:55 UTC** bestanden: **290 Raw-Objekte**, unveränderte alte P6-/P7-Hashes, P8/P9/P10-Archive, Quellen-/Collector-Checkpoint, zehn PR2-Belege und exakt **CHF 10'180**. Dependency-Locks und 212 Masterplan-Hauptabschnitte bleiben erhalten. Keine echte OOS-/Forward-/Alpha-Aussage aus technischen Fixtures. Testmodus ist zurückgesetzt; der lokale Stack ist gesund, Collection und Forward sind aus. Änderungen lokal/uncommitted; neue Remote-CI nicht ausgeführt. Danach endet PR2 vor der separaten Homelab-Produktionsabnahme.

[PR2A-Abnahme](PR2A_REAL_DATA_ACCEPTANCE_REPORT.md), [PR2B-Abnahme](PR2B_MODEL_VALIDATION_REPORT.md), [Gesamtbericht](PR2_ACCEPTANCE_REPORT.md), [verbleibende Blocker](validation/REMAINING_BLOCKERS.md). Die folgenden Abschnitte dokumentieren frühere Abnahmestände.

## PR1 technisch abgenommen – reale Datenfreigaben bleiben offen (2026-10-16)

**PR1 COLLECTORS FUNCTIONAL · SOURCE APPROVAL PARTIAL · REAL DATA COVERAGE PARTIAL · V2 FORECASTS NOT VALIDATED · V3 RECOMMENDATIONS GATED · V3+ PRODUCTION NOT RELEASED.** Ausgangspunkt: `4ded0e61efdd071ed06596c616f51f9ccb5475f0`, sauber, 195 Backendtests. PR1 ergänzt abgesicherte gemeinsame HTTP-/Raw-Verarbeitung, Quellenrechtsbelege, persistente private Backfills/Sync/Coverage, monatliche SNB-Verträge, optionale kompakte OHLCV und explizite IR-Prüfung sowie Data Operations UI. Kein reales externes Source-Gate wurde freigegeben oder aktiviert.

Abnahme: **232 Backendtests**, **15 verschiedene Browserfälle**, Ruff/Format/Mypy (186 Dateien), Frontend lint/typecheck/Standalone-Build, Compose-Build/-Konfigurationen, Alembic ohne Drift, frische Migration auf **0018_provider_evidence / 75 Tabellen**, pip check, Celery und MinIO bestanden. Gefundene UI-Mapping-Verdrahtung und nicht isolierte synthetische Testbudgets wurden korrigiert; produktive Limits blieben unverändert.

Isolierter Restore am 2026-10-16 10:33:33–10:34:34 UTC bestanden: **246 Raw-Objekte**, P6-Dataset, P7-Modell/MLflow/Prediction-, P8-, P9- und P10-Historien einschließlich exakter Embeddings, neuer Collections-Checkpoint und exakt **CHF 10'180**. Alte P6-Hashverträge sind explizit versioniert; numerische/Assistant-Locks und archivierte Modellmanifeste unverändert. Die 212 Hauptabschnitte des Masterplans bleiben erhalten. [PR1-Abnahme mit 27 Berichtspunkten](PR1_ACCEPTANCE_REPORT.md), [Providerstatus](data/PROVIDER_INVENTORY.md), [Datenbetrieb](architecture/data-operations.md).

Keine produktiven Live-Smokes ohne echte Quellenfreigabe; Dokumentationsproben sind kein Produktimport. Historische Daten-/Action-/FX-/Membership-Lücken, Quellen-/Modell-/Strategie- und Zielinstallationsgates bleiben offen. Kein Push/Release; **REMOTE CI NOT VERIFIED FOR THIS CHANGE**. Testmodus ist zurückgesetzt, wiederkehrende Collection bleibt aus. **PR1 endet hier; PR2 wurde nicht begonnen.** Die folgenden P0–P10-Einträge dokumentieren den früheren Abnahmestand.

## P10 technisch abgenommen — V3+ nicht freigegeben (2026-10-15)

**P10 FUNCTIONAL — DATA/SOURCE GATED; V3+ NOT RELEASED.** Lokaler optionaler Ollama-Assistent mit zehn Read-only-Tools, beleggebundener Ausgabe, privaten PDF-Originalen/RAG, Alerts/Notifications, strukturiertem Daily Brief ohne LLM, P8-basiertem Simulations-Optimizer und Financial Time Machine. P9 wurde vorher separat abgenommen; reale Recommendations bleiben gesperrt.

Nachweise: 195 Backendtests, 13 Browserfälle im Standalone-Produktionsbuild, Ruff/Format/Mypy, Frontend lint/typecheck/build, driftfreie und frische Migration 0016 mit 71 Tabellen. Echter lokaler Modell-/Embeddingtest sowie Ollama-/MLflow-/MinIO-Ausfallprüfungen bestanden. Isolierter Restore 2026-10-15 14:16:58–14:18:37 UTC bestanden: P6/P7/P8/P9 und private P10-Metadaten, Originale, Chunks, exakte Embeddings, Kalenderkorrekturen, Alert-/Brief-/Optimizerhistorien sowie CHF 10'180. [P10-Abnahme](P10_ACCEPTANCE_REPORT.md).

Der Restore deckte eine strikte Modelldependency-Abweichung durch neue Supportpakete auf. Numerische Core-Locks bleiben nun bytegetreu erhalten; Assistentenpakete werden separat mit --no-deps gepinnt. Keine Modellgates oder historischen Artefakte geändert. Kein Push, kein Release, Remote-CI für diese Änderungen nicht verifiziert. Bisherige reale Daten-, Quellen-, Modell-, Strategie-, Homelab/VPN-, CA- und Backup-Betriebsgates bleiben offen.

## P9-Abnahme abgeschlossen — P10 beginnt (2026-10-15)

Ausgangspunkt `main`, `1294080ba0042706d4df99f37f39646aea736673`, sauber. Baseline erneut 155 Backend-Tests. GitHub-Lauf `38561223407` für den Ausgangscommit wurde vom Nutzer bestätigt; neue Änderungen wurden nicht gepusht. **REMOTE CI NOT VERIFIED FOR THIS CHANGE.**

**P9 FUNCTIONAL — RECOMMENDATIONS GATED; V3 NOT VALIDATED.** Versionierte private Profile, harte Eligibility, feste reproduzierbare Rubrik/Ranking, P4/P5/P7/P8-Kontext, reine Hypothesen, append-only Bewertungen und historische Strategieverträge mit separatem Operator-Review. Fehlende reale Produktionsprognosen und Strategieevidenz bleiben sperrend. [Separate P9-Abnahme](P9_ACCEPTANCE_REPORT.md).

Verifiziert: 173 vollständige Backend-Regressionsfälle, danach 12 P6/P9-Fälle einschließlich eines zusätzlichen Anfangszustands-Goldens (174 Fälle im Bestand); elf Browserfälle, Ruff/Format/Mypy, Frontend lint/typecheck/build, Compose, driftfreie und frische Migration 0015 mit 55 Tabellen. MLflow-Ausfall bestanden. Isolierter Restore am 2026-10-15 einschließlich P9-Profil-/Regel-/Recommendation-Replay und P7/P8-Historien, Raw-/Modell-Hashes sowie exakt CHF 10'180 bestanden. P4-Zielinstallationsgates bleiben offen.

P10 wurde anschließend separat umgesetzt und technisch abgenommen; siehe aktueller Stand oben.

## P7/P8-Auftrag — technisch abgeschlossen (2026-10-14)

Start: `main`, `552e96b106903422d4d07a5e4eb5ba1e56873878`; lokal und remote identisch. Ausgangsverzeichnis sauber. Baseline erneut: 113 Backend-/6 Browser-Tests. Der Commit-Workflow-Lookup lieferte keine Runs; neue Änderungen wurden nicht gepusht, Remote-CI bleibt unbestätigt.

**P7 FUNCTIONAL — MODELS SHADOW / DATA LIMITED**, separat vor P8 abgenommen: 142 Backend-/8 Browser-Tests, sechs native CPU-Modelle, tatsächlich ausgeführter synthetischer Celery-Trainingslauf, private MLflow/Auth/Artefakte, Ausfallprüfung und isolierter Restore. **V2 NOT VALIDATED**; keine reale Modell-Promotion. [P7-Abnahme](P7_ACCEPTANCE_REPORT.md).

**P8 FUNCTIONAL — RISK DATA LIMITED**: P4-Ledger-Returns, Kalender-/Actions-/FX-Gates, Risiko/Exposure/Health, sieben Szenarien, reine What-if-Hypothesen, immutable Snapshots und APIs/UI. Abschluss: **155 Backend-/10 Browser-Tests bestanden**, Frontend lint/typecheck/build, Ruff/Format/Mypy, Alembic 0014 driftfrei und frisch mit 50 Tabellen. MLflow vollständig gestoppt: Portfolio, Research und Risiko verfügbar. Isolierter Restore am 2026-10-14 bestanden einschließlich Modell-/Prediction-/Risk-/Scenario-/What-if-Hashes und exakt CHF 10'180. [P8-Abnahme](P8_ACCEPTANCE_REPORT.md).

Reale historische Risiko-/PIT-Daten sind weiterhin unvollständig. **V2.5 NOT RELEASED**; bestehende Homelab/VPN-, CA-, Backup-Schedule/Mount- und Schlüssel-Recovery-Gates bleiben offen. Ungenehmigte Quellen bleiben deaktiviert. **P9/P10 nicht begonnen.**

**Updated:** 2026-10-14
**Source of truth:** [Master Development Plan](../MASTER_DEVELOPMENT_PLAN.md), section 158.

| Assignment phase | Plan mapping | Status | Delivered |
| --- | --- | --- | --- |
| Phase 0 — project foundation | P0 | DONE | Repository rules, Compose and architecture decisions. |
| Phase 1A — minimal core | P1 subset | DONE | Next.js, FastAPI, settings, PostgreSQL, Alembic and pgvector. |
| Phase 1B — data/background foundation | P1 subset | DONE | Valkey, Celery, MinIO and readiness. |
| Phase 2 — authentication | P1 subset | DONE | Private Argon2id login, sessions, TOTP, settings and audit. |
| P1 raw-ingestion closure | P1 | DONE | Immutable raw objects, hash verification and provenance. |
| Phase 3 — Instrument Master | P2 | DONE | Stable instruments, identifier history, source gate, gated OpenFIGI mapping and CSV preview. |
| Phase 4 — Market Data Foundation | P3 | DONE WITH GATED SOURCES | Manual CSV preview/commit, canonical and versioned prices/actions/FX, validation, reconciliation, quarantine, PIT queries, indicative return, FX derivation, ECB connector, data-quality and UI. PR1 adds verified monthly SNB macro contracts; daily SNB FX remains unavailable. |
| Portfolio and production access | P4 | FUNCTIONAL — PRODUCTION GATE OPEN | Owned portfolios/accounts, preserved transaction ledger, Decimal WAC, corporate-action application, P3 valuation/FX, returns, snapshots with provenance, transaction CSV, portfolio UI, Caddy/private TLS, monitoring and verified isolated recovery. Target homelab/VPN client trust and an independent production backup mount still require deployment acceptance. |
| Fundamentals and Research | P5 | FUNCTIONAL WITH GATED SOURCES | Versioned fundamentals/filings, metrics, valuation, research, news and estimates; no automatic source activation. |
| Point-in-Time and Backtesting | P6 | FUNCTIONAL WITH HISTORICAL DATA LIMITATIONS | Evidence reviews, strict/reconstructed modes, historical membership, offline calendars, feature/dataset versions and content manifests, targets, purging/embargo, baselines, cost/execution contracts, private APIs/UI and monitoring. Real historical completeness is not inferred from synthetic tests or late imports. |
| Machine Learning and Forecasts | P7 | FUNCTIONAL — MODELS SHADOW / DATA LIMITED | PIT readiness/composition, six local CPU estimators, chronological training/calibration/evaluation, fixed operator promotion gates, private MLflow, immutable forecasts/outcomes, model APIs/UI and restore. V2 not validated. |
| Risk and Scenario Intelligence | P8 | FUNCTIONAL — RISK DATA LIMITED | Ledger TWR, validated risk statistics, exposures, versioned Health, seven scenarios, immutable hypothetical trades/snapshots, owned APIs/UI, monitoring and verified recovery. V2.5 target deployment not released. |
| Structured Recommendations | P9 | FUNCTIONAL — RECOMMENDATIONS GATED | Private profile/rule versions, hard eligibility, deterministic ranking, P8 previews, immutable history, historical P6 strategy replay and separate promotion. V3 not validated. |
| Local Assistant and Intelligence | P10 | FUNCTIONAL — DATA/SOURCE GATED | Evidence-only local chat, private RAG, alerts/briefs, constrained simulations, historical archives and verified isolated recovery. V3+ not released. |

## P3 contracts and limits

- Manual CSV is the functional input for daily prices, corporate actions and FX. Raw bytes precede parsing; committed values reference their verified raw object. The P2 preview still creates no canonical data. Repeated P3 commit is idempotent.
- Price/action/FX current rows point to append-only versions. `known_at` and explicit timezone-aware `as_of` prevent later corrections from appearing in earlier queries. No historical local availability is inferred from an old event date.
- Hard-invalid rows are rejected and, on explicit partial commit, quarantined. Close disagreement thresholds are 0.25%, 0.50% and 2%; manual override requires a reason. Quality components use 40/25/15/10/10 weights after validation.
- Return arithmetic uses raw close plus explicit validated actions. The API labels results `PROVISIONAL` because P3 cannot attest complete action coverage. Adjusted close is never added to those returns.
- FX supports CHF, EUR and USD, direct/inverse/cross conversion and bounded, visibly dated carry forward (`FX_MAX_CARRY_DAYS`, default 5). No valid rate yields `UNAVAILABLE`.
- Source states: `MANUAL_CSV` APPROVED/enabled; `YAHOO` BLOCKED/disabled; `STOOQ` and `OPENFIGI` UNKNOWN/disabled; `SNB` and `ECB` UNKNOWN/disabled. No live financial provider was activated or called during this phase. The ECB collector has a documented CSV contract behind the gate. The SNB stub remains `SOURCE_FORMAT_UNVERIFIED` after gate approval until a daily series is verified.
- The protected `/imports`, `/data-quality` and instrument pages show import, quality and canonical price states. The legacy instrument CSV preview remains available.

## Verification

- Baseline on `e4c60ba`: 27 backend tests, Ruff, Mypy, frontend typecheck and Compose configuration passed locally. The earlier GitHub Actions run on that commit was reported successful by the user; no remote CI action was initiated for P3.
- After P3: `docker compose exec -T api pytest -q`: **48 passed**, one upstream Starlette warning. Integration tests cover preview/commit, repeat import, correction and `as_of`, quarantine, actions, FX and source gates. No test calls a live provider.
- Existing database upgraded to `0005_p3_contract`; disposable database migration from `0001` through `0005` verified 13 required tables. See `python -m scripts.verify_fresh_migration`.
- `docker compose up -d --build`, `docker compose config --quiet`, Ruff, Mypy, frontend lint/typecheck/build, Alembic schema check, Celery and MinIO smoke checks passed locally. All seven Compose services were healthy and API readiness returned HTTP 200.

## Operational boundary

Local Compose binds public ports to localhost over HTTP. The separate P4 production stack provides HTTPS and Secure cookies, private backend/MinIO access, Prometheus/Grafana and configurable independent backups. Production use still requires acceptance on the actual homelab/VPN hostname and browser trust store, an independent protected backup mount, a daily host schedule and encrypted key recovery. The local tests establish the application and recovery path; they do not establish those external deployment conditions. The P3 source gates are unchanged. See [deployment](architecture/production-deployment.md), [backup/restore](architecture/backup-restore.md) and [P4 acceptance report](P4_ACCEPTANCE_REPORT.md).

## P4 contracts

- Migration `0006_portfolio` adds eight tables: benchmarks, portfolios, portfolio_accounts, transactions, portfolio_action_applications, cash_balances, position_snapshots and portfolio_snapshots. `0007_snapshot_provenance` adds nullable knowledge cutoff and exact input references; existing unknown provenance stays null. No prior migration was changed.
- User ownership is checked on portfolio, account, transaction and derived-report operations. Portfolio-row locks serialize accounting writes and rebuilds. Corrections preserve the old transaction and append a replacement; void timestamps preserve earlier PIT replay.
- WAC includes buy costs; sale fees/taxes reduce proceeds and realized P/L. Negative cash remains visible, oversells fail. Corporate actions apply explicitly and idempotently, block manual double counting and require review for revisions, same-day split/income entitlement and delisting settlement.
- Raw closes and P3 dated FX supply native/base valuations. Missing/stale prices, missing FX and unresolved eligible actions leave the total null and the portfolio `PARTIAL`. Event-date FX provenance supplies realized P/L, income, fees and taxes. Missing historical FX leaves only those analytics unavailable.
- Absolute return, daily-linked TWR, bounded conventional-flow XIRR, annualized TWR CAGR and opening-exposure FX contribution have documented definitions. Portfolio and real-instrument benchmark returns remain `PROVISIONAL` while corporate-action coverage is unverified. Dashboard sums stay in backend Decimal and are grouped by base currency.
- Transaction CSV persists exact raw bytes before preview, supports editable mapping and dated ticker/ISIN/FIGI resolution, and commits atomically. Broker IDs take precedence over normalized fingerprints. Invalid references, ambiguity, duplicates or overselling block commit.
- Portfolio pages provide overview, holdings, performance/value chart, allocation charts, income, transaction entry/correction/void/import and data-quality issues. No P5 or later product feature was introduced.

## P4 verification

Final commands, recovery artifacts, local production evidence and remaining deployment gates are recorded in [P4 acceptance report](P4_ACCEPTANCE_REPORT.md). Remote CI has not been run or reported successful for this work. **V1 NOT READY for an unverified target production deployment.**

The local backend suite now contains 61 passing cases; the two browser cases include explicit dividend-cost confirmation and split application. Manual/canonical effects can be linked after exact review, without double booking. Pre-event quotes and invalid preserved ledger rows cannot become invented valuations. The executable Windows scheduling installer is provided and syntax checked; installation against a real production target remains an operator step.

## P5 — Fundamentals & Research

**Status: FUNCTIONAL WITH GATED SOURCES.** Append-only fundamental facts and filings, public/local availability separation, restatements, SEC JSON and explicit primary-document storage, global SEC limiter, Company-IR CSV contract and manual fundamental import, deterministic metrics/valuation/scores, materialized database screener, private watchlists, deduplicated news metadata, typed estimate snapshots and source-gated scheduling are implemented locally. No real company-specific HTML/PDF IR parser or automatic estimate provider has been accepted. Momentum and forward metrics remain unavailable where the required coverage/estimate contracts are absent.

New sources SEC_EDGAR, COMPANY_IR, NEWS_RSS and MANUAL_RESEARCH are **UNKNOWN/disabled**. Existing source gates remain unchanged. Synthetic fixture sources are local test data and do not grant external rights. Migration heads 0008_research and 0009_filing_document add nine tables and distinguish exact response versus primary-document hashes. Earlier migrations are unchanged. Both existing-schema upgrade and fresh migration through 30 required tables passed.

Baseline: main at af101ffed5203cc098599c1409587fd93d1ec421, clean working tree, 61 passing backend cases. P5 regression: 89 backend cases passed, plus the P4 and P5 browser acceptance cases. Ruff/Mypy and frontend lint/typecheck/build passed locally. Screener with 300 isolated instruments used four SELECTs and returned 25 rows in 0.233 seconds on this machine; no market-wide performance guarantee is inferred. Isolated recovery preserved the P5 raw hash and exact CHF 10'180 portfolio value. Detailed commands and limitations: [P5 acceptance](P5_ACCEPTANCE_REPORT.md).

**P4 remains FUNCTIONAL — PRODUCTION GATE OPEN. V1/V1.5 NOT PRODUCTION READY for the unverified target installation.** Hostname/VPN, browser CA trust, independent protected backup mount, daily host schedule and encrypted key recovery remain operator acceptance conditions. P6 was not started. **REMOTE CI NOT VERIFIED FOR THIS CHANGE**; the workflow was extended locally to prepare isolated fixtures and run browser tests, without push or release.

## P6 — Point-in-Time / Backtesting

**FUNCTIONAL WITH HISTORICAL DATA LIMITATIONS**, 2026-10-14. The P5 closure above describes its historical state; P6 has now been explicitly requested and implemented. The foundation distinguishes public/local knowledge and review availability, immutable content-pinned inputs, exact session horizons and realized labels, purged/embargoed splits, quantitative baselines and next-session execution. Unknown membership, missing price/FX and unverified action coverage remain excluded or incomplete. No P7 model training or forecasts were introduced.

Local verification: **113 backend tests and 6 browser tests passed**, Ruff/format/Mypy, frontend lint/typecheck/build, Compose, existing/fresh migrations through **0012_pit_immutability** (41 required tables), Celery and MinIO smoke. Golden end value 1098.90 on 1000 capital with one 1-unit fee. Private cross-user access and missing pinned input/immutable update rejection are tested. Detailed contracts, verification and limits: [P6 acceptance report](P6_ACCEPTANCE_REPORT.md).

CI EACCES was confirmed in actual GitHub logs and reproduced on Linux. The browser runner now installs into a separate runner-owned temporary directory. **REMOTE CI NOT VERIFIED** for the correction; no push/release. P4 production gates and P5 source limitations remain open. Actual historical availability/universe coverage is required before any strict P7 dataset/model acceptance.

P6 backup/isolated recovery passed on 2026-10-14: head 0012, exact raw hashes, private login, CHF 10'180 portfolio value and the pinned P6 dataset content hash survived. See the acceptance report for the local backup set and dataset identifier. This does not close the independent production backup-mount/schedule/key-recovery gates.
