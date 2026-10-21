# PR4 – lokale Abnahme und verbleibende Freigabegates

Stand: 20.10.2026. **PR4 technisch implementiert und lokal verifiziert. Keine Produktionsfreigabe.**

## Getrennte Zustände

| Bereich | Ergebnis |
|---|---|
| PR4 technical status | PR4A Assessment abgeschlossen; PR4B lokal kompatibel geprüft; PR4C lokaler RC verifiziert |
| Security release status | **SECURITY_BLOCKED**: PostgreSQL 4 / MinIO 9 rohe Critical-Paketbefunde, weitere High-/manuelle Reviews; keine genehmigten Exceptions |
| Private deployment readiness | Lokal vorbereitet und getestet; Manifest-/Digestverfahren vorhanden, kein Produktionsrollout |
| Target host verification | **TARGET_HOST_NOT_VERIFIED**, Zielhost laut Nutzer noch nicht verfügbar |
| Source approval status | Bestehende Gates unverändert; keine externe Finanzquelle aus PR4 freigegeben oder aktiviert |
| Real data readiness | **REAL_DATA_LIMITED** |
| P7 model validation | **FORECASTS_SHADOW_ONLY**, keine reale Prognosefreigabe |
| P9 strategy validation | **RECOMMENDATIONS_GATED**, keine Strategiefreigabe |
| V3+ release status | **NOT RELEASED** |

## Abnahmen je Phase

- [PR4A](PR4A_SECURITY_ASSESSMENT_REPORT.md): Git-/CI-Baseline, vollständiges Inventar, Primärquellenprüfung, Exposure und priorisierte Maßnahmen. PR3-CI `39242444587` tatsächlich `completed/failure`: 264 Backendtests und 20/21 Browserfälle bestanden; der Systemstatus-Selektor traf zusätzlich den Next-Routenansager. Selektor korrigiert und anschließend vollständig lokal geprüft.
- [PR4B](PR4B_REMEDIATION_REPORT.md): kompatible Basis-/Imageupdates, Runtimehärtung, privates HTTPS/CA/Auth/Monitoring, MLflow-S3-Probe, Alternativspeicherbewertung ohne Migration und Legacy-Dump-/Restore. Keine numerischen Lock- oder PostgreSQL-Majoränderungen.
- [PR4C](PR4C_RELEASE_CANDIDATE_REPORT.md): vollständige Abschlussregression, frischer Backup-/Restore mit finalen Digests, Faultnachweise, frische Image-DB und unveränderlicher lokaler RC `PR4-LOCAL-20261020-01`.

## Ausgeführte Abschlussprüfungen

| Prüfung | Tatsächliches Ergebnis / Umfang |
|---|---|
| Backend | **264 bestanden**, 397,40 s; neuer Python-3.12.15-/Trixie-Devstand, lokale Services/Fixtures; ein bestehender Starlette-Deprecation-Hinweis |
| Backendqualität | Ruff bestanden; 285 Dateien formatiert; Mypy 197 App-Dateien ohne Fehler |
| Frontend | lint, TypeScript und abgeschlossener Standalone-Build auf Node 24.22 bestanden |
| Browser | **21 bestanden**, 2,1 min, ein Worker, keine Skips; abgeschlossener Build via E2E-Compose, keine gleichzeitige Backendintegration |
| Host/Security | **30 bestanden**, einschließlich ursprünglicher zwölf Betriebsgoldens; Image-/SBOM-Verträge, fehlende Images, Exceptions/Ablauf, Digest-/Quell-/Manifestmanipulation, Redaktion, Backup-Checksumfehler und CI-Preflightfixture |
| Schema | Frisch `0019_validation`, 76 erforderliche Tabellen; gepatchtes PostgreSQL separat im Staging/Restore geprüft |
| Dependency-Audits | Core + Assistant, MLflow und npm-Produktionsabhängigkeiten: kein bekannter Befund, Exit 0; Modell-/Frontend-Locks unverändert |
| Image-/SBOM-Audit | Zehn exakte Images mit vollständigen unterstützten Paketläufen; zehn originale CycloneDX-SBOMs formal und per Hash gültig; native Ollama-Abdeckung separat unvollständig |
| Compose/Preflight | Lokal und Produktion gültig; synthetische sichere Preflightfixture bestanden. Das Loopback-Staging mit `localhost` wird vom strengen Domain-Preflight erwartungsgemäß zurückgewiesen; kein VPN-/DNS-Nachweis daraus |
| Staging | 13 Dienste gesund; CA-Export beendet; HTTPS/CSRF/Cookies/Golden, Prometheus/Grafana, gesperrte interne Metriken und Browser ohne CSP-/Seitenfehler |
| Ausfälle | PostgreSQL, MinIO, Valkey, Worker, Scheduler, API-Neustart sowie MLflow und Ollama kontrolliert geprüft; Core bleibt bei optionalen Ausfällen verfügbar |
| Backup-Abbruch | Nur isolierten Backuphelper während einer vorgeschalteten Testverzögerung beendet; fehlgeschlagenes Set nicht akzeptiert, letzter Erfolgszeiger und dessen Hashes unverändert. Kein behaupteter Mid-Stream-Migrationstest |
| Finaler Restore | 342 Raw-Objekte + Dump, 343 Dateihashes, Golden CHF 10'180, P6/P7/Abhängigkeiten und aktuelle P8/P9/P10/PR1/PR2-Historien bestanden; Cleanup erfolgreich |

[Maschineller Nachweisindex](security/PR4_VERIFICATION_EVIDENCE.json), [Restore](security/PR4_RESTORE_EVIDENCE.json), [Faults](security/PR4_FAULT_EVIDENCE.json), [Runtime](security/PR4_RUNTIME_INVENTORY.json). Prüfungen mit synthetischen Daten belegen technische Verträge und keine reale finanzielle Validierung. Quellenrechte, Verfügbarkeit, PIT- und Modellgates bleiben erhalten.

## Kandidat und Sicherheitsbefunde

[RC-Manifest](releases/PR4_LOCAL_20261020_01.json), [zehn Images](security/PR4_IMAGE_INVENTORY.json), [SBOMs](security/PR4_SBOM_INVENTORY.md), [Vulnerabilityvergleich](security/PR4_VULNERABILITY_REPORT.json), [Maßnahmenmatrix](security/PR4_REMEDIATION_MATRIX.md), [Restrisiken](security/PR4_RESIDUAL_RISKS.md).

Das Manifest bindet Basiscommit `581a13c415d20ff8594d5ecf97b98226b8b5c74e` und uncommittete Quellbytes, Digests, Locks, SBOMs und Nachweise. Eigene Images sind lokale Kandidaten, keine veröffentlichten Registry-Releases. Produktionsstart verlangt separate Security-, Zielhost- und Operatorfreigabe; der lokale Kandidat wird abgewiesen. Keine pauschalen CVE-Ignores oder automatische Exceptions.

MinIO bleibt unverändert und blockiert. SeaweedFS wurde isoliert mit tatsächlichen Minio-/boto3-Aufrufen geprüft (7'020'000 synthetische Bytes); sein eigener Scan meldet 4 High/0 Critical. Advisory-/TLS-/Betriebs-/Migrationsgrenzen bleiben offen; Garage nur anhand Dokumentation gesichtet. [S3-Entscheid](operations/S3_COMPATIBILITY_REVIEW.md). Keine Speicher- oder Datenbankmigration.

## Abschluss und Operatorarbeit

Lokaler Normalbetrieb ist mit `ASSISTANT_TEST_MODE=false`, deaktivierter Collection und Forward Shadow wiederhergestellt; alle zehn lokalen Dienste laufen, alle vorhandenen Healthchecks sind gesund. Der lokale ML-Worker besitzt im Entwicklungs-Compose keinen Healthcheck. Testfreigaben gelten nicht als Produktfreigaben. Staging-Volumes/CA bleiben erhalten. Kein Lesen/Rotieren echter Operator-Secrets, kein öffentlicher Netzzugang, kein Hostneustart, Push, Release, Modell-/Strategiepromotion oder Handel.

Nächste Freigabearbeit: konkrete MinIO-/PostgreSQL-Behandlung, verbleibende High-/native/CSP-Reviews, erneuter frischer Scan jedes geänderten Digests und separat autorisierte Zielhost-Abnahme. [Installationsablauf](operations/DEPLOYMENT_GUIDE.md), [Operatorcheckliste](operations/OPERATOR_ACCEPTANCE_CHECKLIST.md), [Upgrade/Rollback](operations/UPGRADE_ROLLBACK.md). Linuxvorlagen sind vorbereitet; tatsächlich geprüft wurde Windows mit Docker Desktop, kein Linux-Zielhost. VPN/DNS/Firewall, Client-CA-Trust, unabhängiges verschlüsseltes Backup, Tagesjob, Schlüssel-Recovery, Alarmempfang und Hostneustart benötigen echte Nachweise.
