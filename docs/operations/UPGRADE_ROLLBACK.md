# Update und Rollback

1. Wartungsfenster, aktuelles Image/Commit/Digest, Env-Version und Schema-Head erfassen. Secretdatei nur geschützt referenzieren.
2. Preflight, unabhängiges Backup und dessen letzten Restore prüfen; für einen exakten Archive-Checkpoint alle Schreibprozesse kontrolliert einfrieren.
3. Alembic-Diff und Migrationsauswirkungen ausdrücklich reviewen. Alte Migrationen nicht bearbeiten. Neues Image zuerst in isoliertem Staging bauen/prüfen.
4. Kontrolliert migrieren und Dienste aktualisieren; Health, TLS/Auth, eigenes Testportfolio, Modell-/Raw-Integrität, Worker/Beat/Monitoring prüfen. Daten- und Source-Gates bleiben aus, bis separat freigegeben.
5. Operator protokolliert Ergebnis; erst dann produktive Nutzung freigeben.

`ops/deploy.py` bietet standardmäßig DRY_RUN sowie STAGING/PRODUCTION mit ausdrücklichen Flags für Autorisierung und Migrationsreview. Es führt vorhandene Preflight-/Backup-/Compose-/Alembicpfade aus und stoppt beim ersten Fehler. Es ist keine automatische Releasefreigabe und speichert keine erfundene Zielabnahme. Der Erstinstallationspfad muss eine leere Basis kontrolliert vorbereiten; fehlendes Backup stoppt den Updateweg sicher.

`rollback-prep` sichert den aktuellen Zustand, führt aber kein Rollback aus. Ein altes Image kann mit neuem Schema inkompatibel sein. Dann in **neue isolierte Volumes** den vor dem Update verifizierten Satz plus passende Secrets/CA und alte Images restaurieren, Hashes und funktionale Abnahme prüfen, erst anschließend im Wartungsfenster umschalten. Zwischenzeitliche neue Daten müssen als mögliches Verlustfenster ausgewiesen werden; keine blinde Alembic-Downgrade-Ausführung. Die einzige alte Kopie und immutable Archive dürfen nicht überschrieben werden.

Numerische/Assistant-Dependency-Locks bleiben unverändert. Sicherheitsupdates an diesen Pins sind eine ausdrückliche Runtime-Migration mit neuen Modellartefakten und vollständiger Validierung, niemals nachträgliche Änderung archivierter Manifeste.
## PR4-Ergänzung: Auditbindung und Rollbackgrenzen

Vor einem Upgrade müssen Quellstand, Lockfiles, Konfigurationsvertrag, SBOM-Bytes und tatsächliche Image-Digests im unveränderlichen RC-Manifest gebunden sein. `ops/deploy.py` verweigert Produktion bei offenen Security-/Zielhost-/Operator-Gates und baut dort keine Images neu. Ein Tagvergleich genügt nicht. Eigene Caddy-/PostgreSQL-Builds benötigen eine nachvollziehbare Bereitstellung der geprüften Bytes auf dem Zielhost.

PostgreSQL bleibt Major 17, pgvector 0.8.6. Ein späterer Major-Wechsel braucht einen eigenen Dump-/Restore-/Kollations- und Queryvergleich; kein blindes Starten auf bestehenden Volumes. Die Python-Basisänderung erhält die numerischen Locks und verlangt die strikte Prüfung alter Modellmanifeste. Keine historischen Manifeste umschreiben, um einen Rollback zu ermöglichen.

Ein Code-/Image-Rollback darf nur auf nachweislich schemakompatible Digests erfolgen. Nach angewandter inkompatibler Migration gibt es keine automatische Alembic-Rückmigration: kontrollierter Restore aus geprüftem Backup, dokumentierter Datenverlustzeitraum und separate Operatorentscheidung. Der alte Bestand bleibt bis zum abgeschlossenen Nachweis verfügbar. MinIO wird durch PR4 nicht automatisch migriert; siehe [S3-Review](S3_COMPATIBILITY_REVIEW.md).
