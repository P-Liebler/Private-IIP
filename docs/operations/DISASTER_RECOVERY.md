# Wiederanlauf und Disaster Recovery

Ziele als **Vorschlag**, vor Zielbetrieb vom Operator zu bestätigen: RPO höchstens 24 Stunden bei täglicher erfolgreicher Sicherung; RTO Kern höchstens vier Stunden nach verfügbarem Ersatzhost, Backup und Schlüsseln. Diese Werte sind keine gemessene Garantie. Datenverlust ist mindestens der Zeitraum seit dem letzten verifizierten Backup, bei unbekanntem Sicherungsstand unbekannt. Restore-Dauer, Bytes, Hardware und Ausfallzeit im jeweiligen Bericht messen.

| Ausfall / Erkennung | Sofortmaßnahme des Operators | Wiederherstellung und Prüfung |
| --- | --- | --- |
| Host verloren / VPN und Health weg | Zugriff sperren; Backup und Schlüssel schützen | Ersatzhost patchen, Images/Code pinnen, privates Netz herstellen, isolierten Restore abnehmen, danach freigegeben umstellen. Login/TOTP/TLS/Golden/Hashes/Jobs/Monitoring prüfen. |
| PostgreSQL beschädigt / DB-Health oder Integritätsfehler | Schreibprozesse stoppen; beschädigte Volumes zur Analyse erhalten | In neue DB restaurieren, Migration/Hashes/Ownership/Ledger prüfen. Kein blindes Downgrade oder Überschreiben der einzigen Kopie. |
| MinIO-/Raw-Verlust / Health oder Hashfehler | Imports/Training stoppen; keine Ersatzwerte erzeugen | Ganze Raw-Kopie in neuen Store restaurieren; DB-Referenzen und Modell-/Dokument-SHA prüfen, dann Schreibpfade freigeben. |
| Docker-Volume gelöscht | Betroffenen Stack stoppen; restliche Volumes erhalten | Neue isolierte Volumes aus letztem konsistenten Satz, anschließend vollständiger Restorepfad. |
| CA verloren / TLS-Fehler | Keine Clientwarnungen umgehen | Getrennt verschlüsselte CA restaurieren oder [geplante Rotation](TLS_CA_TRUST.md); Fingerprints/Client-/MinIO-Vertrauen prüfen. |
| TOTP-Key verloren / Faktoren nicht entschlüsselbar | Authzugang begrenzen; keine globalen TOTP-Bypässe | Key aus geschützter Sicherung restaurieren; alternativ einzeln identitätsgeprüfter CLI-Reset mit Sessionwiderruf. [Secret-Vertrag](SECRET_MANAGEMENT.md). |
| Backupziel offline / fehlender Tageserfolg | Ursache und letzte unabhängige Kopie bestimmen; Alarm behandeln | Mount/Netz/Rechte wiederherstellen, unter echtem Jobkonto sichern und isoliert vom unabhängigen Ziel restaurieren. Nicht auf lokalen Ordner ausweichen. |
| Ollama/MLflow ausgefallen | Optionalen Dienst als unavailable anzeigen | Kernportfolio bleibt nutzbar. Keine anderen Modellartefakte oder erfundene Erklärungen als Ersatz; Dienst kontrolliert wieder starten. |

## Wiederanlauf

Zunächst Collection/Forward aus lassen. Datenbank, MinIO, Valkey und CA-Vertrauen prüfen, dann API/Web, Defaultworker und Beat. Idempotente Imports/Actions/Predictions/Alerts nutzen bestehende DB-Checkpoints und Deduplication. Ein verlorener Celery-Queueeintrag ist kein Auftrag zum Neuverbuchen des Ledgers. Persistente RUNNING-Jobs anhand ihrer Service-Resume-Verträge kontrolliert wieder aufnehmen; niemals alte Prognosen oder Manifeste umschreiben. ML-Training kann bei Artefakt-/Runtimeabweichung ausdrücklich fehlschlagen, statt heimlich weiterzulaufen.

Host-/Docker-Daemon-Neustart nur nach ausdrücklicher Freigabe. Containerneustarttests ersetzen keinen Hoststarttest. Nach Wiederanlauf Portbindungen, Daten-/Sessionpersistenz, Queuebearbeitung, Beat-Heartbeat, Tagesbackup und Alarmzustellung tatsächlich prüfen. Verantwortlicher, UTC-Start/Ende, ausgewähltes Backup, Datenverlustfenster, Prüfergebnis und verbleibende Einschränkungen gehören ins Operatorprotokoll.
