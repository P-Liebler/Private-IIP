# PR7A – CI-Recovery und aktuelle Securitybelege

27.10.2026. **SECURITY_NOT_APPROVED / REMOTE_FIX_NOT_PUSHED**.
HEAD und erneut gefetchtes origin/main:26f701edce992be60a98c75c76eaa0c914245619.

## Tatsächlicher Remotezustand und Korrektur

[Run40298779663](https://github.com/P-Liebler/Private-IIP/actions/runs/40298779663)
hatte zwei unabhängige Fehler: Verify121491249603 bestand297 Backendtests und
25/26 Browserfälle, scheiterte an fehlender Historie der frischen Chartfixture.
Security121491250106 verifizierte das Scannerbinary, scheiterte anschließend
an ECR-DB-Quota; nachfolgende Prüfungen wurden übersprungen. Das war
VULNERABILITY_DB_UNAVAILABLE, kein neuer CVE-Nachweis. Originale Joblogs bleiben privat.

`ops/prepare_vulnerability_db.py` verwendet gepinntes Trivy0.76.0, geprüften
Binaryhash, ausschließlich offizielle GHCR/ECR-Registries, je zwei begrenzte
Versuche und validierte UTC-/Schema-/bbolt-/Bytehash-/max48h-Cachebelege.
Teilantworten werden getrennt verworfen; Downloaddatum verjüngt keine DB.
Cache enthält nur drei öffentliche DB-Dateien. Actions/cache ist SHA-gepinnt;
PRs schreiben keinen neuen Cache. Beschaffung meldet nur DATABASE_READY.

Die Workflowklassifikation trennt Installations-/DB-/unvollständige Scan-/
Dependency-/Imagefehler. Alle drei Lockaudits laufen unabhängig; kein ignore,
continue-on-error oder Scanpass aus fehlenden Ergebnissen. YAML/Bash lokal
geprüft. Neue Chartfixture verwendet einen eigenen synthetischen Cashledger.
**29/29 Browserfälle ohne Skips**,306 Backend-/67 Hosttests und statische
Prüfungen bestehen. Kein neuer Remote-Pass ohne autorisierten Push behauptet.

## Exakter neuer Bestand

[Inventar](security/pr7-20261027-rc3/inventory.json) und 14 Original-SBOMs;
[formale Validierung](security/pr7-20261027-rc3/sbom-validation.json)14/14.
Am27.10. frischer GHCR-Download im ersten Versuch, DB
UpdatedAt2026-10-27T07:13:33.504287223Z. Sämtliche14 Profile neu gescannt;
kein Nachweis eines älteren Builds auf einen neuen übertragen.

| Imageprofil | Critical | High | Grenze |
| --- | ---: | ---: | --- |
| API/Worker/Scheduler/ML-Worker, jeweils Backend PR7rc6 | 0 | 44 | Dasselbe Image, keine vier verschiedenen CVE-Bestände. |
| MLflow PR7rc1,3.17.2 | 0 | 44 | OS-Befunde offen; Auth-/S3-/Bild-Roundtrip geprüft, Jobs aus. |
| Bisheriges MinIO, lokale Quelle/Legacy-Backuphelper | 9 | 125 | Kein sicher freigegebener Produktivbestand. |
| Grafana12.4.13 mit OS-Patches | 0 | 8 | Verbleibende native Go-/Modulbefunde nicht genehmigt. |
| Web PR7rc7 | 0 | 0 | Gleiche Herkunft nötig bei jedem neuen Build. |
| PostgreSQL17, Valkey, Seaweed4.51, Caddy, Prometheus, CPU-Ollama, jeweils | 0 | 0 | Keine allgemeine Freigabe aus diesen zwei Schwereklassen. |

Medium/Low/Unknown bleiben vollständig im Inventar; insbesondere Ollama hat
weitere Befunde unterhalb High. Numerische Core-Pins unverändert. Supporting-
Patches pypdf6.21.2 (drei Herstelleradvisories), MLflow3.17.2/GitPython3.2.1 und
Zod4.6.7; separate PR6-Lockarchive, strikter Parser-/Runtimeguard. Lock-/npm-
Audits nach Patch vom 26.10. ohne bekannte Befunde; keine allgemeine Garantie.

## Konkreter Review und weiterhin offene Risiken

Der [primäre Advisoryabgleich](security/PR7_UPSTREAM_ADVISORY_REVIEW.md) erfasst
25 Seaweed-Einträge und die abweichend gemeldete Image-Revision. Tatsächliche
gRPC-/PUT-/POST-/Versions-/Retentionprobes bestehen, S3-Verkehr läuft durch
eigenen CA-geprüften Gateway. Filer-/Master-/Volume-/gRPC-Ports sind nicht
hostpubliziert. Das ist keine reproduzierbare Buildattestation und kein
vollständiger Audit ungenutzter nativer Zusatzprotokolle.

Caddy wurde mit Go1.27.3 neu gebaut, Prometheus auf offiziellen Sicherheitsstand
3.15.1 gebracht. Ollama0.40.11 CPU verwendet das vollständig SHA-geprüfte
offizielle Archiv, begrenzte CPU-Extraktion und Lizenzen; keine GPU-Abnahme.
Native RAG- und Erklärungspfade sowie Modellabwesenheit funktionieren. Das
ersetzt keinen vollständigen nativen C++-Audit. Grafana ist funktional geprüft,
seine acht Highs bleiben offen. Backend-OS-Highs werden nicht durch Änderungen
numerischer Abhängigkeiten oder weggefilterte Paketlisten verdeckt.

CSP enthält weiter unsafe-inline. Browserhydration und erfolgreiches Login
sind keine Nonce- oder XSS-Freigabe. Client-CA/VPN/Firewall/Backup-/Schlüsselplan
auf einem echten Zielhost fehlen. Keine Critical-/High-Ausnahme automatisch
erteilt, keine Quelle/kein Modell promoviert und kein Release ausgeführt.

Primärlinks und Prüfdatum für Dependency-/Go-/Seaweed-/CSP-Verträge stehen im
Advisorybericht und in den Inventarzeilen. Frühe26.10.-Inventare bleiben
historische Zwischenstände. Der finale Source-/Secret-Scan wird separat auf
dem aktuellen Git-sichtbaren Bestand protokolliert; keine Treffertexte veröffentlichen.
Der27.10.-Scan meldet **NO_KNOWN_SECRET_FINDINGS /0** ohne neue Ausnahmen.
Der abschließende [sanitisierte Sourcebeleg](security/pr7-20261027-rc3/source-security-receipt.json)
bindet Scanner, privaten Originalreport und Source-Dateimanifest per SHA256.

Primärbelege für die Supporting-Patches, geprüft26.10.:
[pypdf Objektreferenzen](https://github.com/py-pdf/pypdf/security/advisories/GHSA-6c7f-9265-g8fw),
[Cross-References](https://github.com/py-pdf/pypdf/security/advisories/GHSA-jr96-gvgh-j3r4),
[xref-Grenzen](https://github.com/py-pdf/pypdf/security/advisories/GHSA-gmh7-3g9r-mjh5),
[MLflow-Patch](https://github.com/mlflow/mlflow/commit/31ff9e56f5038d61ec75344518912945f60dffec),
[MLflow3.17.2](https://github.com/mlflow/mlflow/releases/tag/v3.17.2),
[GitPython-Advisory](https://github.com/gitpython-developers/GitPython/security/advisories/GHSA-83vg-56qc-22m7),
[Zod4.6.7](https://github.com/colinhacks/zod/releases/tag/v4.6.7).
DB-Vertrag: [Trivy-Dokumentation](https://trivy.dev/docs/latest/configuration/db/),
[offizielles GHCR-Paket](https://github.com/aquasecurity/trivy-db/pkgs/container/trivy-db),
[Actions/cache](https://github.com/actions/cache). Neuer tatsächlicher DB-Abruf27.10.
