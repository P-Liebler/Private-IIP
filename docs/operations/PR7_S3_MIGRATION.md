# PR7 – überprüfbare S3-Kopie

Stand 26.10.2026. `ops/s3_migrate.py` ist ein getrenntes Operationswerkzeug.
Es ändert keine Anwendungsendpoints und schreibt niemals in die Quelle.
Produktive Migration und Cutover benötigen eine eigene Operatorfreigabe.

## Verträge

- Explizite Buckets, HTTPS mit CA-Prüfung, getrennte Zielbucketnamen und Zielendpoint.
- Read-only-Inventar aller nativen Versionen einschließlich Nullversionen und
  Löschmarker. Jede Objektversion wird vollständig gelesen und mit SHA-256 erfasst.
- Content-Header, Benutzer-Metadaten und Tags werden geprüft; ACL-/Bucket-Policies
  sind eine separate Betreiberabnahme. KMS/SSE, Archivspeicherklassen und aktive
  Retention-/Object-Lock-Verträge sperren diesen Kopierpfad bis zu einem geprüften
  Policy-Migrationsverfahren. Nicht unterstützte oder verweigerte Lock-Abfragen
  gelten ausdrücklich nicht als Beweis fehlender Retention.
- DB-Referenzen müssen genau einen passenden Originalhash erreichen. Das
  Quiesce-Checkpoint und der konsistente DB-Dump gehören zum selben Belegsatz.
- Unveränderliches Manifest mit Inhaltsdigest; atomar ersetztes, synchronisiertes
  Journal mit OS-Prozesssperre, Manifest-/Endpoint-/Bucketbindung und Teilenachweisen.
- Multipart-Wiederaufnahme prüft gespeicherte Teile; ein verlorener Abschlussbeleg
  wird durch vollständiges erneutes Lesen des Zielobjekts rekonstruiert. Dubletten
  erzeugen bei Wiederholung keine neue Objektversion.
- Vorhandene abweichende oder unerwartete Zielobjekte, geänderte Quellen,
  beschädigte Manifeste und fehlende DB-Referenzen brechen die Kopie ab.
- Historische Bytes liegen unter `__pr7_archive/<Manifestdigest>/<Versiondigest>`.
  Das Manifest bewahrt ursprüngliche Schlüssel, Version-IDs und Löschmarker;
  das Journal ordnet neue Zielversionen zu. Native Version-IDs werden nicht erfunden
  oder gleichgesetzt. Aktuelle nicht gelöschte Schlüssel stehen zusätzlich unter
  ihrem Originalnamen für bestehende Anwendungsadapter bereit.

Das ist eine logische Versionsabbildung, keine identische Wiederherstellung der
internen Versionshistorie eines anderen Servers. Anwendungen mit gepinnten nativen
S3-Version-IDs benötigen vor einem Cutover eine gesonderte Referenzmigration.
Die Anwendung nutzt derzeit unveränderliche Objektschlüssel und Byteshashes.

## Ablauf für später autorisierte Kopien

1. Schreiber anhalten, aktuelle Archive samt separaten Dokumentrückzugs- und
   UI-Anfragehashes prüfen; DB-Dump erstellen. Quelle nur mit Leserechten anbinden.
2. `ops/export_s3_references.py` in den API-Container pipen und seine JSON-Ausgabe
   privat sichern. Sie enthält Raw-Originale, Modellarchive und Dokumentoriginale
   einschließlich zurückgezogener Dokumente. MLflow verwendet einen eigenen
   Tracking-/Artefaktvertrag: dessen Referenzen zusätzlich aus dem konsistenten
   Tracking-DB-Dump exportieren und explizit derselben Referenzliste hinzufügen.
3. Frische getrennte Zielbuckets mit aktivierter Versionierung und geprüften
   privaten Zugriffsregeln vorbereiten. Quelle und Ziel dürfen nicht dieselben
   Bucketnamen verwenden. Keine Originalvolumes wiederverwenden.
4. Zugangsdaten ausschließlich als `MIGRATION_SOURCE_ACCESS_KEY`,
   `MIGRATION_SOURCE_SECRET_KEY`, entsprechende `MIGRATION_TARGET_*`-Variablen
   setzen. `MIGRATION_SOURCE_ENDPOINT`/`MIGRATION_TARGET_ENDPOINT` sind HTTPS;
   optionale `*_CA_FILE` verwenden. Boto3 aus dem gepinnten Operationsruntime nutzen.
5. Inventar und Dry Run ausführen:

   ```text
   python ops/s3_migrate.py inventory --bucket raw-originals --references private/refs.json --manifest private/manifest.json
   python ops/s3_migrate.py dry-run --manifest private/manifest.json
   ```

6. `private/target-map.json` enthält beispielsweise
   `{"raw-originals":"isolated-raw-copy"}`. Nur das ausdrücklich autorisierte
   isolierte Ziel beschreiben:

   ```text
   python ops/s3_migrate.py copy --manifest private/manifest.json --target-map private/target-map.json --journal private/journal.json --authorize-isolated-target
   ```

   Derselbe Aufruf setzt nach Prozessverlust fort. `--stop-after-parts 1` erlaubt
   einen kontrollierten Abbruch mit Exit77. Die Quelle muss unverändert bleiben.
   Journalverlust bei bestehendem Ziel erfordert eine gesonderte Untersuchung;
   das Werkzeug adoptiert keinen fremden Bestand automatisch.
7. Manifest, Referenzexport, Journal und DB-Dump gemeinsam in ein unabhängiges
   Backup aufnehmen. Keine Dateinamen oder DB-Referenzen nach GitHub hochladen.
8. In separatem App-Staging tatsächliche Raw-/Modell-/Dokument-/RAG-/MLflow-Wege
   sowie Restore prüfen. Cutover/Rollback ausschließlich im Staging simulieren;
   Originalendpoint weiter unverändert lassen. Das Kopierwerkzeug allein erteilt
   keine Freigabe. Abweichungen bleiben ein fehlgeschlagener Lauf mit privatem
   Journal; keine automatische Bereinigung und kein Überschreiben der Belege.

## Prüfung

Dreizehn lokale Tests prüfen Wiederaufnahme, Versionen, Löschmarker, vollständige Zielkontrolle,
Idempotenz, Quelländerung, Manifestkorruption, Zielkollision und verlorene
Abschlussbelege, exklusive Manifestanlage und die erzwungene Read-only-
Operationsliste der Quelle (`ops/tests/test_s3_migrate.py`). Fehlerhafte Kopien
erhalten einen fehlgeschlagenen Journalstatus samt Abweichungen; ein alter
Erfolg bleibt bei einer später fehlgeschlagenen Prüfung nicht als aktueller
Status stehen. Der reale isolierte API-Probelauf
liegt getrennt in `ops/pr7_general_migration_probe.py`; ein Fixture-Erfolg ersetzt
keine Migration des vollständigen PR6-Bestands oder dessen abschließenden Restore.
Der tatsächliche isolierte Lauf vom 26.10. bestand mit 6 Versionen/Löschmarkern,
einer expliziten Referenz, Multipart-Unterbrechung und neuem Prozess,
unverändertem Journal bei Wiederholung sowie ohne Wiederbelebung des gelöschten
aktuellen Schlüssels. Beleg `backups/pr7-general-migration-v2/evidence/general-migration/result.json`.
Eigenes Projekt, Volumes und Credentials; danach gestoppt. Der vorherige
fehlgeschlagene Lauf mit erschöpfter Volumeanzahl bleibt als Fehlerbeleg erhalten.

API-Verträge am 26.10.2026 anhand der Primärdokumentation geprüft:
[ListObjectVersions](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectVersions.html),
[CompleteMultipartUpload](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html),
[GetObjectRetention](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectRetention.html).

Der anschließende vollständige synthetische Bestandstest bestand mit 683
Objekten/323 DB-Referenzen einschließlich Wiederaufnahme und unveränderter
Quelle. V2 pinnt ursprüngliche Änderungszeitpunkte und prüft die gesamte
Quellversionsmenge vor und nach der Kopie. Ein kurzes Windows-Sharing-Lock
erhält begrenzte Journal-Rename-Retries; ein dauerhafter Lock bleibt ein Fehler
mit erhaltenem letzten vollständigen Beleg. Details im
[Stagingbericht](PR7_SYNTHETIC_STAGING.md). Dort ist auch die explizite Aufnahme
der Versionszuordnungsbelege ins neue Zielbackup beschrieben.
