# PR4B – Image-Härtung und Kompatibilität

## Aktueller Nachweis vom 21.10.2026

PR4B: PostgreSQL pr4-rc2 (17.11/pgvector 0.8.6), Backend pr4-rc3 und MLflow pr4-rc4 neu gebaut, exakt gescannt und im lokalen Restore/Staging geprueft. Core-Modelllock unveraendert; separater MLflow-Lock mit certifi 2026.10.19/Pillow 13.0.0. Keine produktive Migration.

[Neue Abnahme und priorisierte Restarbeit](PR4_ACCEPTANCE_20261021.md). Die folgenden Angaben vom 19./20.10. bleiben als historische Nachweise erhalten; sie sind nicht der aktuelle Sicherheitsstand.


Stand: 20.10.2026. **Lokale Kompatibilität geprüft; SECURITY_BLOCKED.** Kein Produktionsrollout. Die abschließende Restore-Abnahme wird im [PR4C-Bericht](PR4C_RELEASE_CANDIDATE_REPORT.md) separat an den finalen Imagebestand gebunden.

## Geprüfte Änderungen

| Komponente | Änderung | Bereits nachgewiesen |
|---|---|---|
| Caddy | Anwendung 2.11.7, eigener Build Go 1.27.2 / x/net 0.60.0; OS-Patches | Privates HTTPS mit bestehender CA, Reverse Proxy, MinIO-TLS, Auth/Cookies, gesperrte öffentliche Metriken; read-only/cap-drop-Staging |
| PostgreSQL | OS-Patches; PostgreSQL 17.11, pgvector 0.8.6 beibehalten | Unverändertes PR3-Dump und alle archivierten Prüfverträge erfolgreich isoliert wiederhergestellt |
| Backend | Python 3.12.15 / Debian Trixie, Basisdigest gepinnt | Alte P6-/P7-Verträge, Modellabhängigkeiten und Historien im Restore; HTTPS/Auth/Golden im Staging |
| Web | Node 24.22.0 LTS, Alpine-Patches; npm/Corepack/Yarn aus Runtime entfernt | Neuer Standalone-Build, Staging-Login/Logout, keine CSP-/Hydrationfehler |
| Prometheus | 3.15.0 per Digest | Konfiguration und 14 Alertregeln gültig, API-Scrape erreichbar |
| Grafana | 12.4.13 per Digest | Bestehende Daten/provisioniertes Dashboard und authentifizierter Zugriff; anfängliches unhealthy unter Last, danach gesund |
| MLflow | Python-Basis wie Backend; UID 10001, read-only, tmpfs, cap-drop; unbenötigte Serverjobs aus | Neuer Trackingserver gesund; Basic Auth und echter S3-Artefakt-Roundtrip mit SHA-256 bestanden; erster Kandidatenstart bleibt als Fehlversuch erhalten |
| Ollama | 0.40.4 beibehalten; read-only/tmpfs/cap-drop | Server/Health und kontrollierter Ausfall bestanden; vollständiger unterstützter Paketlauf und ergänzende native Dateihashes. Native Security-/Inferenz-/GPU-Abnahme offen |
| Valkey | Bestehende Version, exakter Digest | Core-Fault-/Recovery-Probe bestanden |
| MinIO | Bestehende Bytes per Digest festgehalten | SDK-, Backup-/Restore- und Staging-Kompatibilität; offene Critical-Befunde, kein Speicherwechsel |

Buildrezepte: `backend/Dockerfile`, `frontend/web/Dockerfile`, `ops/caddy/Dockerfile.candidate`, `ops/postgres/Dockerfile.candidate`, `ops/mlflow/Dockerfile`. Die eigenen Images sind lokale RC-Builds, nicht als öffentliche Registry-Releases ausgegeben. Paketarchive/Repositorien können sich ändern: erneute Builds verlangen neue Digests und vollständige Prüfung. Der spätere Rollout verwendet ausschliesslich die tatsächlich geprüften Imagebytes.

## Bereits ausgeführte Recovery-/Sicherheitsprüfung

Unverändertes PR3-Backup `20261019T103107Z-64300`, separater Restore am 20.10.2026, **06:20:27–06:23:44 UTC**, bestanden. Backend `sha256:3b42fc95388c400d24d1056bb875e8c6183394760ca235fab5d6077e151e76b1`, PostgreSQL `sha256:72b5b100d4271206baa9d3ca49c451766dcd163077d17264dd3c183720465bb2`. 320 Raw-Objekte/2'914'753 Bytes im ursprünglichen Backup; Integritätsprüfung vor dem Import; strikte Daten-/Modell-/Historienprüfungen und exakt CHF 10'180 im Verifikationsskript. Die isolierten Container/Volumes wurden entfernt. Der erste Versuch mit dem damaligen fünfsekündigen HTTP-Testtimeout scheiterte beim Login, nachdem die Archivprüfungen bereits bestanden waren; er bleibt als fehlgeschlagener Nachweis erhalten. Nur der Testclient erhielt einen begrenzten 30-Sekunden-Timeout.

Lokale Nachweise: `backups/pr4-legacy-compatibility-v2/runtime/restore-status.json`, `backups/pr4-legacy-restore-v2.txt`; ursprüngliche PR3-Abnahmen nicht überschrieben. Neuere RC-Builds benötigen ihren eigenen abschliessenden Restore; der obige Nachweis wird nicht auf andere Digests umetikettiert.

Staging: HTTPS-Endpunktprobe und Browserprobe bestanden; Browser `page_errors=0`, `csp_errors=0`. Unvertrauenswürdige CA abgelehnt, bestehendes separates CA-Zertifikat für TLS-Prüfung verwendet. Der Browser verwendet einen temporären Leaf-SPKI-Pin, keinen nachgewiesenen Windows-/Android-OS-Trust. Scheduler-, Worker-, MinIO-, PostgreSQL-, Valkey-Ausfall und API-Neustart mit erneuter Readiness/Golden-Bewertung bestanden. Nachweise: `backups/pr4-staging-endpoint.txt`, `backups/pr4-staging-browser.txt`, `backups/pr4-staging-recovery.json`.

## MLflow-Betriebsumfang

Der erste gehärtete Start erzeugte zusätzlich zum Trackingserver mehrere Huey-Jobprozesse. Die installierte Runtime und die [offizielle Variablendokumentation](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.environment_variables.html) bestätigen die standardmässig aktivierte Server-Jobausführung. Private-IIP trainiert bereits im Celery-ML-Worker und benötigt diese separate Ausführung nicht. `MLFLOW_SERVER_ENABLE_JOB_EXECUTION=false`, periodische Serverjobs und Custom-Scorer-Ausführung sind deshalb explizit deaktiviert. Der neue Server wird gesund. `ops/probe_mlflow_tracking.py` besteht Metadatenanlage, unauthentifizierte Ablehnung (401), authentifiziertes Schreiben/Lesen eines synthetischen S3-Artefakts und exakten Hashvergleich. Nachweis: `backups/pr4-mlflow-tracking-probe-v3.txt`, Run `81eb5773e6e6409ea980a0b671f8c684`, SHA-256 `ff65f3640ddfdc4e509f4136d1b4c02c8225cbaea6e23f07d40839ca8715684b`.

Zwei Harnesskorrekturen sind sichtbar erhalten: `127.0.0.1` war nicht Teil der vorhandenen MLflow-Host-Allowlist und wurde erwartungsgemäss abgelehnt; der Test verwendet jetzt den bereits erlaubten Host `localhost`. Der presignierte HTTPS-Download benötigt auch beim Testclient explizites Vertrauen in die bestehende private CA. Dafür wird ein temporäres Bundle aus öffentlichen Roots und Staging-CA verwendet, ohne TLS-Prüfung abzuschalten. Private-IIP selbst verwendet für seine Trackingintegration die vorhandenen REST-Aufrufe und für seine Originalartefakte den bestehenden Minio-Adapter; es wurde kein neuer Produktions-Downloadpfad eingeführt.

## Abschlussregression

Auf dem neuen Python-/Trixie-Backend: **264 Tests bestanden**, 397,40 s, ein bestehender Starlette-Deprecation-Hinweis. Ruff bestanden; 285 Backenddateien bereits formatiert; Mypy ohne Fehler in 197 App-Dateien. Frische Migration auf `0019_validation`, 76 erforderliche Tabellen bestanden. Frontend lint/typecheck/Standalone-Build auf Node 24.22 bestanden. **21 Browserfälle bestanden**, ein Worker, 2,1 Minuten, keine übersprungenen Fälle; **30 Host-/Security-Vertragstests bestanden**, einschließlich der bisherigen zwölf Betriebsgoldens. Lokale Nachweise: `backups/pr4-final-backend.txt`, `backups/pr4-final-browser.txt`, `backups/pr4-host-final-v9.txt` und `backups/pr4-final-frontend-*.txt`. Die numerischen/Assistant-/MLflow-/Frontend-Locks sowie die 212 nummerierten Master-Hauptabschnitte bleiben unverändert.

Die Backend-Gesamtregression lief gegen die lokale PostgreSQL-17.11-Baseline; die gepatchten PostgreSQL-Imagebytes wurden separat im Produktions-Staging und isolierten Dump-/Restore geprüft. Diese unterschiedlichen Prüfaufbauten werden nicht als identisch ausgegeben. Kein neuer Remote-CI-Lauf wurde gestartet.

Der [beobachtete Runtimebestand](security/PR4_RUNTIME_INVENTORY.json) bindet 14 Rollen an die zehn gescannten Images: 13 laufende Dienste gesund, CA-Export erfolgreich beendet. API/Worker/Scheduler/ML-Worker/MLflow UID 10001, Web 1000, PostgreSQL 999, Grafana 472, Prometheus 65534. Caddy, MinIO und Ollama behalten ihre dokumentierten Root-Ausnahmen; kein ungeprüfter UID-Override. Root-Dateisysteme von Caddy, Web, Backenddiensten, MLflow, Ollama, Prometheus und Grafana sind read-only mit expliziten Schreibmounts/tmpfs. PostgreSQL, MinIO und Backup benötigen ihre geprüften Volume-/Initialisierungspfade. Keine privilegierten Container, Hostnetzwerke oder Docker-Socket-Mounts. Hostports sind ausschließlich Loopback; die spätere VPN-/Firewall-Abnahme bleibt offen.

Die finalen HTTPS-/Browserproben (`backups/pr4-final-stage-endpoint.txt`, `backups/pr4-final-stage-browser.txt`) bestehen Auth, CSRF, sichere Cookies, Golden, Monitoring und gesperrte interne Metriken ohne CSP-/Seitenfehler. Prometheus/Grafana wurden auch nach read-only/cap-drop gesund beobachtet. MLflow- und Ollama-Ausfälle halten Portfolio/Instrumentzugriff verfügbar; ohne Ollama wird `LLM_UNAVAILABLE` angezeigt. [Faultnachweis](security/PR4_FAULT_EVIDENCE.json). Das Staging-Ollama-Volume enthält keine Modellgewichte: kein Modell- oder GPU-Kompatibilitätsnachweis daraus.

Endscan: zehn Images und zehn formal gültige originale SBOMs, Trivy 0.76.0, DB vom 20.10.2026. [Remediation-Matrix](security/PR4_REMEDIATION_MATRIX.md), [SBOM-Inventar](security/PR4_SBOM_INVENTORY.md). Die erste abschließende Ollama-Exportzeitüberschreitung bleibt separat erhalten; der erfolgreiche Full-Image-Registry-Lauf ist digest-/plattform-/configgebunden. Die native Library-Abdeckung bleibt unvollständig.

## Offene Grenzen

- Vier Critical-Paketbefunde im PostgreSQL-Image und neun im unveränderten MinIO-Image bleiben ohne genehmigte Behandlung Release-Blocker. Weitere High-Befunde und manuelle/native Reviews bleiben offen; keine automatische Exception.
- Numerische, Assistant-, MLflow- und Frontend-Locks unverändert; historische Manifeste und Artefakte werden nicht angepasst.
- MinIO bleibt ein Release-Blocker; [S3-Entscheid und tatsächliche SDK-Prüfung](operations/S3_COMPATIBILITY_REVIEW.md).
- CSP enthält weiter die dokumentierte `unsafe-inline`-Einschränkung. [Next.js](https://nextjs.org/docs/app/guides/content-security-policy) verlangt für Nonces dynamisches Rendering; experimentelles SRI ist keine pauschale Ersatzfreigabe. Keine ungeprüfte Policyänderung, die Hydration beschädigt. Umstellung und XSS-Restbewertung bleiben offen.
- Kein PostgreSQL-Majorwechsel, keine automatische S3-Migration, kein Zielhost-/VPN-/Client-Trustnachweis und keine Finanzfreigabe.
