# PR3B – Betriebszuverlässigkeit

Stand 19.10.2026. **LOCALLY_TESTED; LOCAL_RECOVERY_ACCEPTED; OPERATOR_GATES_OPEN.** PR3A hat verwertbare Sicherheitsbefunde und offene Zielgates, keine Produktionsfreigabe. Die autorisierte lokale Vorbereitung ist abgeschlossen; es gibt keinen behaupteten Betreiberhost.

Vorhandene Backup-/Restore-/Scheduler-/Monitoringpfade wurden erweitert, keine zweite Daten-/ML-Architektur. Gegenseitiger OS-Dateilock schützt Backup/Restore/Retention auf derselben Wurzel; Windows-Byte-Lock wurde mit echtem konkurrierenden Zugriff getestet. Pfadprüfung verhindert Sets außerhalb der ausgewählten Wurzel. Fehlgeschlagene Sicherung pruned nicht. Manifest enthält Größe; letzter guter Backupstatus bleibt separat erhalten. Restore-Hashfehler werden vor jedem Dockeraufruf sichtbar abgewiesen. Elf Offline-Goldens bestanden.

Windows-Tagesjob bleibt ein expliziter Operatorinstaller (S4U/NAS-Grenze dokumentiert). Linux systemd-Service/Timer mit Persistent, Mountpoint-Guard und Preflight als **nicht installierte, auf Linux noch nicht betrieblich geprüfte Vorlage** ergänzt. Kein realer Zeitplan installiert. Gemeinsamer Hostlock verhindert Überlappung; NAS-/Mehrhost-Locksemantik muss am Ziel geprüft werden.

Monitoring ergänzt MinIO, Worker-Control-Ping, abgeschlossenen Dispatch, Restorealter/-fehler und freien Backupplatz samt Prometheus-Regeln. Worker-Ping ist kein Verbrauchsnachweis, Dispatchalter deckt ausbleibende Verarbeitung ab. CPU/RAM/Hostkapazität sind zusätzlich hostseitig zu messen. Optionales MLflow/Ollama sind getrennte Capabilityzustände. JSON-Logs sind begrenzt; keine vertraulichen Portfolio-/Dokumentwerte in Metriklabels.

`ops/deploy.py` ist standardmäßig DRY_RUN, mit getrenntem STAGING/PRODUCTION-Modus und expliziten Operator-/Migrationsreviewflags für Änderungen. Vorhandene Backup-/Compose-/Alembicwerkzeuge werden wiederverwendet. Kein automatisches Rollback nach Schemaänderung; Recovery in neue Volumes ist dokumentiert.

Der synthetische TOTP-Key-Drill prüft verschlüsselte Key-Wiederherstellung und Ablehnung eines falschen Keys. Er ist keine echte CA-/Client-/Konten-Recovery und liest keine Betreibersecrets. Der vollständige isolierte Operatorworkflow ist in [Secret Management](operations/SECRET_MANAGEMENT.md) beschrieben und bleibt offen.

Kontrollierte lokale Staging-Faults sind **bestanden**, UTC 10:15:23–10:20:40 am 19.10.2026: Beat/Worker-Ausfall lässt Bewertung verfügbar; MinIO/PG/Valkey-Ausfall liefert 503-Readiness; nach Start sind Readiness und Golden CHF 10'180 wieder korrekt. Nach API-Neustart bleibt die persistierte Session gültig; Logout widerruft sie. Unvertraute CA und fremde Origin werden abgewiesen. Keine echten Provideraufrufe. Der erste Probe-Runner erwartete bei Logout fälschlich 200 statt des bestehenden 204-Vertrags; nach Korrektur wurde der gesamte Faultlauf erfolgreich wiederholt.

Gemessene Recovery-Zeiten einschließlich Compose-/Health-Warten: Scheduler 59,478 s, Worker 97,023 s, MinIO 18,645 s, PostgreSQL 13,420 s, Valkey 12,319 s, API-Warmneustart 12,776 s. Lokaler kompletter Container-Prozessstart mit vorhandenen Volumes/OS-Caches: **96,382 s**, bestanden; kein Host-/Daemonreboot, keine behauptete Erstinstallation auf leerer Hardware. Raw-Artefakte unter `backups/pr3-staging-recovery-final.json` und `pr3-cold-start-result.json`.

Optionaler Ollama-Dienst fehlt im separaten Staging: Assistantstatus ist ausdrücklich nicht verfügbar, Portfolio/Research-/Risikopfad bleiben nutzbar. P7/P9-Regression erhält zudem den bestehenden MLflow-Ausfallvertrag. Ein ausgefallener Finanzprovider wird nur über vorhandene Offline-Transportfixtures simuliert; keine unfreigegebene Livequelle aktiviert.

Frisches Backup `backups/pr3-acceptance/sets/20261019T103107Z-64300`: **320 Rohobjekte, 2.914.753 Bytes, 16,311 s**, Dump und Mirror erfolgreich. Schreibprozesse wurden vor Checkpoint/Dump eingefroren. Neuer isolierter Restore **10:32:03–10:33:48 UTC**, **104,332 s**, erfolgreich; eigene Container, Netzwerke und Volumes anschließend entfernt. Login, exakte Raw-/Modell-/Dataset-/History-Hashes und Golden CHF 10'180 geprüft. Der letzte erfolgreiche Backupstand ist in der Operatoransicht vom letzten Versuch getrennt sichtbar.

RPO 24 h / RTO 4 h sind ausdrücklich **unbestätigte Planungsziele**, keine Leistungszusage. Die Restorezeit betrifft diesen kleinen technischen Fixturebestand auf vorhandener Hardware mit gecachten Images, keine vollständige Disaster-RTO. Containerneustarts ersetzen keinen Host-/Docker-Daemon-Neustart. Zwölf Hostgoldens und Prometheus-Regelprüfung (**14 Regeln**) bestanden. Lokale CLI→Celery-Ping-Probe erfolgreich in **5,695 s inklusive Prozessstart**.

**INDEPENDENT_BACKUP_VERIFIED=false, DAILY_BACKUP_SCHEDULE_VERIFIED=false, SECRET_RECOVERY_VERIFIED=false, MONITORING_ALERT_DELIVERY_VERIFIED=false.** Regeln und Grafana beweisen keine zugestellte Warnung. Es wurde keine Nachricht an Dritte versendet.
