# PR4A – Sicherheitsbewertung

Prüfdatum: 19.–20.10.2026. **PR4A ASSESSMENT COMPLETE; SECURITY_BLOCKED.** Die Bestandsaufnahme ist abgeschlossen. PR4B und PR4C benötigen zusätzlich die Abnahme des geänderten Imagebestands; dies ist keine Release-Freigabe.

## Ausgangspunkt und CI

HEAD und origin/main: `581a13c415d20ff8594d5ecf97b98226b8b5c74e`; zu Beginn sauber. GitHub-Workflow `39242444587`, Job `118026254378`: tatsächlich **completed/failure**. Backend 264 bestanden, Frontend bestanden, Browser 20 bestanden / ein Fehler. Der Systemstatus-Assert traf neben dem fachlichen Fehlerhinweis den Next-Routenannouncer mit ebenfalls `role=alert`. Der Test filtert jetzt auf den konkreten Operations-Fehler. Lokale Nachprüfung für Nichtoperatoren: ein Browserfall bestanden (9,6 s). Neue Remote-CI wurde nicht gestartet; kein Push.

Erneute lokale Backend-Baseline: **264 passed**, 436,99 s; vorhandener Starlette-Deprecation-Hinweis. Frontend-Lint, Typecheck und neuer Standalone-Build bestanden. Die vollständigen lokalen Browserläufe bestanden zunächst 18/21 beziehungsweise 19/21 Fälle unter starker Ressourcenlast. Die tatsächlichen Wartebedingungen für Login, Dataset-Refetch und Forward-Readiness wurden präzisiert; eine vollständige grüne Abschlussregression ist separat erforderlich. Die CI-Redaktion ignorierte trotz expliziter Übergabe die Endung `.log`; dies ist korrigiert und über den echten Dateieinstieg mit synthetischen Zugangsdaten getestet. Security-Vertragstests wurden ergänzt; der aktuelle Testumfang steht im PR4-Abnahmebericht.

## Auditvertrag und aktueller Umfang

Trivy **0.76.0**, offizielles unveränderliches Release vom 14.10.2026; Windows-Archiv gegen veröffentlichte SHA-256-Liste geprüft. Executable-SHA-256: `51e50a34f8739424bc88282602d10945b25249ffdb51703fe3c9453c20217c42`. Vulnerability-DB: Schema 2, UpdatedAt `2026-10-19T07:19:54.308593453Z`. Alle Schweregrade werden erfasst. Export der vollständigen lokalen Images, ohne Docker-Socket-Mount in einen Scanner. Konfigurations-/Secret-Umgebungen werden nicht in die öffentliche Auswertung übernommen.

Docker/containerd-Manifestdigest und Trivy-Configdigest sind getrennte Identitäten. Der Export verbindet sie über `manifest.json` und die verifizierten Config-Bytes. Archivhash, Configdigest und Registry-/Imagebezug werden getrennt erfasst. Ein bloßer Tag oder ein früherer Scan gelten nicht für einen neuen Build.

Die ersten Auditversuche sind erhalten: zunächst fehlende Unterscheidung von Manifest-/Configdigest, danach Ablehnung des von Trivy erzeugten CycloneDX-Formats 1.7 durch den lokalen Validator. Dieser unterstützt nun 1.7. Die vollständigen Scan-/SBOM-Dateien aller zehn Bestandsimages wurden erneut validiert, ursprüngliche Fehlerrecords nicht überschrieben. Alle zehn SBOMs bestehen zusätzlich die offizielle, lokal vendorte CycloneDX-1.7-JSON-Schema-Prüfung. SBOMs werden bytegenau kopiert; eine zwischenzeitliche Reserialisierung mit ungültigem Hashbezug wurde verworfen und bleibt als Fehlversuch erhalten. Tatsächliche Prozess-/Netz-/Analysefehler bleiben SCAN_INCOMPLETE und benötigen neue Läufe.

## Vollständiger Bestandsaudit

Maschinenlesbare Digests, Paketversionen, CVEs und Fixangaben: [Inventar](security/pr4-baseline/inventory.json), [formale SBOM-Prüfung](security/pr4-baseline/sbom-validation.json). HIGH/CRITICAL sind Paketbefunde, keine bewiesenen Exploits. Der DB-Stand entspricht dem geprüften PR3-Stand; für die geänderten Images wurde am 20.10. eine neue DB mit `UpdatedAt=2026-10-20T07:17:35.368599961Z` separat heruntergeladen.

| Komponente | HIGH | CRITICAL | Vergleich mit PR3 |
|---|---:|---:|---|
| Caddy | 4 | 0 | Gleich |
| PostgreSQL/pgvector | 115 | 16 | Gleich |
| Valkey | 0 | 0 | Gleich; andere Schweregrade bleiben erfasst |
| MinIO | 121 | 9 | Gleich |
| Backend | 91 | 9 | Gleich |
| Web | 45 | 3 | Gleich |
| Prometheus | 102 | 4 | Gleich |
| Grafana | 146 | 6 | Gleich |
| MLflow | 91 | 9 | Gleich |
| Ollama | 48 | 0 | Jetzt vollständiger Image-Paketlauf statt nur Teilscan |

Die Ollama-SBOM beweist keine lückenlose Schwachstellenzuordnung beliebiger CUDA-/cuDNN-/GGML-/MLX-Binaries. Die nativen Dateiversionen und Hashes wurden ergänzend in `backups/pr4-ollama-native-library-hashes.txt` erfasst; der manuelle Abdeckungsreview bleibt offen. Fehlende Paketbefunde werden nicht als Sicherheitsfreigabe ausgelegt.

## Exposure und Priorisierung

Caddy ist der vorgesehene private HTTPS-Einstieg und verarbeitet unzuverlässige HTTP-/TLS-Eingaben. API und Web empfangen darüber authentifizierte und nicht authentifizierte Anfragen. PostgreSQL, Valkey, S3, MLflow und Ollama erhalten keine Hostports in der Produktionsdefinition. Prometheus und Grafana sind ausschliesslich an Loopback gebunden. Diese Konfigurationsprüfung ersetzt keinen echten VPN-/Firewall-Test; ein kompromittierter interner Dienst bleibt ein relevantes Angriffsszenario.

MinIO und PostgreSQL enthalten Critical-Befunde und bleiben priorisierte Blocker. Ein fehlender Herstellerpatch ist keine Ausnahme. Numerische Runtime-Locks dürfen zur Reduktion von Paketbefunden nicht ungeprüft verändert werden. Die geänderten Kandidaten werden anhand ihrer tatsächlichen Digests, SBOMs und der archivierten P6/P7-Verträge überprüft.

## Priorisierte Maßnahmen

1. Caddy: gleicher Anwendungsstand 2.11.7, isolierter Build mit Go 1.27.2 und x/net 0.60.0; erst nach Scan, Modulliste, TLS-/Auth-/CSP-/MinIO- und Recovery-Probe übernehmen.
2. PostgreSQL/pgvector: Major 17 erhalten, konkrete OS-Patches und Stand 17.11 prüfen; Dump/Restore/Trigger/Decimal/JSONB/vector vor Übernahme. Kein Start eines anderen Major auf vorhandenen Volumes.
3. MinIO: archivierter Upstream und offene S3-/Go-Befunde bleiben Blocker. Kostenlose S3-Kandidaten separat anhand tatsächlicher SDK-Aufrufe prüfen; keine automatische Datenmigration.
4. Python 3.12.15 und Node 24.22.0 LTS als isolierte Kandidaten bauen. Alle numerischen/Assistant-Locks und alte Artefakte bleiben unverändert. Erst Laufzeit-/Modell-/Frontend-/Restore-Abnahme, dann Standardpin ändern.
5. Prometheus/Grafana und optionale MLflow-/Ollama-Images mit vollständigen Scans prüfen; private Netzgrenze ersetzt keinen Patch.

## Primärquellen, geprüft am 19.10.2026

- [Trivy Release 0.76.0](https://github.com/aquasecurity/trivy/releases/tag/v0.76.0)
- [Caddy 2.11.7](https://github.com/caddyserver/caddy/releases/tag/v2.11.7), [Modulvertrag](https://github.com/caddyserver/caddy/blob/v2.11.7/go.mod), [Go TLS Advisory](https://pkg.go.dev/vuln/GO-2026-6607), [offizielle Go-Releases](https://go.dev/dl/)
- [Python 3.12.15](https://www.python.org/downloads/release/python-31215/), [offizieller Image-Build](https://github.com/docker-library/python/blob/master/3.12/slim-bookworm/Dockerfile)
- [Node 24.22.0 LTS](https://nodejs.org/en/blog/release/v24.22.0)
- [PostgreSQL Security](https://www.postgresql.org/support/security/)
- [MinIO-Archivstatus](https://github.com/minio/minio), [Advisories](https://github.com/minio/minio/security/advisories), [Community-Imageherkunft](https://github.com/coollabsio/minio)
- [Prometheus 3.15.0](https://github.com/prometheus/prometheus/releases/tag/v3.15.0), [Grafana Security](https://grafana.com/security/security-advisories/)
- [SeaweedFS S3-Vertrag](https://github.com/seaweedfs/seaweedfs/wiki/Amazon-S3-API), [Garage S3-Vertrag](https://garagehq.deuxfleurs.fr/documentation/reference-manual/s3-compatibility/)

Keine Ausnahme genehmigt, kein Exploit ausgeführt. TARGET_HOST_NOT_VERIFIED, REAL_DATA_LIMITED, FORECASTS_SHADOW_ONLY und RECOMMENDATIONS_GATED bleiben bestehen. Die S3-Kandidatenprüfung und Entscheidung sind im [Kompatibilitätsreview](operations/S3_COMPATIBILITY_REVIEW.md) dokumentiert.
