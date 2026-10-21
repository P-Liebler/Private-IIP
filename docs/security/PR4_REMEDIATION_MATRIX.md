# PR4 – Remediation-Matrix

## Aktueller Nachweis vom 21.10.2026

Aktuell priorisiert: P0 Backend certifi-Critical mit verfuegbarem Fix, exakter Modelllock erfordert getrennten Runtimeweg; P0 MinIO 9 Critical und Wartungsentscheidung; P0 PostgreSQL noch 3 Critical (libxml2/zlib/gosu). MLflow pr4-rc4 behebt certifi/Pillow; High- und native/CSP-Reviews offen. Keine genehmigten Exceptions.

[Neue Abnahme und priorisierte Restarbeit](../PR4_ACCEPTANCE_20261021.md). Die folgenden Angaben vom 19./20.10. bleiben als historische Nachweise erhalten; sie sind nicht der aktuelle Sicherheitsstand.


Prüfstand: 20.10.2026. **SECURITY_BLOCKED. Keine genehmigten Exceptions.** Exakte Paketversionen, CVEs, Pfade, Advisories und Digestbindungen stehen im [Endinventar](PR4_IMAGE_INVENTORY.json); der [maschinenlesbare Vergleich](PR4_VULNERABILITY_REPORT.json) erhält auch neu gemeldete Befunde. Die Zahlen zählen Paketbefunde pro Image, keine nachgewiesenen Exploits.

| Komponente | Baseline High / Critical | Endbestand High / Critical | Behandlung und verbleibende Entscheidung |
|---|---:|---:|---|
| Caddy | 4 / 0 | 0 / 0 | Kontrollierter Build derselben Anwendung mit Go 1.27.2 und x/net 0.60.0; HTTPS/CA/Proxy getestet. Ein Unknown-Befund und laufende Buildwartung bleiben zu prüfen. |
| PostgreSQL/pgvector | 115 / 16 | 95 / 4 | OS-Patches bei unverändertem Major 17 und pgvector 0.8.6; Legacy-Restore bestanden. SQLite, libxml2, zlib und gosu benötigen dokumentierte Behandlung; Release blockiert. |
| Valkey | 0 / 0 | 0 / 0 | Identische Version, Digestbindung; ein Medium-Befund bleibt. Recovery getestet. |
| MinIO | 121 / 9 | 121 / 9 | Identische Bytes; archivierter Upstream. Netzwerkisolation und erfolgreicher Restore ersetzen keinen Patch. Gepflegter Patchpfad oder separat genehmigte Migration erforderlich. |
| Backend | 91 / 9 | 44 / 0 | Python 3.12.15 / Trixie, unveränderte numerische Locks, UID 10001/read-only/cap-drop. Verbleibende OS-Befunde benötigen Review. |
| Web | 45 / 3 | 0 / 0 | Node 24.22 LTS, Alpine-Patches, unbenötigte Paketmanager entfernt. Null bekannte Paketbefunde beweisen keine allgemeine Sicherheit; CSP-Restpunkt bleibt. |
| Prometheus | 102 / 4 | 8 / 0 | Version 3.15.0, Digestbindung; Scrape/Regeln und read-only-Betrieb geprüft. Restliche Go-Befunde bleiben offen. |
| Grafana | 146 / 6 | 5 / 0 | Version 12.4.13, Provisioning/Auth und read-only-Betrieb geprüft; restliche Paketbefunde bleiben offen. |
| MLflow | 91 / 9 | 44 / 0 | Python 3.12.15 / Trixie; nicht benötigte Serverjobs/Custom Scorer deaktiviert; UID 10001/read-only, Auth/S3-Roundtrip bestanden. Restliche OS-Befunde bleiben offen. |
| Ollama | 48 / 0 | 48 / 0 | Unverändertes Image; vollständiger unterstützter Paketlauf, zusätzliche native Dateihashes. Native CUDA/cuDNN/GGML/MLX-Abdeckung bleibt unvollständig; keine Inferenz-/GPU-Abnahme. |

## Nachweis und Bewertung

Baseline-DB: 19.10.2026; End-DB: 20.10.2026 07:17:35 UTC, Trivy 0.76.0. Imageänderungen und DB-Änderungen wirken gemeinsam auf den Vergleich. Ein verschwundener Befund wird deshalb nicht automatisch als behoben oder unerreichbar eingestuft. Originalbefunde bleiben erhalten.

Die technischen Maßnahmen sind implementiert und lokal geprüft. **Security-Reviewer/Genehmigung: ausstehend.** `FIX_AVAILABLE` und `FIX_UNAVAILABLE` beschreiben Paketinformationen; sie erteilen keine Freigabe. Unbelegte Codepfade bleiben `REQUIRES_OPERATOR_REVIEW`. Kein privater Hostport, fehlender Herstellerpatch oder erfolgreicher Funktionstest erzeugt automatisch `NOT_APPLICABLE_WITH_EVIDENCE`.

Prioritäten und konkrete PostgreSQL-Primärbelege: [verbleibende Risiken](PR4_RESIDUAL_RISKS.md). MinIO-Entscheid und isolierte Alternativenprüfung: [S3-Review](../operations/S3_COMPATIBILITY_REVIEW.md). Alle High-/Critical-Paketbefunde bleiben ohne genehmigte, digestgenaue Behandlung Freigabehindernisse. Die 13 rohen Critical-Befunde allein halten das Release-Gate geschlossen.
