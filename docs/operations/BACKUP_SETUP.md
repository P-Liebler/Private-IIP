# Backupbetrieb

## PR9: aktueller Core-Vertrag (28.10.2026)

Die folgenden älteren Beispiele ohne Core-Overlay gehören zum Legacy-Profil. Für Private Core immer `docker-compose.prod.yml` **und** `ops/docker-compose.core.yml` mit der gleichen privaten Environmentdatei verwenden. Der vorhandene Backupmotor bleibt unverändert zuständig für Dump, Raw-Dateien, Hashmanifest, Lock und Retention; PR9 ergänzt Schutz des ausgewählten Ziels und der Overlay-Environmentvariablen.

```powershell
python ops/backup.py --compose-file docker-compose.prod.yml --compose-override ops/docker-compose.core.yml --env-file C:/privat/core.env --root E:/Private-IIP-Backups --destination-policy C:/privat/backup-destination.json --prune
```

Dies ist ein späterer Operatoraufruf, kein ausgeführter Produktionsjob. Die geschützte Zielpolicy entsteht aus `ops/windows-backup-destination.example.json` erst nach tatsächlichem Review: absolute Zielwurzel, Volume-Seriennummer, benannter Operator/UTC-Zeitpunkt und Hash der echten Schlüssel-/Restoreprobe. Das Beispiel ist absichtlich nicht freigegeben. Der Windows-Guard prüft vor jedem Schreibzugriff tatsächlichen Mount/ACL, genaue Volumeidentität, anderes physisches Laufwerk als Systemdisk und vollständig aktivierte, entsperrte BitLocker-Verschlüsselung. Fehlende Rechte auf BitLocker-/Diskabfragen sind ein Fehler, kein angenommener Erfolg. Ziel muss zusätzlich physisch/administrativ unabhängig von **allen** App-/Docker-Datenträgern sein; eine andere Partition oder bloß andere Seriennummer genügt nicht. Diese zusätzliche Identität und eine Offline-/unveränderliche Kopie werden durch tatsächlichen Operatorreview belegt. NAS-/Linux-Ziele benötigen ihren vorhandenen Mount-/Verschlüsselungsnachweis; der Windows-Guard behauptet dort keine Prüfung und scheitert ausdrücklich.

Windows-Zeitplan zunächst nur anzeigen:

```powershell
./ops/install_backup_schedule.ps1 -EnvFile C:/privat/core.env -BackupRoot E:/Private-IIP-Backups -ComposeOverride ./ops/docker-compose.core.yml -DestinationPolicy C:/privat/backup-destination.json -TaskName PrivateIIP-Core-Backup -DailyTime 03:00 -WhatIf
```

Erst nach dokumentierter Freigabe ohne `-WhatIf` registrieren. Nach Registrierung `Get-ScheduledTaskInfo -TaskName PrivateIIP-Core-Backup`, Start/Ende, `LastTaskResult=0` und **neues** erfolgreiches Manifest am überprüften Ziel vergleichen. Job unter dem echten Dienstkonto ausführen. BitLocker-/Geräteabfragen können administrative Rechte benötigen; der Guard muss unter genau diesem Konto erfolgreich geprüft sein. `-RunElevated` bereitet ausschließlich nach gesondertem Operatorreview eine Task mit `Highest` statt standardmäßig `Limited` vor; dies erfordert entsprechende Hostrechte und ist keine hier ausgeführte Erhöhung. Dockerzugriff selbst ist hostadministrativ. S4U kann keine NAS-Zugänge voraussetzen. Der Timer allein beweist keinen gelungenen Backupzugriff.

Linux: vorhandene `private-iip-backup.service`/`.timer` als Vorlage behalten; im operatorgeprüften Service-Drop-in den bestehenden `ExecStart` durch denselben Backupaufruf mit `--compose-override ops/docker-compose.core.yml` ersetzen. Die bisherige Legacy-Preflightzeile entsprechend ersetzen oder den vollständigen Core-Installationspreflight vor Inbetriebnahme separat abnehmen. Mountpoint und tatsächliche entschlüsselte Gerätidentität vor **jedem** Lauf prüfen (z.B. `mountpoint`, `findmnt`, `cryptsetup status` unter dem tatsächlichen Dienstkonto). Kein Fallback in einen gleichnamigen lokalen Ordner. Ein stale Security-DB-Bericht darf das Notfallbackup nicht verhindern; fortlaufende Backupjobs benötigen einen überprüften Zielguard, nicht täglich eine neue Installationsfreigabe. Die Vorlagen wurden hier nicht als Linux-Dienst installiert oder abgenommen.

Retention bleibt 7 Tage/4 ISO-Wochen/6 Monate mit höchstens 17 vollen Sätzen als konservative Kapazitätsbasis. Zunächst tatsächliche Bytes und Wachstum messen; 5 GiB sind nur die Prüfuntergrenze. `--prune` nutzt weiter den vorhandenen Lock und darf nur den geprüften Root verwalten. Erst bei bestätigtem unabhängigen Ziel anwenden; hier wurde keine bestehende Datei gelöscht.

Vorhandene Prometheusregeln erkennen Backupfehler bzw. fehlenden Erfolg nach 26 Stunden, weniger als 15 Prozent freien Platz sowie fehlende/ältere Restoreproben nach 31 Tagen. Weil unveränderte letzte Erfolge verpasste Tagesläufe sichtbar machen, zusätzlich den tatsächlichen Timer-/Taskverlauf prüfen. Am Ziel kontrolliert testen: nicht verfügbares Backupziel, scheiternder Tagesjob, ausbleibender Folgelauf und überfälliger Restore. Alarm-Firing **und echten Empfang mit Empfängerbestätigung** dokumentieren. Prometheus ohne tatsächlich eingerichteten Benachrichtigungskanal ist keine Alarmzustellungsabnahme.

Monatlich sowie nach Schema-/Image-/Artefaktänderungen vollständig vom unabhängigen verschlüsselten Ziel restaurieren. Separates verschlüsseltes Secretbackup für DB-/S3-Zugänge, ursprünglichen TOTP-Key und private CA, getrennte Recoverykeyverwahrung und Negative-Key-Probe gemäß [Secretvertrag](SECRET_MANAGEMENT.md). Keine Secrets in gewöhnliche Backups oder Manifest-/Receipttexte kopieren. Der [ausführbare Hostablauf](PRIVATE_CORE_INSTALLATION.md) protokolliert alle zwölf tatsächlichen Zieltests; alle bleiben ohne Zielhost offen.

Lokaler PR9-Pfad `C:\Users\liebler\Private-IIP-Local-Staging-Backups`: geschützt und ausreichend frei, aber **kein unabhängiger und kein nachgewiesen verschlüsselter Datenträger**. Es wurde kein Produktionszeitplan installiert und keine Recoveryfreigabe erzeugt.

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

## Zusätzliches OpenShift-Ziel

Der bestehende Motor kann mit `--openshift-config` einen explizit reviewten
`oc`-Transport verwenden. Keine automatische Clusteraktion, kein Docker-Fallback
und kein behaupteter Clusterrestore. [OpenShift-Backupvertrag und Operatorweg](OPENSHIFT_ARGOCD.md#manueller-oc-transport).
