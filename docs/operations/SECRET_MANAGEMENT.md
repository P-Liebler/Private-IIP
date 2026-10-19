# Secrets und Wiederherstellung

Kein Secret gehört in Git, Build-Args, Browserstorage, URL-Logs oder gewöhnliche Anwendungsbackups. Vorhandene Compose-Env-Dateien liegen außerhalb des Repositorys: Linux 0600 und übergeordneter Ordner 0700; Windows NTFS-ACL ausschließlich Dienstkonto/benannte Administratoren/SYSTEM. Effektive ACL mit `Get-Acl` prüfen; Docker-/Hostadministratoren können Containerumgebungen lesen. Docker-Secrets wurden nicht als scheinbare vollständige Migration ergänzt: einige bestehende Images und der gemeinsame Settings-Vertrag verwenden noch Env-Werte. Diese Restexposition ist im Sicherheitsreview zu berücksichtigen.

| Material | Betroffene Funktion | Verlust / Rotation |
| --- | --- | --- |
| TOTP_ENCRYPTION_KEY | Verschlüsselte aktive/pending TOTP-Faktoren | Ohne alten Schlüssel nicht entschlüsselbar. Ein neuer Schlüssel allein repariert keine Konten. Autorisierter CLI-Reset nach Identitätsprüfung widerruft Sessions; Benutzer richtet TOTP neu ein. |
| Caddy privates CA-Material | TLS-Ausstellung und bestehendes Client-/MinIO-Vertrauen | CA wiederherstellen oder geplante Vertrauensrotation durchführen. |
| DB-/MinIO-Passwörter | Dienstzugang | Kontrolliert bei Dienst und allen Konsumenten ändern; Datenvolumes nicht löschen. |
| Grafana-/MLflow-Zugang | Administration | Gesondert rotierbar, Persistenz/Authdatenbank berücksichtigen. |
| Backup-Verschlüsselungsschlüssel | Zugriff auf unabhängige Sicherungen | Außerhalb desselben Backupziels geschützt hinterlegen; Verlust kann alle Sicherungen unbrauchbar machen. |

Secrets/Env und private CA gehören in eine **getrennte verschlüsselte** Sicherung mit eigenem Wiederherstellungsschlüssel und Zugriffsnachweis. Nicht in `BACKUP_ROOT/sets`, Reports oder Logdateien ablegen. Betreiber wählt beispielsweise verschlüsselten Offline-Datenträger oder ein geschütztes verschlüsseltes Repository; kein kostenpflichtiger Dienst ist nötig.

## Isolierter Recovery-Workflow

In eigener Testumgebung mit eigenen Volumes, ohne Produktionsverbindungen: verschlüsselte Secrets-Sicherung entschlüsseln, Zugriffsschutz prüfen, Datenbank/Object Store restaurieren, originalen TOTP-Key und originalen CA-Zustand einsetzen, nur öffentliche CA exportieren. TOTP-Login eines ausdrücklich genehmigten Testkontos, Sessionverhalten, Client-TLS, API→MinIO-TLS und Vergleich der CA-Fingerprints prüfen. Negative Probe mit falschem Key muss scheitern. Danach Testumgebung und temporäre Klartextdateien kontrolliert entfernen, keine Keys protokollieren. Für echte Produktionssecrets ist vorher separate Operatorfreigabe nötig.

`APP_ENV=test python -m scripts.secret_recovery_drill` prüft nur den synthetischen verschlüsselten TOTP-Key-Vertrag und falschen Key. Es liest keine Betreibersecrets und ist **kein** Nachweis der echten CA-/Client-/Konten-Recovery. SECRET_RECOVERY_VERIFIED bleibt bis zum vollständigen protokollierten Zieltest offen. Kein wirklicher Schlüssel wurde im PR3-Auftrag rotiert.
