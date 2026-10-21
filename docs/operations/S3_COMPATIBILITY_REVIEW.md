# PR4 – S3-Kompatibilitätsprüfung

Prüfdatum: 20.10.2026. **Kein Speicherwechsel freigegeben.** MinIO bleibt vorläufig der bestehende Speicher; seine offenen Sicherheitsbefunde blockieren die Release-Freigabe.

## Tatsächlich getesteter Kandidat

SeaweedFS 4.48, `chrislusf/seaweedfs:4.48@sha256:4e61d15fd35994cb1e43e1e553dff106794841fd9a99ade2fc8c8bfce4d7872d`. Separates Compose-Projekt `private-iip-pr4-s3-probe`, internes Netz ohne Hostports, eigenes Volume und ausschliesslich generierte Testzugänge. Kein Zugriff auf bestehende Raw- oder Modellobjekte. Reproduzierbare Definition: `ops/docker-compose.s3-probe.yml`; Prüfung: `ops/s3_compatibility_probe.py`.

| Vertrag | Ergebnis |
|---|---|
| Tatsächlicher `MinioObjectStorage`-Adapter mit installiertem Minio-SDK | Bestanden: Bucket, Multipart-Put, Stat, Get, List, Metadaten |
| Wiederholtes Schreiben desselben Raw-Schlüssels | Durch den bestehenden Adapter abgelehnt; Server-WORM dadurch nicht bewiesen |
| boto3 aus dem MLflow-Image | Bestanden: Get, Head/Metadaten, Range, `upload_fileobj` |
| Ungültige S3-Signatur | Abgelehnt |
| Versionierung | Aktiviert und exakte alte Objektversion zurückgelesen |
| Objektintegrität | 7'020'000 synthetische Bytes, SHA-256 `e16789866c65748f876adafc20ee96f3de549e842f648a5d6b03136a322ce334` |

Lokale Nachweise: `backups/pr4-s3-minio-sdk-v4.txt`, `backups/pr4-s3-boto3-sdk.txt`. Frühere Fehlversuche bleiben erhalten: zunächst fehlender Python-Modulpfad, danach zu wenig Testvolumes für die Bucket-Allokation; nach Korrektur bestanden. Diese Harnessfehler sind kein Nachweis einer Anbieterinkompatibilität.

## Offene Sicherheits- und Betriebsprüfung

Die [S3-Dokumentation](https://github.com/seaweedfs/seaweedfs/wiki/Amazon-S3-API) ersetzt keine Integrationstests. Der [Upstream-Sicherheitsbereich](https://github.com/seaweedfs/seaweedfs/security) enthält relevante Hinweise:

- [GHSA-99q7-x53r-6j4g](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-99q7-x53r-6j4g): Filer-TUS-Autorisierung, betroffene Versionen ab 4.39, kein Patch angegeben. Der Kandidat wird deshalb nicht pauschal als sicher eingestuft.
- [GHSA-5fx4-c9qp-36jc](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-5fx4-c9qp-36jc): unauthentifizierte S3-gRPC-Identitätsverwaltung, angegebener Bereich bis 4.45; kein dokumentierter Patch im Advisory. Die höhere Versionsnummer allein belegt keine geprüfte Behandlung dieses Codepfads.
- [GHSA-qmx6-fpcw-q3xg](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-qmx6-fpcw-q3xg): Bucket-Policy bei POST-Uploads, angegebener Bereich bis 4.45. Keine Freigabe aus dem erfolgreichen normalen PUT-Test ableiten.

Nicht abgenommen: private TLS-Konfiguration, Einschränkung der internen Verwaltungsports, vollständiger MLflow-Server-Artifact-Roundtrip, Produktionsgrössen/Streaminglast, unterbrochene Objektmigration, unabhängiges Backup und vollständiger Restore auf SeaweedFS. Die Prüfung nutzt internes HTTP und beweist keine Produktions-TLS-Sicherheit. Der vollständige Kandidatenscan ist separat zu bewerten; Paketbefunde allein ersetzen die Advisory-Prüfung nicht.

Der separate vollständige Kandidatenscan mit der DB vom 20.10.2026 meldet **4 High, 0 Critical, 15 Medium**. [Inventar und originale SBOM](../security/pr4-s3-prototype/inventory.json), formal validiert. Diese Paketprüfung beseitigt die oben beschriebenen Advisory- und Betriebsgrenzen nicht.

Garage wurde anhand seiner [S3-Kompatibilitätsdokumentation](https://garagehq.deuxfleurs.fr/documentation/reference-manual/s3-compatibility/) gesichtet, jedoch nicht installiert oder getestet. Dafür wird kein Kompatibilitätserfolg behauptet.

## Entscheidung und spätere Migration

**REQUIRES_OPERATOR_REVIEW / STORAGE_MIGRATION_NOT_AUTHORIZED.** MinIO wird nicht automatisch ersetzt. Der [archivierte MinIO-Upstream](https://github.com/minio/minio) und ein Community-Build begründen keine langfristige Security-Freigabe. Ein alternativer Speicher benötigt erst einen vertretbaren Sicherheits- und Betriebsnachweis und eine explizite Operatorentscheidung.

Vor einer späteren Migration ist ein separates Verfahren erforderlich: unveränderte Quelle und neues isoliertes Ziel, Manifest jedes Schlüssels mit Grösse, Version, SHA-256 und Metadaten; Dry Run; Kopieren ohne Überschreiben; Hashvergleich nach erneutem Lesen; persistente Checkpoints zur Wiederaufnahme; idempotente Wiederholung; Gesamtzählung; Modell-/Dokument-/Embedding- und MLflow-Prüfung; vollständiger isolierter Restore; Rückfall auf die unveränderte Quelle. Kein Löschen der Quelle und kein automatischer Endpointwechsel. Dieses Verfahren ist hier als Anforderung dokumentiert und noch nicht als durchgeführte Migration ausgewiesen.
