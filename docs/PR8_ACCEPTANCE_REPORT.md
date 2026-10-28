# PR8 – Private Core V1 Release Readiness

Stand: 27.10.2026. **LOCAL_SYNTHETIC_VERIFIED / NOT_RELEASED.** Lokaler Core-Kandidat, Regressionssuite, Backup und isolierter Restore sind geprüft. Keine produktive Umschaltung, kein Push, kein Release und keine Source-/Modell-/Strategiepromotion.

| Getrenntes Gate | Aktueller Status |
| --- | --- |
| REMOTE_CI_STATUS | VERIFY_PASSED_SECURITY_FAILED; PR8_WORKTREE_NOT_REMOTE_VERIFIED |
| SECURITY_STATUS | SECURITY_BLOCKED |
| OBJECT_STORAGE_STATUS | LOCAL_CORE_S3_AND_FINAL_CLIENT_RESTORE_VERIFIED |
| POSTGRESQL_STATUS | LOCAL_PG17_AND_FINAL_RESTORE_VERIFIED |
| CORE_FUNCTIONAL_STATUS | LOCAL_SYNTHETIC_CORE_VERIFIED |
| UX_STATUS | AUTOMATED_30_PASS; INDEPENDENT_USER_TEST_PENDING |
| REAL_PORTFOLIO_STATUS | PENDING_ORIGINALS_AND_SECURITY_APPROVAL |
| LIVE_DATA_STATUS | BLOCKED_BY_SOURCE_APPROVAL |
| AUTOMATIC_REFRESH_STATUS | CURRENT_HOLDINGS_PLANNER_GATED; LIVE_CONTINUITY_UNVERIFIED |
| TARGET_HOST_STATUS | TARGET_HOST_NOT_VERIFIED |
| BACKUP_RECOVERY_STATUS | LOCAL_TARGET_BACKUP_AND_1383_FILE_RESTORE_VERIFIED; INDEPENDENT_TARGET_SCHEDULE_PENDING |
| PREFLIGHT_STATUS | CONFIGURATION_BLOCKED_BACKUP_FREE_SPACE_BELOW_5_GIB |
| PRIVATE_CORE_V1_STATUS | NOT_RELEASED |
| FORECAST_VALIDATION_STATUS | NOT_VALIDATED_SHADOW_ONLY |
| RECOMMENDATION_VALIDATION_STATUS | NOT_VALIDATED_GATED |

## Nachweise

**306 Backend-, 82 Host- und 30/30 Browserfälle** bestanden; Frontend-Lint, Typecheck und Standalone-Build ebenfalls. [Maschinenlesbarer Testbeleg](security/pr8-20261027/test-results.json). Testmodus und Rollen nach Browserlauf zurückgesetzt. Der endgültige Scope umfasst **13 Services / 9 unterschiedliche Images**, dazu 13 formal validierte SBOMs. Der neue separate MC-Client ersetzt den alten MinIO-Client im Core-Recoverypfad. Zielbackup und isolierter Restore prüfen **1383 Dateihashes** bei unveränderten alten Archivverträgen. Eine aktuelle synthetische CHF-10’180-Bewertung, tatsächlicher Prometheus-Scrape und der strukturierte Assistentenausfall ohne Ollama sind nachgewiesen. Diese Ergebnisse sind keine Abnahme realer Depotoriginale.

Kandidat: [pr8-core-v1-rc3-manifest.json](../ops/releases/pr8-core-v1-rc3-manifest.json); [Scope](../ops/releases/pr8-core-v1-scope.json), [RC3-Inventar](security/pr8-20261027/core-rc3/inventory.json), [SBOM-Prüfung](security/pr8-20261027/core-rc3/sbom-validation.json), [Source-Scan](security/pr8-20261027/source-security-receipt.json), [read-only Preflight](security/pr8-20261027/core-preflight-v2.json). Das Manifest bindet auch die tatsächlich beim Restore verwendeten Runtime-/Recovery-Digests. Ein Manifest ohne tatsächliche Freigaben autorisiert keine Installation.

- [Security und tatsächliche CI](PR8A_SECURITY_RELEASE_REPORT.md)
- [Core-Deployment, Vorprüfung und Cutover/Rollback](PR8B_DEPLOYMENT_REPORT.md)
- [Quellen und tatsächliche Holdings-Aktualisierung](PR8C_DATA_PROVIDER_REPORT.md)
- [Realer Pilot und Anfängerabnahme](PR8D_REAL_PORTFOLIO_REPORT.md)
- [Technische Regression und Archivprüfung](PR8E_CORE_ACCEPTANCE_REPORT.md)

## Noch zwischen Kandidat und privater Nutzung

1. Alle relevanten verbleibenden High-/Critical-Befunde, isolierten alten Modell-Verifier, native Build-/Wartungsgrenzen und Style-CSP bewerten. Backend: 44 High in einem gemeinsam verwendeten Image; erforderlicher archivierter Modell-Verifier: 1 Critical/47 High. Tatsächlicher Securityreview mit Beleg/Person/Frist; keine automatische Ausnahme. Alter MinIO-Bestand bleibt ausschließlich Entwicklungs-/Migrationsquelle, seine historischen 9 Critical/125 High werden nicht als behoben dargestellt.
2. Am vorgegebenen C:-Backupziel ausreichend freien Platz bereitstellen und read-only Preflight wiederholen. Letzter Bericht: 3’915’988’992 freie Bytes, Mindestprüfgrenze 5 GiB; keine automatische Fremddaten-/Volumelöschung. Der lokale erfolgreiche Restore bleibt ein eigener Nachweis und ersetzt keinen unabhängigen Backupzeitplan.
3. Zielhost bereitstellen und autorisieren. VPN/DNS, Windows-/Android-CA, Login/TOTP, unabhängiges Backupziel mit Zeitplan/Restore, Alarmzustellung, Schlüssel-Recovery und Neustartverhalten tatsächlich abnehmen. Die vorhandene Antwort „lokal vorbereiten“ bleibt gültig.
4. Entweder konkrete externe Nutzungs-/Speicher-/Analyzerechte freigeben und initialen sowie späteren Liveabruf nachweisen, oder rechtmäßig bereitgestellte manuelle Originale verwenden. Allgemeine verschiedene ISIN bleiben möglich; automatische universelle Kursversorgung wird nicht behauptet.
5. Nach Security-/Hostfreigabe echte private Originale in einem eigenen Pilotaccount importieren und Positionen, Cash, Gebühren/Steuern, Dividenden/Splits und CHF-Bewertung am gleichen Brokerstichtag erklären. Keine Ausgleichsbuchungen zur Ergebnisanpassung.
6. Tatsächliche unabhängige Anfängerperson testen lassen und konkrete gravierende Hürden beheben. Anschließend separate Operatorfreigabe des exakten Manifests; ein später autorisierter Push benötigt neue tatsächliche CI. Der bereits angeforderte Remote-Lauf 40475316877 endete mit Verify success und Security failure.

Fehlende Daten, veraltete Kurse, ungeklärte Identifier/Corporate Actions und FX bleiben sichtbar unvollständig. Forecasts und Empfehlungen sind von Core unabhängig gesperrt. 0 CHF verpflichtende API-Kosten betrifft keine Hardware-/Betriebskosten. Synthetische Nachweise sind keine reale Depot-, Quellen-, Host- oder Investmentvalidierung.
