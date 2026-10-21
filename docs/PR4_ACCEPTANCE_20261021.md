# PR4 – erneute lokale Abnahme vom 21.10.2026

**Lokaler Kandidat geprüft; SECURITY_BLOCKED. Keine Produktionsfreigabe.** Dieser Nachweis ergänzt die Abnahme vom 20.10. Die damaligen JSON-Dateien und das alte RC-Manifest bleiben unverändert. Aktueller Kandidat: [PR4-LOCAL-20261021-01](releases/PR4_LOCAL_20261021_01.json).

## Getrennte Abschlusszustände

| Bereich | Ergebnis |
|---|---|
| PR3_CI_FIXED | FIXED LOCALLY; REMOTE_SUCCESS_NOT_VERIFIED |
| PR4_TECHNICAL_IMPLEMENTATION | Implementiert und lokal getestet; Sicherheitsmigrationen separat offen |
| SECURITY_REMEDIATION_STATUS | PARTIAL / SECURITY_BLOCKED; 13 Critical- und 366 High-Paketbefunde |
| SECURITY_REVIEW_STATUS | SECURITY_REVIEW_REQUIRED; keine genehmigten Ausnahmen |
| RELEASE_CANDIDATE_STATUS | RC_TESTED / RC_SECURITY_BLOCKED / RC_OPERATOR_REVIEW_REQUIRED |
| TARGET_HOST_STATUS | TARGET_HOST_NOT_VERIFIED; laut Nutzer nicht verfügbar |
| REAL_DATA_STATUS | REAL_DATA_LIMITED; keine Quellenfreigabe |
| P7_MODEL_STATUS | FORECASTS_SHADOW_ONLY; keine reale Prognosefreigabe |
| P9_STRATEGY_STATUS | RECOMMENDATIONS_GATED; keine Promotion |

## PR4-0: tatsächliche CI und unabhängige Regression

HEAD und nach Fetch `origin/main`: `8004ea39eeeb5628bf90cef9c86567a2d3af33ff`. Bereits vorhandene PR4-Arbeiten übernommen. Der tatsächliche GitHub-Run `39242444587`, Job `118026254378`, wurde erneut als completed/failure überprüft: Backend 264, Frontend und Fixturevorbereitung bestanden; Browser 20/21. Die mehrdeutige Alert-Abfrage traf Operationsfehler und Next-Routenansager. Der bereits vorhandene konkrete Textfilter bleibt erhalten; kein Berechtigungs-/403-Vertrag geändert. [Detaillierter CI-Nachweis](PR4_0_CI_RECOVERY_REPORT.md).

Zusätzlich Dataset-Status konkret gefiltert, Recommendation-Aktion an das tatsächlich neu erzeugte Ergebnis samt GET-ID gebunden und Portfolioanzeige nach bestätigtem POST/201 abgewartet. Keine Finanzassertion entfernt. CI-Fehlerlogs werden vor Ausgabe redigiert. Ein anfänglicher 20/21-Lauf mit zu kurzer Portfolioanzeige-Wartezeit sowie ein fehlerhafter zusätzlicher UI-ID-Assert bleiben als Fehlversuche erhalten. Abschließend sechs fokussierte Fälle und alle 21 Browserfälle bestanden. Keine neue Remote-CI als erfolgreich ausgewiesen; kein Push.

| Prüfung | Neues Ergebnis am 21.10. |
|---|---|
| Backend | **266 bestanden**, 160,55 s; zwei neue Guards für fehlende Modellbytes und inkompatiblen Lock; bestehender Starlette-Hinweis |
| Ruff / Format / Mypy | Bestanden; 286 Dateien formatiert, 197 App-Dateien ohne Typfehler |
| Browser | Betroffener Systemstatusfall bestanden, sechs fokussierte Fälle bestanden; **21 bestanden**, 2,5 min, keine Skips |
| Frontend | Lint, Typecheck und abgeschlossener Standalone-Build auf Node 24.22 bestanden; finale E2E-Änderungen separat nachgeprüft |
| Host / Security | **32 bestanden**; neue Tests verhindern Veröffentlichung manipulierter Originale/anderer Scanner-DB/unvollständiger Scans |
| Schema | Frisch **0019_validation / 76 erforderliche Tabellen** |
| Python-Audit | Core/Assistant Exit 1: neuer certifi-Befund bleibt offen; gepatchter separater MLflow-Lock Exit 0 |
| npm-Produktion | Exit 0; kein bekannter Befund im Lauf |
| Image / SBOM | Zehn exakte Images gescannt; zehn unveränderte originale CycloneDX-SBOMs formal und per Hash gültig |

Tests verwenden ausschließlich lokale Services beziehungsweise ausdrücklich synthetische Fixtures. Backendintegration und Browser-Datasetaufbau liefen nacheinander. Technischer Erfolg begründet keine finanzielle Validierung.

## PR4A: aktuelles Sicherheitsinventar

[Inventar](security/pr4-20261021/inventory-final.json), [Vergleich](security/pr4-20261021/vulnerability-report-final.json), [SBOM-Prüfung](security/pr4-20261021/sbom-validation-final.json), [beobachtete Runtime](security/pr4-20261021/runtime-inventory-final.json). Trivy 0.76.0, ausführbare Datei SHA-256 `51e50a34f8739424bc88282602d10945b25249ffdb51703fe3c9453c20217c42`; DB UpdatedAt `2026-10-21T01:19:53.032404989Z`. Image-/Configdigests bleiben getrennt. Nicht abgeschlossene Scans werden nicht in Nullbefunde umgedeutet. Der Publisher prüft nun zusätzlich ursprüngliche Scan-/SBOM-Hashes und den ursprünglichen DB-Vertrag.

| Komponente | High | Critical |
|---|---:|---:|
| Caddy | 0 | 0 |
| PostgreSQL/pgvector | 93 | 3 |
| Valkey | 0 | 0 |
| MinIO | 123 | 9 |
| Backend | 44 | 1 |
| Web | 0 | 0 |
| Prometheus | 8 | 0 |
| Grafana | 5 | 0 |
| MLflow | 44 | 0 |
| Ollama | 49 | 0 |

Paketbefunde sind keine bewiesenen erreichbaren Exploits. Sie bleiben ohne konkreten Review offen. [Critical-Triage](security/pr4-20261021/critical-triage.json) bindet alle 13 Befunde an konkrete Pakete, Pfade, Fixangaben, Digests und verbleibende Entscheidungen. [Buildherkunft](security/pr4-20261021/build-provenance.json) hält deklarierte Basisimages, Builddefinitionen und beobachtete Betriebssysteme fest; keine signierte Buildattestation behauptet. Arbiträre CUDA-/cuDNN-/GGML-/MLX-Binaries sind durch unterstützte Paketanalysatoren nicht lückenlos abgedeckt: **SCAN_INCOMPLETE_MANUAL_REVIEW**. Keine pauschale Ignore-Liste. Die Vergleichsdatei umfasst auch Änderungen der Advisory-DB; verschwundene CVEs allein beweisen keinen Patch.

## PR4B: konkret geänderte Kandidaten

- PostgreSQL `pr4-rc2`: gleiche Majorversion 17.11 und pgvector 0.8.6; aktualisierte Bookworm-Pakete, unbenötigtes libsqlite3 nach Abhängigkeits-/Entrypointprüfung entfernt. Kein blindes Autoremove. gpgv/Keyrings bleiben erhalten. Gleichzeitiger DB-Vergleich: 95 High/4 Critical vorher, 93/3 nachher. Bestehendes Schema und Archive im neuen isolierten Restore geprüft. Default-Kandidat im Produktions-Compose aktualisiert; keine Zielhostmigration.
- Backend `pr4-rc3`: Python 3.12.15/Trixie mit unveränderten Core-/Assistant-Pins. Neue negative Artefaktprüfungen, kein Gate abgeschwächt. Der neue certifi-Critical bleibt ein Releaseblocker.
- MLflow `pr4-rc4`: ausschließlich separater Lock `certifi 2026.10.19`, `Pillow 13.0.0`; MLflow 3.17.1, Python 3.12.15 und numerische Pins erhalten. pip check und separater Dependency-Audit bestanden. Gleicher DB-Stand: vorher 50 High/2 Critical, jetzt 44/0. Tatsächlicher authentifizierter Tracking-/S3-TLS-Roundtrip mit Text- und synthetischem RGB-Bildartefakt bestanden; nicht authentifizierte Metadaten bleiben 401, Jobs/Custom Scorer bleiben deaktiviert. Erster Probeversuch während Kaltstart fehlgeschlagen und separat erhalten.
- Übrige Digests bleiben erhalten und wurden mit neuer DB erneut gescannt. Caddy/CA, Secure-Cookies, blockierte interne Metriken und private Netzgrenzen nicht gelockert. CSP-Browserprobe meldet keine CSP-/Seitenfehler; die vorhandene Inline-Ausnahme bleibt ein offener Reviewpunkt. Temporärer Browser-SPKI-Pin ist kein Client-OS-Trustnachweis.

### Aktuelle Primärquellenprüfung (21.10.2026)

[certifi-Advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2) und [Fixrelease](https://github.com/certifi/python-certifi/releases/tag/2026.10.19): kompromittierte Zwischen-CA-Schlüssel, Critical, Fix verfügbar. Der gesamte Core-Lock gehört zum Modellvertrag. Ein stiller Paketwechsel würde alte Artefakte sperren oder den Vertrag vortäuschen. [Getrennter Kompatibilitätsweg](operations/MODEL_RUNTIME_COMPATIBILITY.md) vorbereitet, Runtime-/Legacy-Routing noch nicht implementiert oder freigegeben; keine Ausnahme erteilt.

[Pillow-Advisory](https://github.com/python-pillow/Pillow/security/advisories/GHSA-8g5g-8vmr-9782), [13.0-Änderungen](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html): Fix 13.0.0, Upstream High, Trivy Critical. Die tatsächliche Python-3.12-/MLflow-Bildintegration wurde geprüft; kein bloßer Versionsvergleich als Kompatibilitätsnachweis.

[Debian SQLite](https://security-tracker.debian.org/tracker/CVE-2025-7458) und [libxml2](https://security-tracker.debian.org/tracker/CVE-2026-6653): Entfernung unbenötigter SQLite-Runtime reduziert Befunde; libxml2, zlib und gosu/Go bleiben konkret offen. [MinIO-Upstream](https://github.com/minio/minio/releases) ist archiviert; automatisierte [Distributionsbuilds](https://github.com/coollabsio/minio) sind kein Wartungsnachweis. MinIO bleibt gesperrt. SeaweedFS-Prototypnachweise vom 20.10. gelten nur für ihren dokumentierten Umfang; [TUS-Advisory](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-99q7-x53r-6j4g) bleibt zu prüfen. [Migrationsplan](operations/OBJECT_STORAGE_MIGRATION.md) vorbereitet, **NOT_AUTHORIZED / NOT_EXECUTED**.

[Ollama 0.40.6](https://github.com/ollama/ollama/releases/tag/v0.40.6) ist verfügbar; beibehaltener geprüfter Digest ist 0.40.4. Kein belegter nativer CVE-Fix oder bestandener Inferenz-/GPU-Review aus der bloßen Releaseexistenz abgeleitet. Caddy 2.11.7, Prometheus 3.15.0 und Grafana 12.4.13 wurden gegen die offiziellen Releaseinformationen geprüft; Paketbefunde und vorhandene angepasste Buildverträge gelten weiterhin.

## PR4C: Restore, Betrieb und unveränderlicher Kandidat

Frisches konsistentes Backup `20261021T071921Z-49252`: **355 Raw-Objekte**, 3.065.303 Bytes einschließlich Dump, 26,93 s. Isolierter Restore **07:20:50–07:23:11 UTC**, Cleanup bis 07:23:21 UTC erfolgreich, 356 Dateihashes verifiziert, **CHF 10’180**. Neue PostgreSQL-/Backenddigests und exakt gescannter MinIO-Digest verwendet. P6-Hash `dd5cd6ef97b9248eb148725797470069b9b33635df15f8506d61bf99761ea538`, P7-Artefakt `9706d2dc2631d0cfde24ddaad3ccd4f41b686351cd5b82ecd5e0a96fc18f5c94`, exakter Lock sowie P8-/P9-/P10-/PR1-/PR2-Verträge unverändert gegen den neuen Checkpoint geprüft. Neue synthetische Tests ergänzen Historien; alte Historien werden nicht durch frühere Gesamtzähler ersetzt.

[Restore-Evidenz](security/pr4-20261021/restore-evidence.json), [Prüfindex](security/pr4-20261021/verification-evidence.json), [Faults](security/pr4-20261021/fault-evidence.json). Lokales Staging mit den neuen Kandidaten: HTTPS/Auth/CSRF/Cookies/Golden, Prometheus/Grafana sowie Browserhydrierung geprüft. Kontrollierte Core- und optionale Dienstausfälle werden mit ihren tatsächlichen Ergebnissen im Prüfindex ausgewiesen. Falsche DB-Zugangsdaten führen zu Readiness 503; fehlende Modelle und inkompatible Locks werden abgewiesen. Frühere Backup-Abbruch-/Checksumnachweise bleiben ausdrücklich auf den 20.10. datiert; kein behaupteter Mid-Stream-Migrationstest.

Der neue RC bindet Commit, uncommittete Quellbytes, zehn Image-/Configdigests, 15 Dienstrollen, Original-SBOM-Hashes, Locks, Schema und neue Test-/Restoreberichte. Alte Audits/RCs bleiben bytegleich erhalten. Der Deploymentprüfer verweigert den Kandidaten wegen offener Releasegates. Kein Push, Release, Zielhostrollout, S3-Wechsel, PostgreSQL-Majorwechsel, Modell-/Strategiepromotion oder Handel.

Lokaler Normalbetrieb wiederhergestellt; Test-Staging und S3-Prototyp sind gestoppt, Volumes und CA erhalten. API meldet `APP_ENV=local`, `ASSISTANT_TEST_MODE=false`, `DATA_COLLECTION_ENABLED=false` und `FORWARD_SHADOW_ENABLED=false`. Das normale Entwicklungsfrontend hat seine generierte Typdatei wiederhergestellt. MLflow verwendet den gepatchten Kandidaten; keine Modellgewichte heruntergeladen oder geändert. Alle zehn lokalen Dienste laufen, alle vorhandenen Healthchecks sind gesund; der lokale ML-Worker besitzt keinen Healthcheck.

## Verbleibende Arbeit für die sichere private Installation

1. Backend-TLS-Runtimewechsel und getrennten archivtreuen Legacy-Replayweg umsetzen und separat abnehmen; keine Modellmanifeste umschreiben.
2. MinIO-Wartungs-/Ersatzentscheidung treffen, vollständigen isolierten Migrationsnachweis inklusive unterbrochenem Transfer, Metadaten, Mirror, Restore und Rollback erbringen; produktiven Wechsel separat autorisieren.
3. PostgreSQL-Criticals sowie High-, native Ollama- und CSP-Befunde konkret bearbeiten. Jedes geänderte Image erneut scannen/testen; Ausnahmen ausschließlich digest-/CVE-genau mit Reviewer und Ablaufdatum.
4. Geprüften Stand nach Nutzerfreigabe pushen und tatsächliche grüne Remote-CI nachweisen; neuer RC muss den finalen Stand und frische Security-DB binden.
5. Echten Zielhost bereitstellen und VPN/DNS/Firewall, Ressourcen, Client-CA-Trust, unabhängiges verschlüsseltes Backup, Tagesjob, Schlüssel-/CA-Recovery, Alarmempfang, Hostneustart und Rollback nachweisen. Security-, Zielhost- und Operatorfreigaben getrennt dokumentieren; ausschließlich freigegebene Digests mit `--no-build` starten.
6. Quellenrechte, Real-Datenbereitschaft und reale Modell-/Strategievalidierung bleiben eigene spätere Freigaben. Collection und Forward Shadow bleiben standardmäßig aus.

PR4 endet mit diesem gesperrten lokalen Kandidaten. PR5 wird nicht begonnen.
