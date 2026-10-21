# Object-Store-Migration – vorbereiteter Ablauf

Stand: 21.10.2026. **MIGRATION_NOT_AUTHORIZED / NOT_EXECUTED.** MinIO bleibt unverändert. Der isolierte SeaweedFS-SDK-Prototyp ist keine Produktionsfreigabe; [Kompatibilitätsreview](S3_COMPATIBILITY_REVIEW.md). Dieser Ablauf ergänzt den bereits dokumentierten Entscheid und erfindet keinen genehmigten Zielstore.

## Voraussetzungen

1. Operator wählt Distribution, exakten Digest, Wartungsverantwortlichen und privaten Endpunkt nach geprüftem Security-/Lizenz-/Ressourcennachweis. Offene Advisories nicht allein anhand höherer Versionsnummer schließen.
2. Neues isoliertes Ziel, eigene Credentials/Volumes und TLS-Vertrauenskette bereitstellen. Keine alten Volumes mit einem fremden Server starten. Externe Nutzungsrechte und finanzielle Freigaben bleiben unverändert.
3. Quellenbestand einfrieren: API-Importe, Worker, Scheduler und sonstige Schreibpfade stoppen. Den Zustand mit DB-Dump, Quell-Objektbestand und getrennt geschützten Recovery-Schlüsseln sichern. Mindestens ein vollständiger isolierter Restore muss vorher bestanden sein.

## Manifest und Dry Run

Pro Bucket/Schlüssel jede benötigte Version mit Größe, explizit gelesenem SHA-256, Content-Type und anwendungsrelevanten Metadaten erfassen. ETags sind bei Multipart kein SHA-256-Ersatz. DB-Referenzen, Raw-Originale, Modelle, Dokumente, Chunk-/Embeddingversionen und MLflow-Artefakte vollständig zuordnen. Zeitstempel/Zugriffsrechte/Versionierungs- und Retentionsemantik getrennt prüfen; Serverversion-IDs sind nicht automatisch portabel.

Der Dry Run schreibt weder Quelle noch DB-Konfiguration: Quellzählung, verfügbare Zielkapazität, Namenskonflikte, fehlende Objekte und geplante Operationen ausgeben. Keine Secretwerte oder Dokumentinhalte in Berichte aufnehmen. Bei fehlenden Referenzen oder Hashkonflikten stoppen.

## Kopie und Wiederaufnahme

In ein leeres Ziel kopieren; Quellobjekte niemals löschen oder überschreiben. Ein persistenter append-only Checkpoint bindet Quellmanifesthash, Zielkennung und jeden abgeschlossenen Schlüssel/Hash. Nach jedem Upload das Zielobjekt erneut lesen und Größe, SHA-256 und Metadaten vergleichen. Bei vorhandenen Zielobjekten nur nach identischem Hash überspringen; Unterschiede sperren den Lauf. Ein Neustart wiederholt ausschließlich unbestätigte Einträge und bleibt idempotent.

Unterbrechung mit ausschließlich synthetischen Objekten testen: laufenden Transfer abbrechen, partiellen Upload erkennen/isolieren, erneut starten und Endzählung/Hashes vergleichen. Der bisherige PR4-Backup-Abbruch vor dem Mirror ersetzt diesen Mid-Stream-Test nicht.

## Abnahme vor dem Umschalten

- Tatsächliche Minio-/boto3-Aufrufe einschließlich Multipart/Streaming, Range, Metadaten, ungültiger Signaturen und HTTPS mit striktem CA-/Hostnamencheck bestehen.
- Vollständige Zählung und jeder Objekthash stimmen mit dem eingefrorenen Manifest überein; keine ungeklärten Zusatz-/Fehlobjekte.
- Backup-Mirror vom Ziel und vollständiger isolierter Anwendungsrestore auf dem Zielstore bestehen: Golden CHF 10'180 im synthetischen Testportfolio, P6/P7-/Dependency- und P8/P9/P10/PR1/PR2-Checkpoint-Verträge einschließlich Dokumentoriginalen/Embeddings und MLflow-Artefakten.
- Ressourcen, Healthchecks, Netzwerkisolation, Volumerechte, Versionierung, Retention und Wiederanlauf sind tatsächlich geprüft.
- Neuer gescannter Imagebestand, SBOMs, RC und unabhängiger Operatorentscheid liegen vor.

## Umschalten und Rollback

Endpointänderung ausschließlich im genehmigten Wartungsfenster. Zunächst read-only prüfen, dann Schreibpfade kontrolliert freigeben. Den alten Store und das Vorher-Manifest bis zur ausdrücklich bestätigten Abnahme erhalten. Nach neuen Zielschreibvorgängen ist Rückschalten kein bloßer Konfigurationsrollback: neue Daten/DB-Referenzen inventarisieren, Verlustfenster dokumentieren und gesondert entscheiden. Keine automatische Rückmigration oder Löschung der Quelle.

**Noch offen:** Kandidatensicherheit, tatsächliche TLS-/Mirror-/Restore-/Mid-Stream-Abnahme, Ressourcenvergleich auf dem Ziel und Operatorwahl. Aus den bisherigen normalen SDK-Tests wird keiner dieser Nachweise abgeleitet.
