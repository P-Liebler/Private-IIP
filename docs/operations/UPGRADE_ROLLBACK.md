# Update und Rollback

1. Wartungsfenster, aktuelles Image/Commit/Digest, Env-Version und Schema-Head erfassen. Secretdatei nur geschützt referenzieren.
2. Preflight, unabhängiges Backup und dessen letzten Restore prüfen; für einen exakten Archive-Checkpoint alle Schreibprozesse kontrolliert einfrieren.
3. Alembic-Diff und Migrationsauswirkungen ausdrücklich reviewen. Alte Migrationen nicht bearbeiten. Neues Image zuerst in isoliertem Staging bauen/prüfen.
4. Kontrolliert migrieren und Dienste aktualisieren; Health, TLS/Auth, eigenes Testportfolio, Modell-/Raw-Integrität, Worker/Beat/Monitoring prüfen. Daten- und Source-Gates bleiben aus, bis separat freigegeben.
5. Operator protokolliert Ergebnis; erst dann produktive Nutzung freigeben.

`ops/deploy.py` bietet standardmäßig DRY_RUN sowie STAGING/PRODUCTION mit ausdrücklichen Flags für Autorisierung und Migrationsreview. Es führt vorhandene Preflight-/Backup-/Compose-/Alembicpfade aus und stoppt beim ersten Fehler. Es ist keine automatische Releasefreigabe und speichert keine erfundene Zielabnahme. Der Erstinstallationspfad muss eine leere Basis kontrolliert vorbereiten; fehlendes Backup stoppt den Updateweg sicher.

`rollback-prep` sichert den aktuellen Zustand, führt aber kein Rollback aus. Ein altes Image kann mit neuem Schema inkompatibel sein. Dann in **neue isolierte Volumes** den vor dem Update verifizierten Satz plus passende Secrets/CA und alte Images restaurieren, Hashes und funktionale Abnahme prüfen, erst anschließend im Wartungsfenster umschalten. Zwischenzeitliche neue Daten müssen als mögliches Verlustfenster ausgewiesen werden; keine blinde Alembic-Downgrade-Ausführung. Die einzige alte Kopie und immutable Archive dürfen nicht überschrieben werden.

Numerische/Assistant-Dependency-Locks bleiben unverändert. Sicherheitsupdates an diesen Pins sind eine ausdrückliche Runtime-Migration mit neuen Modellartefakten und vollständiger Validierung, niemals nachträgliche Änderung archivierter Manifeste.
