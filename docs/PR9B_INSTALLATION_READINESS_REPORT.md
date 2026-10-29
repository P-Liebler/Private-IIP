# PR9B – Installation und Backup-Voraussetzungen

Stand: 29.10.2026. **LOCAL_PREPARATION / TARGET_HOST_NOT_VERIFIED / NOT_APPROVED.**

## Technisch ergänzt

- Backup-CLI und geschützte Environmentdatei müssen denselben Root benennen,
  bevor ein Dateischreibzugriff oder Compose-Aufruf möglich ist. Ein geänderter
  privater S3-Identitätshash oder eine der fünf öffentlichen Configdateien
  macht einen alten Installations-Preflight unbrauchbar; Negativfälle sind geprüft.
- [OpenShift/GitOps](OPENSHIFT_GITOPS_ACCEPTANCE_REPORT.md) ist als separates
  Ziel vorbereitet. Der optionale `oc`-Transport verwendet denselben Backupmotor
  und hat keine automatische Cluster- oder Recoveryfreigabe.

- Der read-only Core-Preflight prüft zusätzlich absolute sichere Backup-/Konfigurationspfade, Symlinks und Windows-Reparsepoints, tatsächliche NTFS-ACL bzw. POSIX-Rechte und eigene nicht externe Projektvolumes. Produktion darf nicht in das Checkout sichern. Der Bericht bindet Modus, Zeitpunkt und Konfigurationsbytes.
- `ops/core_storage.py` misst reale Dateibytes und erfolgreiche volle Sicherungssätze. Die Kapazitätsschätzung nimmt höchstens 17 volle Retentionssätze (7 tägliche + 4 wöchentliche + 6 monatliche), 20 Prozent Reserve und zusätzlich 5 GiB an. Keine unbelegte Kompressions-/Deduplizierungsersparnis. Lokales synthetisches Wachstum beschreibt kein echtes Depotarchiv; unvollständige alte Manifestgrößen werden ausdrücklich aus der Wachstumsschätzung ausgeschlossen.
- `ops/core_install_plan.py` bereitet konsistente, digestgebundene Core-Kommandos und Rollbackschritte vor. Kein Apply-Unterbefehl und kein Produktionsstart. Preflight muss höchstens 24 Stunden alt und an dieselben Environment-/Scope-/Inventarbytes gebunden sein. Ein Manifest wird auf unveränderte Source-/Artefaktbytes und exakten Scope geprüft; gültige Bytes sind keine Freigabe.
- Der bestehende Backupmotor bleibt erhalten. Compose-Overlays werden im Windows-Zeitplan unterstützt; Backupaufrufe verwenden die genaue Environmentdatei und verwerfen widersprechende geerbte Variablen, einschließlich Overlayvariablen. Der zusätzliche optionale Windows-Zielguard verweigert Backups vor jedem Dateischreibzugriff, wenn Zielidentität, privater ACL-Vertrag, anderes physisches Laufwerk als Systemdisk oder vollständig aktive BitLocker-Verschlüsselung nicht nachweisbar sind. Die Beispielpolicy ist **NOT_APPROVED**. Keine Verschlüsselung wurde vorgetäuscht oder eingeschaltet.
- Ein zwölfteiliger Zielhostablauf und private append-only Operatorbelege mit Manifest-/Evidenzhash stehen bereit. Der Beleghelfer erteilt keine Freigabe.

## Tatsächlicher lokaler Speicher

Ein neuer dedizierter Stagingpfad auf dem bereits vom Nutzer autorisierten C:-Laufwerk wurde vorbereitet: `C:\Users\liebler\Private-IIP-Local-Staging-Backups`. Neu gesetzte ACL: aktueller Benutzer, SYSTEM und Administratoren; breite Vererbung entfernt. Die separate synthetische Konfiguration liegt außerhalb des Checkout in `C:\Users\liebler\Private-IIP-Local-Staging-Config`. Bestehende Originalkonfigurationen und Docker-Volumes wurden nicht verändert.

Die [tatsächliche Speichermessung](security/pr9-20261028/backup-storage-measurement.json) erfasste **22’214’991’321 Bytes in 45’154 Dateien** im lokalen `backups`-Baum; dieser enthält auch Scans und technische Evidenz. Der PR8-Core-Backuproot `backups/s8-v1` enthält **20’386’195 Bytes**, drei erfolgreiche Sätze und einen größten vollständigen Satz von **6’535’365 Bytes**. Für diesen kleinen synthetischen Bestand ergeben 17 volle Sätze plus 20 Prozent Reserve und 5 GiB mindestens **5’502’030’566 Bytes**. Mangels unterschiedlicher Beobachtungstage ist tägliches Wachstum **unbekannt**; reale Depot-/Dokument-/Modellbestände benötigen eigene Messung. Alte unvollständige Größenmetadaten werden nicht erfunden.

Am neuen dedizierten Pfad waren bei der Messung **66’625’159’168 Bytes frei**, und die Pfad-/Rechteprüfung ergab keine Fehler. Der anschließend tatsächlich bestandene [read-only Preflight v3](security/pr9-20261028/core-preflight-storage-v3.json) meldet **62’833’876’992 Bytes frei**, **16’579’248’128 Bytes Docker-RAM** und `configuration_errors=[]`: **TECHNICAL_CONFIGURATION_VALID / SECURITY_BLOCKED / NOT_APPROVED**. Dabei wurde der unveränderte PR8-Scope verwendet, um den alten Speicherblocker getrennt zu prüfen. Die ersten beiden Versuche blieben als `PREFLIGHT_INCOMPLETE` erhalten; der zweite dokumentiert einen begrenzten `docker info`-Timeout bei `DOCKER_MEMORY`. Es wurde nichts gestartet.

Der [tatsächlich erzeugte Installationsplan](security/pr9-20261028/core-install-plan-storage-v1.json) ist `CONFIGURATION_PLAN_READY`, führt keine Befehle aus und erteilt keine Freigabe. Das alte RC3-Manifest wird nach PR9-Sourceänderungen korrekt als geändert/ungültig erkannt, anstatt seine frühere Identität umzuschreiben. Der [finale PR9-Preflight](security/pr9-20261028/core-preflight-final-v2.json) bindet denselben 13-Service-Scope, Inventar, private Environmentbytes und alle fünf öffentlichen Configdateien sowie den exakten privaten S3-Identitätshash. **60’639’080’448 freie Bytes**, keine Konfigurations-/Pfad-/Rechtefehler, **TECHNICAL_CONFIGURATION_VALID / SECURITY_BLOCKED / NOT_APPROVED**. Der [finale geführte Plan](security/pr9-20261028/core-install-plan-final-v2.json) ist konsistent und startet nichts. CA-Export wird separat per Exitcode geprüft; PostgreSQL muss authentifiziert über TCP auf seiner tatsächlichen Datenbank bereit sein. Geänderte Configbytes machen einen alten Preflight unbrauchbar.

Dies sind Zeitpunktmessungen; laufende Image-/Scanarbeiten verändern freien Platz. Der neue Pfad ist **LOCAL_STAGING_ONLY**, nicht unabhängig und ohne bestätigte At-rest-Verschlüsselung. Der frühere `BACKUP_FREE_SPACE_BELOW_5_GIB` ist für diesen lokalen Pfad behoben. Damit ist kein Recoverygate geschlossen.

## Ausführbarer Operatorweg

[Geführte Core-Installation und Zielhostprüfung](operations/PRIVATE_CORE_INSTALLATION.md) beschreibt geschützte Konfiguration, Staging-/Produktionsgrenzen, Preflight, exakte Imageverträge, getrennte Freigaben, manuelle Ausführung nach Freigabe und datenerhaltenden Rollback. Es enthält tatsächliche Erfolgskriterien für Hostname, VPN/DNS, Windows/Android, CA, Login/TOTP, Backup/Restore, Schlüssel-Recovery, Alarmempfang und Hostreboot.

[Backupbetrieb](operations/BACKUP_SETUP.md) ergänzt das bestehende Verfahren um Core-Overlay, unabhängiges verschlüsseltes Ziel, Zeitplan, Retention, fehlgeschlagene/verpasste Läufe, Alarmzustellung und tatsächliche Recoveryproben. RPO/RTO bleiben Vorschläge, bis sie auf dem Ziel gemessen wurden. Ein lokales Backup oder automatischer Browserfall ist kein Zielhostnachweis.

## Verbleibende tatsächliche Abnahmen

1. Finaler Scope, Digests/Scans, vollständige Regression und Restore sind im neuen RC gebunden; die tatsächliche getrennte Securityentscheidung bleibt offen.
2. Zielhost, privaten DNS/VPN-Zugang und beide tatsächlichen Clients bereitstellen; dort denselben Preflight ausführen.
3. Physisch und administrativ unabhängiges verschlüsseltes Backupziel sowie getrennt verwahrte Recoverykeys bestimmen. Lokal geschütztes C: erfüllt das nicht.
4. Unter echtem Dienstkonto Tagesjob, Ausfall-/Mountguard, Retention, Speicherüberwachung und Empfang von Fehler-/Überfälligkeitsalarmen nachweisen.
5. Vom unabhängigen Ziel vollständig isoliert restaurieren; Secrets-/CA-/TOTP-/DB-/S3-Recovery und echten Hostreboot abnehmen.
6. Separate Zielhost-/Recovery-/Migrations-/Operatorentscheidungen zum exakten Manifest dokumentieren. Erst danach produktiv starten und anschließend echte private Originale aufnehmen.

## Prüfungen

13 gezielte Hosttests für sichere Pfade/Kapazität, geänderte oder abgelaufene Pläne, private Hostbelege, Environmentisolation, fehlende Operatorentscheidung, fehlerhafte Verschlüsselungsprüfung und unzulässigen Backupdatenträger bestanden. Die endgültige gesamte Hostsuite besteht mit **155 Tests**; [gebundener Regressionsbeleg](security/pr9-20261028/regression-final.json). Ruff für die geänderten PR9B-Pythondateien bestanden. Keine Provideraufrufe und keine echte Infrastrukturabnahme waren Teil dieser Tests.

`BACKUP_STORAGE_STATUS`: **LOCAL_CAPACITY_AND_PERMISSIONS_VERIFIED_FINAL_PR9_SCOPE_PREFLIGHT_VALID**. `INDEPENDENT_RECOVERY_STATUS`: **PENDING_INDEPENDENT_ENCRYPTED_TARGET_AND_OPERATOR_DRILL**. `CORE_DEPLOYMENT_STATUS`: **PREPARED_NOT_INSTALLED_TARGET_HOST_MISSING**.

Der neue vollständige lokale Core-/Backup-/Restorelauf ist bestanden; **1385 Dateihashes**, alte Archivverträge und historische Goldenbewertung erhalten. Dies ersetzt keine unabhängige Recoveryprobe oder Zielhostabnahme. [Endabnahme](PR9E_RELEASE_CANDIDATE_REPORT.md).
