# PR4C – Release-Candidate-Verifikation

## Aktueller Nachweis vom 21.10.2026

PR4C: neue Regression 266 Backend / 21 Browser / 32 Hosttests; frischer Restore mit 355 Raw-Objekten, CHF 10’180 und unveraenderten Archivvertraegen bestanden. Neuer RC PR4-LOCAL-20261021-01: RC_TESTED / RC_SECURITY_BLOCKED. Zielhost weiter nicht verfuegbar.

[Neue Abnahme und priorisierte Restarbeit](PR4_ACCEPTANCE_20261021.md). Die folgenden Angaben vom 19./20.10. bleiben als historische Nachweise erhalten; sie sind nicht der aktuelle Sicherheitsstand.


Stand: 20.10.2026. **Lokale Verifikation bestanden; SECURITY_BLOCKED; TARGET_HOST_NOT_VERIFIED.**

Git-Basis: `581a13c415d20ff8594d5ecf97b98226b8b5c74e`; Änderungen lokal und uncommitted. Kein Push, kein Remote-CI-Erfolg und kein Release für PR4 behauptet.

## Kandidat und Herkunft

- RC-ID: `PR4-LOCAL-20261020-01`; [unveränderliches Manifest](releases/PR4_LOCAL_20261020_01.json).
- Das Manifest bindet zusätzlich zum Basiscommit die tatsächlichen Git-sichtbaren Quelldateibytes einschließlich neuer Dateien. Ein HEAD allein würde den Kandidaten nicht beschreiben.
- Zehn Image-/Config-Digests, zehn originale SBOM-Hashes, vier unveränderte Dependency-Locks, Konfigurationsvertrag `PR4-1`, Alembic `0019_validation`, Report-/Test-/Restore-Hashes und 15 Servicezuordnungen stehen im Manifest. [Imagebestand](security/PR4_IMAGE_INVENTORY.json), [SBOM-Inventar](security/PR4_SBOM_INVENTORY.md).
- Eigene Images sind lokal vorhanden. Ein späterer Zielhost benötigt einen verifizierten Transport exakt dieser Bytes; keine öffentliche Registry-Verfügbarkeit behauptet und kein erneuter Build beim Rollout.

Das Manifest wird append-only angelegt. Inhalt, Artefakte und Quellbestand müssen bei Validierung übereinstimmen. Ein anderer Build, abweichende Dateien oder ein anderer Digest verlangt neue Evidenz. Die lokalen Gates sind ausdrücklich keine Operatorgenehmigung; Produktionsausführung muss diesen Kandidaten zurückweisen.

## Regression und Laufzeit

**264 Backendtests, 21 Browserfälle ohne Skips und 30 Host-/Security-Vertragsfälle bestanden.** Ruff/Format/Mypy, Frontend lint/typecheck/Standalone-Build, frische Migration und Compose-Prüfungen bestanden. Details und Grenzen der unterschiedlichen Prüfaufbauten: [PR4B](PR4B_REMEDIATION_REPORT.md), [Gesamtabnahme](PR4_ACCEPTANCE_REPORT.md), [maschineller Nachweisindex](security/PR4_VERIFICATION_EVIDENCE.json).

Produktions-Staging: alle 13 Langzeitdienste gesund, CA-Export erfolgreich, 14 beobachtete Rollen an die gescannten Images gebunden. Private HTTPS-/Auth-/Cookie-/CSRF-/Monitoring- und Browserproben bestanden. Core- sowie MLflow-/Ollama-Ausfälle geprüft; tatsächlicher authentifizierter MLflow-S3-Artefakt-Roundtrip bestanden. Ollama-Serverprüfung enthält keine Modellinferenz oder GPU-Abnahme. [Runtimebestand](security/PR4_RUNTIME_INVENTORY.json), [Faultnachweis](security/PR4_FAULT_EVIDENCE.json).

## Frischer vollständiger Restore

Backup `20261020T145904Z-5272`, **20.10.2026 14:59:04–14:59:18 UTC**. 342 Raw-Objekte, 1'505'900 Raw-Bytes; mit Datenbankdump 2'993'018 Bytes. 343 Dateihashes vor dem Import geprüft. API, Worker, Scheduler und UI waren für den Checkpoint/Backup angehalten; danach wurden die normalen lokalen Dienste wieder gestartet.

Isolierter Restore **14:59:43–15:00:41 UTC**, **57,91 Sekunden**, erfolgreich. Backend `c35ab504…`, PostgreSQL `72b5b100…`, MinIO `69b55a1c…`: vollständige Digests im [Restore-Nachweis](security/PR4_RESTORE_EVIDENCE.json). Cleanup erfolgreich bis **15:00:48 UTC**, temporäre Container/Volumes entfernt. Kein unabhängiges Produktionsbackup aus diesem lokalen Verzeichnis abgeleitet.

Bestätigt: Golden exakt **CHF 10'180**; P6-Hash `dd5cd6ef97b9248eb148725797470069b9b33635df15f8506d61bf99761ea538`; P7-Artefakthash `9706d2dc2631d0cfde24ddaad3ccd4f41b686351cd5b82ecd5e0a96fc18f5c94`; strikte numerische Dependency-Verträge; aktuelle Prediction-/Outcome-, P8-, P9-, P10-, PR1- und PR2-Checkpoint-Hashes. Zwei Dokumentoriginale mit zwei Chunks/Embeddings gehören zum geprüften Archiv. Alte PR3-Nachweise wurden separat mit den ersten Kandidaten wiederhergestellt und bleiben unverändert.

Die Browserprüfungen ergänzen legitime synthetische Versionen. Der neue Checkpoint enthält deshalb 41 Predictions, 59 Risiko-, 30 Szenario-, 30 What-if-, 16 Recommendation- und 15 Profilversionen. Diese neuen Historien werden weder rückdatiert noch als unveränderte alte Gesamtzählung ausgegeben. Alle bereits vorhandenen Quellengates sind unverändert. Archivierte alte Daten-/Modellmanifeste wurden nicht angepasst.

## Fehlversuche und Restgrenzen

Frühere Browserläufe unter Ressourcenlast und der mehrdeutige PR3-Systemstatus-Selektor sind dokumentiert. Selektoren/Antwort-/Ladewartebedingungen wurden korrigiert; finanzielle Assertions bleiben erhalten. Ein Legacy-Restore scheiterte zunächst am fünfsekündigen Testclienttimeout, ein Ollama-Export am Zeitlimit; getrennte erfolgreiche Läufe ersetzen diese fehlgeschlagenen Aufzeichnungen nicht rückwirkend. Zwischenzeitlich waren alle eigenen Abhängigkeiten gestoppt; die Ursache wurde nicht nachgewiesen. Proben aus diesem Zustand sind Fehlversuche, keine erfolgreiche Verfügbarkeitsevidenz. Keine Host-/Docker-Neustarts zur Behebung ausgeführt.

Trivy 0.76.0 mit DB vom **20.10.2026 07:17:35 UTC**: alle zehn unterstützten Paketläufe abgeschlossen, zehn SBOMs formal gültig. Vier rohe Critical-Befunde in PostgreSQL und neun in MinIO bleiben offen; keine genehmigten Exceptions. Weitere High-Befunde, Ollamas native Library-Abdeckung und die dokumentierte CSP-`unsafe-inline`-Einschränkung bleiben zu behandeln. [Matrix](security/PR4_REMEDIATION_MATRIX.md), [Restliche Risiken](security/PR4_RESIDUAL_RISKS.md).

Kein neuer Remote-CI-Lauf, Push oder Release. Die neue CI soll diese unbehandelten Critical-Befunde blockieren. Zielhost/VPN/DNS/Client-CA-Trust, unabhängiges Backup, Tagesjob, Schlüssel-Recovery, Alarmzustellung und Hostneustart bleiben offen.

Unveränderte Gates: `SECURITY_BLOCKED`, `TARGET_HOST_NOT_VERIFIED`, `REAL_DATA_LIMITED`, `FORECASTS_SHADOW_ONLY`, `RECOMMENDATIONS_GATED`, `V3+ NOT RELEASED`.
