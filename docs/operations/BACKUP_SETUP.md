# Backupbetrieb

Der vorhandene [Backup-/Restore-Vertrag](../architecture/backup-restore.md) bleibt maßgeblich: PostgreSQL-Dump, alle immutable Raw-Objekte einschließlich Modell-/MLflow-/P10-Originalen, Manifest und SHA-256. Secrets und private CA werden separat verschlüsselt gesichert. PR3 ergänzt Dateigröße, dauerhaft getrennten letzten Erfolg sowie gegenseitigen Ausschluss von Backup, Restore und Retention.

## Ziel und Zeitplan

Vor Freigabe tatsächlichen NAS/separaten Host/verschlüsselten externen Datenträger bestimmen. Identität/Mount, Dienstkonto-Rechte, Verschlüsselung im Transport und at rest, getrennte Schlüssel, Kapazität, Aufbewahrung, offline/unveränderliche Kopie und Restore von diesem Ziel protokollieren. Fehlt der Mount, darf der Tagesjob nicht in einen gleichnamigen lokalen Ordner schreiben. Preflight kann Existenz/Zugriff/Platz prüfen, aber keine physische Unabhängigkeit beweisen.

Windows: vorhandenen `ops/install_backup_schedule.ps1` zunächst `-WhatIf` ausführen, dann nur durch Operator registrieren. Daily 03:00 Hostzeit, StartWhenAvailable und IgnoreNew. S4U hat standardmäßig keinen NAS-Netzzugang; eine echte netzwerkberechtigte Task-Identität ist separat einzurichten. Keine Passwörter in Taskargumenten. Job unter genau dieser Identität einmal starten, LastRunTime/LastTaskResult und Backupmanifest vergleichen, fehlendes NAS/fehlgeschlagenen Job prüfen. Docker Desktop muss ohne unbelegte Annahme nach dem tatsächlichen Hoststart verfügbar werden. WSL2-Volumes und NTFS-/NAS-ACL mitprüfen.

Linux: `ops/systemd/private-iip-backup.service`/`.timer` sind nicht installierte Vorlagen. Operator passt `/opt/private-iip`, `/srv/private-iip-backup`, Konto und geschützte Env-Datei an. Mountpoint-Guard verhindert lokalen Fallback. Timer läuft 03:00 UTC mit Persistent=true; systemd startet denselben Service nicht parallel. Dediziertes Docker-berechtigtes Konto hat hostadministrative Rechte. Erst nach Prüfung installieren/aktivieren und nachweisen: timer next/last, service result, Journal, Manifest, Mount-Ausfall und später Hoststart. Diese Vorlage wurde auf dem Windows-Arbeitsplatz nicht als laufender Linux-Dienst abgenommen.

## Integrität und Retention

`python ops/backup.py --compose-file docker-compose.prod.yml --env-file /secure/production.env --root /independent/iip --prune`

Erfolg benötigt Dump **und** erfolgreichen Object-Mirror; Manifest enthält UTC-ID, Status, Dauer, Bytes, Anzahl und SHA-256. Fehlerstatus enthält nur Fehlerklasse, keine Provider- oder Secrettexte. `runtime/backup-status.json` ist der letzte Versuch; `last-successful-backup.json` erhält den letzten guten Stand. Der Backup-/Restore-Lock wird vom Betriebssystem auch bei Prozessabbruch freigegeben. Ein belegtes lokales Backup ist keine unabhängige Produktionssicherung.

Retention wählt erfolgreiche Stände für sieben Tage, vier ISO-Wochen und sechs Monate; ein Stand darf mehrere Klassen abdecken. Fehlgeschlagene Stände werden nicht automatisch gelöscht, letzter Erfolg bleibt erhalten. Löschung bleibt auf direkte aufgelöste Kinder des Sets-Verzeichnisses beschränkt. Der gemeinsame Lock verhindert Pruning während Restore auf demselben Root. Einzelner Host/Dateisystem mit funktionierenden OS-Locks ist der unterstützte Vertrag; mehrere Hosts und NAS-Protokoll-Locksemantik benötigen gesonderte Prüfung. Ein Angreifer mit Schreibzugriff auf Manifest und Dateien kann Prüfsummen neu berechnen; getrennte immutable/offline Kopien sind erforderlich.

Mindestens monatlicher isolierter Restore und nach jedem Backup-/Schema-/Artefaktwechsel. Alte P6-/P7-/P8-/P9-/P10-/PR1-/PR2-Hashes sowie exakt CHF 10'180 prüfen. `ops/restore_verify.py` verwirft beschädigte Dumps/Raw-Dateien vor jedem Dockeraufruf und speichert den Fehlerstatus. Ein Restore erzeugt ausschließlich ein eigenes zufälliges Compose-Projekt ohne Hostports; nie in aktive Produktionsvolumes restaurieren.
