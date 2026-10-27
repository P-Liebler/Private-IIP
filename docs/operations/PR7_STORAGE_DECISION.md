# PR7 – Storageentscheidung in Prüfung

Prüfdatum: 26.10.2026. **PREFERRED_CANDIDATE_SEAWEEDFS_4_51 / NOT_APPROVED**.
Diese technische Priorisierung erteilt keine Migrations- oder Betriebsfreigabe.

## Vergleich anhand der Anwendung

| Kandidat | Herstellerbeleg und benötigte Verträge | Entscheidung |
| --- | --- | --- |
| MinIO Community / vorhandenes coollabs-Image | Das [Upstreamrepository](https://github.com/minio/minio) ist seit 25.04.2026 archiviert. Der vorhandene Paketbestand hatte neun Critical-Befunde; ein fremder Containername belegt keinen gepflegten Sicherheitsweg. | Bestand erhalten, keine Freigabe. |
| MinIO AIStor Free | Upstream verweist auf den gepflegten AIStor-Weg. Kostenlose Lizenz bedeutet noch keine geprüfte Offline-, Archivierungs- oder langfristige Nutzbarkeit. | Lizenz-, Aktivierungs- und Wartungsvertrag offen; kein getesteter Ersatz. |
| SeaweedFS 4.51 | [Offizielles Release](https://github.com/seaweedfs/seaweedfs/releases/tag/4.51), aktive Pflege; S3 mit Versionen/Multipart und bereits vorhandene tatsächliche Minio-/boto3-Anwendungsadapter. | Bevorzugter isolierter Prüfkandidat; aktuelle Advisory- und Betriebsabnahme offen. |
| Garage | Die [offizielle Kompatibilitätstabelle](https://github.com/deuxfleurs-org/garage/blob/main-v2/doc/book/reference-manual/s3-compatibility.md) unterstützt keine vollständige S3-Objektversionierung/ListObjectVersions. | Erfüllt den geforderten Versionsmigrationvertrag nicht; nicht installiert. |
| Ceph RGW | [Herstellerdokumentation](https://docs.ceph.com/en/latest/radosgw/s3/) nennt Objektversionen, Multipart, Policies und Metadaten. Die verlinkte Dokumentation beschreibt eine Entwicklungsversion. | Fachlich geeigneter weiterer Kandidat, aber erheblicher zusätzlicher Clusterbetrieb; kein lokaler Ressourcen-/Release-/Restoretest. |

Die Präferenz folgt benötigten Verträgen und vorhandenen Adapterpfaden. Sie folgt keinem Vergleich isolierter CVE-Zähler.

## Exakter neuer Kandidat und Quellprüfung

- Image: `chrislusf/seaweedfs:4.51@sha256:f7a49e3f3972ebed5be2ed4befa4a0c68eb7bdddba6e692d42729ceb545134b8`.
- Offizieller Releasequellcode: Commit `153ab668c99731a6d29492bf6c61d0b4fa701101`, lokal read-only geprüft unter `backups/pr7-seaweed-upstream`.
- Das Image meldet abweichend den Buildstand `ffa87c25f`. Dieser wurde über die offizielle Commit-API zu `ffa87c25fdf587178b1521ad87f2a4a72a02e584` aufgelöst. Die beiden unten genannten Dateien wurden zusätzlich genau dort gelesen und gehasht (`backups/pr7-seaweed-image-source/source-review.json`). Auch dieser Stand enthält die genannten Auth-/Policyprüfungen. Das ist ein Abgleich der gemeldeten Revision, keine reproduzierbare Buildattestation.
- `weed/s3api/s3api_server_grpc.go`: `PutIdentity`, `RemoveIdentity` und die Policy-Schreiboperationen prüfen `checkAdminAuth`. Mit Filer-Signaturschlüssel ist ein gültiger Admin-Bearer nötig; ohne Schlüssel beschränkt die Implementierung auf lokale Peers. Das ist ein Quellbefund, noch kein negativer Laufzeittest des Images.
- `weed/s3api/s3api_object_handlers_postpolicy.go`: Nach Signatur/Formprüfung ruft der Schreibpfad `AuthorizeObjectWrite` und bei ACL-Anforderungen `AuthorizeObjectAclWrite` auf. Das ist kein pauschaler Nachweis aller Policybedingungen oder Codepfade.
- Die gRPC-Portoption `0` bedeutet automatische Portwahl, keine Abschaltung. App-Clients dürfen deshalb nur den TLS-S3-Proxy erreichen; Filer-/Master-/Volume-/Adminports gehören in ein getrenntes internes Netz ohne Hostpublikation.

Der spätere [Advisoryabgleich](../security/PR7_UPSTREAM_ADVISORY_REVIEW.md)
erfasst25 Herstelleradvisories. Im [vollständigen synthetischen Staging](PR7_SYNTHETIC_STAGING.md)
bestanden inzwischen negative Remote-gRPC-/PUT-/POST-Tests, native
Versions-/Retentionsemantik, MLflow-Roundtrip und native RAG-Originalprüfung.
683 Objekte/323 DB-Referenzen wurden mit Wiederaufnahme und unveränderter
Quelle kopiert; alle aufgezeichneten DB-Archivhashes stimmen überein. Der
neue getrennte Anwendungsrestore mit640 Objekten/641 Hashes bestand ebenfalls.
HTTPS-/Ausfall-/Zielbackup-Gesamtprüfung und Freigaben bleiben separat offen.
Alte PR4–PR6-Berichte bleiben historische Nachweise ihrer damaligen Digests.

## Neuer isolierter S3-Vertragslauf

`ops/docker-compose.pr7-s3.yml` ergänzt den vorhandenen synthetischen PR5-Vertrag unter einem eigenen expliziten Projekt. Gepinnte4.51-Stores liegen im internen Storage-Netz, App-/boto3-Probes nur im Clientnetz; ausschließlich der TLS-Proxy verbindet beide. Keine Hostports oder Originalvolumes. Telemetrie ausgeschaltet. Dienste laufen unter UID10001, `volume.nocopy` verhindert die Übernahme des Image-Datenverzeichnisses mit abweichender UID1000. Genau dieser Copy-up-Effekt verursachte den erhaltenen ersten Startfehler, bevor der korrigierte Lauf bestand.

Neuer Lauf `backups/pr7-s3-candidate-v2`: **PASS**, danach Stores/Proxy gestoppt.3 synthetische Objekte/12’600’070 Bytes, Metadaten/SHA256, Range/Streaming, falsche Credentials, strikte CA-Prüfung, Multipart-Abbruch nach5’242’880 bestätigten Bytes und Wiederaufnahme in einem neuen Prozess, Mirror und Objektrestore bestanden. Core-Backend PR7rc2 prüfte mit der echten Storagefactory Quelle→Ziel→Quelle und erneut alle Originalbytes. Die boto3-Probe lief im gepatchten MLflow-Image PR7rc1. Keine echte Trackingserver-/RAG-Abnahme daraus ableiten; keine produktive Endpointänderung. Erhaltene Legacy-Bezeichnungen `pr5-synthetic-*` sind lediglich die wiederverwendeten Fixture-Bucketnamen im neuen isolierten Projekt.

Dieser erfolgreiche begrenzte Vertragslauf schließt weder das allgemeine Versionen-/DB-Referenz-Migrationstool noch das endgültige vollständige Anwendungs-Staging oder Restore ab.

## Freigabereihenfolge

1. Neues synthetisches Staging mit eigenen Volumes/Credentials, strikter CA-Prüfung und getrenntem Storage-Netz.
2. Alle im Auftrag genannten S3-Verträge über echte Anwendungsadapter prüfen; unerfüllte Retention darf nicht als WORM ausgegeben werden.
3. Read-only-Quellmanifest einschließlich Versionen, Delete Markers, Metadaten, Bytehashes und DB-Referenzen; Quellenbestand während Abnahme einfrieren.
4. Dry Run, persistierte Kopierbelege, kontrollierter Multipart-Abbruch/Wiederaufnahme, vollständiges erneutes Lesen des Ziels; Version-IDs explizit zuordnen.
5. PR6-Dokumentrückzüge und technische Wiederholungsbelege mit ihren separaten Hashverträgen erhalten; keine alten Manifesthashes neu berechnen.
6. Zielbackup und isolierter Restore mit exaktem PR7-Imagebestand, Golden CHF 10’180 und unveränderten Altarchiven.
7. Simulierter Cutover/Rollback; tatsächlicher Cutover ausschließlich nach separater Operatorfreigabe.

Der vorhandene `ops/s3_migration_probe.py` bleibt ein synthetischer Prototyp. Er ist noch kein vollständiges allgemeines Versionen-/DB-Referenz-Migrationstool. Keine produktive Konfiguration oder Originalvolumes wurden umgeschaltet.

Der neue allgemeine Vertrag ist `ops/s3_migrate.py`, ergänzt durch den
[vollständigen Stagingbericht](PR7_SYNTHETIC_STAGING.md). Seine synthetische
Bestandsmigration, native Sicherheits-/Adapterprobes und der neue Zielrestore
mit 1381 Hashes bestehen am 27.10. Der feste historische Goldenstichtag und die
heutige Stale-Price-Sperre werden getrennt geprüft. Technische Abnahme und
Produktions-/Security-/Operatorentscheid bleiben ausdrücklich getrennt.
