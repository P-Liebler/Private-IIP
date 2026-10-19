# PR3A – Deployment und Sicherheit

Stand 19.10.2026. Ausgangspunkt `c8457351786d2023b5d4426751a33e46f62961f4`, sauber und identisch mit origin/main. PR2-CI 39214727791 tatsächlich completed/success, Job 117935826123 erfolgreich. Änderungen dieses Auftrags sind lokal, ohne Push/Release.

**IMPLEMENTED / LOCALLY_TESTED; SECURITY_REVIEW_BLOCKED. TARGET_HOST_VERIFIED=false, OPERATOR_ACCEPTED=false.** Der Nutzer hat ausdrücklich bestätigt: kein Zielhost verfügbar, lokal vorbereiten. Keine echte Firewall-, DNS-, Task-Scheduler-, Schlüsselrotations- oder Hostneustartaktion.

## Umsetzung

`ops/preflight.py`: offline nutzbare Standardbibliothek, keine Secretwerte in Ergebnissen, Pflichtfelder/Platzhalter/Fernetformat/verschiedene zufällige Zugangsdaten, sichere Origins/Cookies/MinIO-TLS, verbotener Testmodus/Debug/Automatik, Staging-/Produktionsprojektgrenze, absolute Backupwurzel, Platz/Zugriff, Engine >=28/Compose >=2.24, CPU/RAM und gerenderte Hostports/Privilegien/Socket-Mounts. Umgebungswerte überschreiben nicht unbemerkt die geprüfte Datei. Nicht automatisierbare reale Nachweise bleiben ausdrücklich offen.

Backend validiert sichere Settings jetzt auch in Staging und lehnt kurze/Platzhalter-Produktionscredentials ab. Normale Nutzer erhalten keine Systemadministration; separate OPERATIONS_OPERATOR_USERNAMES-Allowlist. Kein neues Authverfahren, keine Änderung numerischer Modell-/Assistant-Locks oder alter Artefakte. Restore-Fixture-Erzeugung ist in Production ausdrücklich gesperrt.

Der vorhandene Authvertrag vertraut clientseitigem X-Forwarded-For nicht. Hinter Caddy können IP-basierte Limits deshalb mehrere private Clients gemeinsam betreffen; Username-Limits bleiben getrennt und Ausfälle sperren weiterhin. Eine spätere Zielkonfiguration darf Proxyvertrauen nur auf nachweislich kontrollierte Hops begrenzen, niemals beliebige Forwarded-Header übernehmen. Kein ungetesteter Auth-/Proxy-Bypass wurde ergänzt.

Produktions-API/Web/Worker/Beat: non-root aus bestehenden Images, alle Capabilities entfernt, readonly Rootfilesystem und temporäres `/tmp`. Begrenzte Docker-Logs, no-new-privileges für langlebige Dienste; keine privileged Container/Hostnetz-/Docker-Socket-Mounts. PostgreSQL/MinIO/Caddy starten nach ihren bestehenden Imageverträgen teils als root; notwendige Initialisierung und persistente Schreibverzeichnisse wurden nicht durch ungetestete User-Overrides beschädigt. Daten-/CA-/Monitoringvolumes bleiben schreibbar, Konfig-/Trustmounts readonly. Optionales MLflow läuft weiter nach vorhandenem Imagevertrag; Root/Env-Secrets sind dokumentierte Restrisiken.

Caddy ergänzt Permissions-Policy und eine mit Next kompatible CSP mit bewusst verbleibendem unsafe-inline. CA-Export ist zeitlich begrenzt. Update 2.11.4 → 2.11.7 ist mit Registry-Digest gepinnt und in lokalem Staging gestartet; persistierte CA wurde erhalten. Normale TLS-Ketten-/Hostnameprüfung bleibt aktiv, kein verify=False. Der Endpunkt-Test meldet ausdrücklich keine Ziel-/Operatorfreigabe.

## Lokale Nachweise

- Baseline 257 Backendtests; vollständiger neuer Lauf **264 bestanden** in 506,61 Sekunden, bekannte Starlette-Deprecation-Warnung.
- Elf Offline-Betriebsgoldens: fehlende/Platzhaltercredentials, falsche Domain/Origins/Schlüssel, offene VPN-Bindings, unsichere Cookies, fremde Portbindung, Docker-Socket, Umgebungsisolation, konkurrierende Sicherung/Restore, Fehlersichtbarkeit und Hashfehler vor Docker.
- Ruff, Format (285 Dateien), Mypy (197 App-Dateien), Alembic ohne Drift und frische Migration **0019_validation / 76 Tabellen** bestanden. Keine Schemaänderung.
- Lokaler Staging-Stack mit eigenem Projekt, Volumes, DB, Secrets und Backupwurzel gesund. HTTPS-Probe: Kette/Hostname, Header, Cookie, Login, Golden CHF 10'180, öffentliche Metrics 404, Prometheus-Scrape/Grafana bestanden.
- Lokales Beispiel-Env scheitert am Preflight erwartungsgemäß. Ein localhost-Testname erfüllt keine private Zielhostkonfiguration.

Browserabschluss: **21 bestanden**, einschließlich aller 20 bisherigen Fälle und neuem Operatorstatus-Golden. Elf Offline-Betriebsgoldens wurden um einen Test zur Redaktion von Authheaders ergänzt: **zwölf bestanden**. Playwright-Fehlerberichte können Sessioncookies enthalten; `ops/redact_test_artifacts.py` entfernt Authheaders und Fixturepasswörter vor Ausgabe in CI. Lokale Fehlberichte wurden ebenfalls bereinigt. Die eigentlichen Auth-/Finanzgates wurden nicht verändert.

API-Zugriffslogs laufen nach Prüfung des tatsächlichen Outputs jetzt ebenfalls durch den JSON-Rootformatter; Celery überschreibt den Formatter nicht mehr. Neue gestartete lokale API-Prozesse geben nachweislich JSON mit UTC-Zeit aus. Weitere Recovery-Ergebnisse stehen im [Gesamtbericht](PR3_ACCEPTANCE_REPORT.md).

## Sicherheitsreview: keine Produktionsfreigabe

Python Core+Assistant sowie separater MLflow-Lock mit pip-audit 2.10.1 tatsächlich geprüft: keine bekannten Meldungen. npm audit --omit=dev: null Meldungen. Das ist keine Aussage über OS-/Go-Pakete der Images. Die Modellpins wurden nicht geändert.

Trivy 0.70.0 mit aktueller Datenbank hat nach dokumentierten Mirror-/Timeoutfehlern verwertbare Imagebefunde geliefert. Nicht abgeschlossene Scans gelten nicht als null Befunde. Maschinenlesbare vollständige Befunde und Versions-/Digestbezüge werden im Sicherheitsinventar zusammengefasst.

| Geprüfter Stand | High/Critical-Paketbefunde | Behandlung |
| --- | --- | --- |
| Caddy 2.11.4 | 22 / 0 | Auf 2.11.7 mit Digest aktualisiert |
| Caddy 2.11.7 | 4 / 0 | Verbleibende Go/x-net-DoS-Meldungen offen, kein grüner Security-Gate |
| Valkey 8.1.10-alpine | 0 / 0 | Kein bekannter High/Critical-Befund im konkreten Scan; keine Sicherheitsgarantie |
| MinIO RELEASE.2025-10-15T17-29-55Z | 121 / 9 | S3-/Go-/Imagebefunde; Upstream archiviert, Wartungs-/Patchentscheidung erforderlich |
| pgvector 0.8.6-pg17-bookworm | 115 / 16 | OS-/Runtimebefunde prüfen und gepatchtes Image abnehmen |
| Prometheus v3.6.0 | 102 / 4 | Nur adminlokal, dennoch Update/Neuscan erforderlich |
| Lokales Backendimage | 91 / 9 | OS-/Pythonbasis separat von auditfreien Python-Pins; Runtime-/Imageupdate reviewen |
| Grafana 12.3.4 | 146 / 6 | Nur authentifiziert adminlokal; Plugin-/Runtime-/OS-Pfade vor Freigabe prüfen |
| Next-Produktionsimage | 45 / 3 | Node-/Basisimage-Befunde trotz auditfreier npm-Produktionsdependencies |
| MLflow-Image | 91 / 9 | Optional, intern und authentifiziert; Basisimage-Befunde offen |
| Ollama 0.40.4, Go-Binary + OS-Paketmanifest | 48 / 0 | Begrenzter Scan, keine vollständige CUDA-/Libraryabdeckung; kein vollständiger Image-Pass |

Vollständige CVE-/Paket-/Versions-/Fix-/Schwere-/URL-Liste ohne Image-Env/Secrets: [maschinenlesbares Inventar](security/PR3_IMAGE_AUDIT.json), reproduzierbar mit `ops/summarize_security_audit.py`. Erfasst sind die exakten gescannten Artefakte/Digests, nicht automatisch jeder spätere Code-Layer-Rebuild. Nur HIGH/CRITICAL wurden in den Image-Scans angefordert; niedrigere Schweregrade sind damit nicht als fehlend nachgewiesen. Vollständige Ollama-Imageversuche liefen in Timeouts; der begrenzte Folgescan ist entsprechend gekennzeichnet. Kein Exploit wurde ausgeführt und kein nicht erreichbarer Codepfad ohne Beleg als sicher verworfen.

Counts sind Paketbefunde, keine Anzahl bewiesener ausnutzbarer App-Endpunkte. MinIO und PostgreSQL sind nicht hostveröffentlicht, Prometheus nur localhost; das verringert Exposition, heilt aber keine Schwachstelle. Für Caddy sind TLS-/HTTP-DoS-Pfade relevant, weil es der Ingress ist. Keine blanket-Risikoakzeptanz ohne Operator.

Primärprüfung 19.10.2026: [Caddy-Releases](https://github.com/caddyserver/caddy/releases/tag/v2.11.7), [Caddy-Advisories](https://github.com/caddyserver/caddy/security/advisories), [Go TLS CVE-2026-97031](https://pkg.go.dev/vuln/GO-2026-6607), [MinIO-Advisories und Archivstatus](https://github.com/minio/minio/security/advisories), [Docker-Portgrenzen](https://docs.docker.com/engine/network/port-publishing/). CVE-2026-97031 betrifft Go-TLS vor 1.26.9 beziehungsweise 1.27.2; das gescannte Caddy 2.11.7 enthält Go 1.26.8. Keine Behauptung, dass ein bloßes Tagupdate alle Befunde behebt. MinIO nennt seit April 2026 u. a. nicht authentifizierte Object-Writes; es wurde kein Exploit gegen die Anwendung ausgeführt.

## Offene Operator-/Releasegates

Imagebefunde beheben oder konkret nach Funktion/Exposition und Verantwortlichem bewerten; kein stiller Stackwechsel, keine nachträgliche Änderung alter numerischer Artefakte. Echten Host/VPN/DNS, Windows-/Android-CA-Vertrauen, geschützte Env-ACL, unabhängiges verschlüsseltes Backup, Tagesjob, vollständige Secret-/CA-Recovery und Alarmzustellung prüfen. **PRIVATE_CORE_DEPLOYMENT_NOT_VERIFIED.**
