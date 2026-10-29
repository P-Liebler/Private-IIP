# PR10B – Zielbetrieb und Recovery-Abnahme

Stand **29.10.2026**. **TARGET_NOT_AVAILABLE / PREPARED_NOT_DEPLOYED /
NOT_APPROVED**.

Der Nutzer hat zuvor bestätigt, dass noch kein Zielhost bereitsteht. Die
gewünschte zusätzliche Bereitstellung ist **Red Hat OpenShift GitOps mit
Argo CD Applications**. Das bestätigt die unterstützte Bereitstellungsart;
ein tatsächlich zugänglicher Cluster oder eine produktive Zielentscheidung
wurde damit nicht bereitgestellt. In PR10B wurden weder ein Zielhost erfunden
noch Clusterzugriff, Sync, Apply, Cutover oder Produktivinstallation ausgeführt.

## 1. Primären Zielbetrieb vor dem Cutover entscheiden

| Weg | Gegenwärtiger Zustand | Entscheidung |
| --- | --- | --- |
| Docker Compose | Bisher lokal geprüfter Corepfad mit vorhandener geführter Installation und Backupengine | Als technische Referenz erhalten; kein als verfügbar bestätigter Produktivhost |
| OpenShift / Argo CD | Separater vorbereiteter Zielvertrag, Overlays, beschränkte RBAC, TLS-/Storage-/Backupentwürfe | Erhalten; keine tatsächliche Clusterabnahme und kein gemeinsames Release aus Compose-Evidenz |

Für den ersten realen Betrieb wird genau **ein** tatsächlich verfügbarer und
vom Operator bestätigter Weg priorisiert. Ohne diese Entscheidung entstehen
keine weiteren Plattformabstraktionen. Die weiterhin fehlenden Betreiberangaben
sind unten konkret benannt; es wird keine erneute Nachfrage nach bereits
beantworteter Hostverfügbarkeit gestellt.

## 2. Vorhandene technische Vorbereitung

Die datierten [PR9-Installationsnachweise](PR9B_INSTALLATION_READINESS_REPORT.md)
und die [OpenShift-Vorbereitungsabnahme](OPENSHIFT_GITOPS_ACCEPTANCE_REPORT.md)
bleiben unverändert erhalten. Dazu gehören lokale Preflights, geschützt
abgelegte synthetische Konfiguration, erfolgreiche isolierte Restores und
Arbitrary-UID-/Kustomize-Prüfungen. Sie sind **keine** Messungen auf einem
neuen Zielhost und keine PR10-Produktionsfreigabe.

Vorhandene ausführbare Werkzeuge:

- [`ops/core_preflight.py`](../ops/core_preflight.py): read-only Prüfung von
  Konfiguration, lokalen Images, Speicher-/Pfadrechten und Scope.
- [`ops/core_install_plan.py`](../ops/core_install_plan.py): konsistente
  digestgebundene Kommandoliste ohne Apply-/Startfunktion; bindet maximal
  24 Stunden alten Preflight, private Konfigurationsbytes, S3-Identität und
  die öffentlichen Configdateien.
- [`ops/backup.py`](../ops/backup.py) und
  [`ops/restore_verify.py`](../ops/restore_verify.py): bestehende SQL-/S3-/Hash-
  und isolierte Restoreverträge; kein Ersatz durch eine PVC-Dateikopie.
- [`ops/openshift/preflight.py`](../ops/openshift/preflight.py): ausschließlich
  Offlineprüfung, auch bei gültigem Draft bewusst Exitcode 2 und
  `DRAFT_NOT_DEPLOYABLE`.
- [`ops/openshift_backup.py`](../ops/openshift_backup.py): optionaler expliziter
  Transport derselben Backupengine; exakte Namespace-/Pod-/Runtimebindung,
  stillstehende Writer und gehaltene Lease bleiben erforderlich.
- [`ops/record_host_check.py`](../ops/record_host_check.py): private
  append-only Operatoraussage mit Manifest-/Evidenzhash; erzeugt ausdrücklich
  keine Host- oder Releasefreigabe.

Anleitungen: [Core-Installation](operations/PRIVATE_CORE_INSTALLATION.md),
[OpenShift/GitOps](operations/OPENSHIFT_ARGOCD.md),
[Backupbetrieb](operations/BACKUP_SETUP.md),
[Secretverwaltung](operations/SECRET_MANAGEMENT.md),
[TLS-Vertrauen](operations/TLS_CA_TRUST.md).

Die aktuelle PR10-Compose-Härtung setzt Caddy und den getrennten CA-Export auf
UID 10001 und interne HTTP-/HTTPS-Ports 8080/8443. Der interne S3-TLS-Port 9002
und der Anwendungsorigin bleiben erhalten. Eine begrenzte Initialisierung darf
nur ein neues leeres CA-Exportziel vorbereiten. Bereits von Root erzeugte CA-/
Datenvolumes benötigen eine tatsächliche Operatorprüfung und gegebenenfalls
geprüfte Kopie in neue Volumes; keine rekursive implizite Rechte-Reparatur.
Dies ist nicht die Freigabe eines festen UID-Vertrags für OpenShift.
Der getrennte lokale Canary ist ein technischer Teilbeleg. Die abschließenden
[lokalen Regressionen](security/pr10-20261029/regression-final.json) bestehen
mit 321 Tests je Backendbuild. Der frische Core erfüllt alle acht Prüfbereiche;
beide getrennten vollständigen Restores prüfen je 1’387 Dateien und bestätigen
die Bereinigung. Der [neue Preflight](security/pr10-20261029/core-preflight-final.json)
meldet `TECHNICAL_CONFIGURATION_VALID / SECURITY_BLOCKED / NOT_APPROVED`;
der [Installationsplan](security/pr10-20261029/core-install-plan.json) ist
konsistent und hat keine Dienste gestartet. Dies bleibt lokale synthetische
Evidenz, keine Zielhost- oder unabhängige Recoveryabnahme.

**Neue Builds benötigen eigene Evidenz.** PR10-Code-/Configänderungen machen
das alte PR9-Manifest nicht zu einem neuen gültigen Release. Die alten
Anleitungsbeispiele mit PR9-Dateinamen sind historische Referenzen; vor einer
späteren Ausführung sind der tatsächlich freigegebene abschließende Scope,
Inventar, neue Configbytes und das dazugehörige Manifest zu verwenden. Ein
geändertes oder abgelaufenes Manifest/Preflight ist erneut zu prüfen und
nicht durch manuelles Ändern alter Hashes zu retten.

## 3. Exakt fehlende Betreiberangaben

Diese Angaben werden privat dokumentiert. Passwörter und Schlüssel gehören
nicht in Antworten, Tickets, Belege oder Git.

| Bereich | Benötigte tatsächliche Angaben / Nachweise |
| --- | --- |
| Primärziel | Compose oder OpenShift, verantwortlicher Operator und autorisierter Staging-/Produktionsscope |
| Host / Zugang | Betriebssystem, tatsächlicher administrativer Zugriffsweg, private VPN-Adresse und DNS-Name; getrennte Stagingidentität |
| OpenShift zusätzlich | Erreichbarer Kontext/API-Server, Cluster-/GitOps-Operator-/Argo-CD-Version, Namespace, eingeschränkter Controller-ServiceAccount und effektive RBAC |
| Images | Private Registry, zugelassener Push-/Pullweg, echte Mirror-Digests/Plattformmanifest, vollständiges finales Imageinventar einschließlich Backup/Recovery |
| Persistenz | Neue DB-/S3-/Queue-/CA-Volumes; bei OpenShift StorageClass/CSI, Kapazität, Reclaimpolicy, UID-/SELinux-/fsGroup-Verhalten und PVCschutz |
| Zugriff / TLS | Tatsächliches VPN und privater DNS, private Route/Ingress falls OpenShift, gültige CA-Kette, Rotation und freigegebene Netzwerkgrenzen |
| Secrets | Externe geschützte Ablage, Rollen/Dienstkonto, separate Sicherung und Rotation; kein Secret im Application-Repository |
| Recovery | Wirklich unabhängiges physisches **oder** administrativ getrenntes Ziel, nachgewiesene At-rest-Verschlüsselung, getrennt verwahrte Recovery-Schlüssel und isolierte Restoreumgebung |
| Betrieb | Tageszeitplan/Dienstkonto, Retention, gemessenes Archivwachstum, freie Kapazität, Alarmempfänger und verifizierter Empfang |
| Clients | Tatsächlicher Windows-Browser und echtes Android-Gerät mit VPN/CA-Vertrauen; reine Viewportemulation genügt nicht |
| Freigaben | Getrennte Security-, Zielbetriebs-, Recovery-, Migrations-/Rollback- und Operatorentscheidung zum exakten unveränderlichen Manifest |

Ein öffentliches Dashboard oder ein grüner Argo-Sync erfüllt weder diese
Angaben noch die Freigaben. Quellen-/Modell-/Strategiegates bleiben unabhängig.

## 4. Abnahmefolge auf dem später tatsächlich vorhandenen Ziel

### Gemeinsame Voraussetzungen

1. Finale gescannte digestgebundene Images und das zugehörige gültige Manifest
   bereitstellen. Offene Sicherheitsbefunde nach bestehender Policy beheben
   oder durch eine tatsächlich autorisierte befristete Entscheidung bewerten.
2. Neue getrennte Stagingprojekte/-Namespaces/-Volumes und private Secrets
   vorbereiten. Vorhandene echte Originale erst nach Security-/Umgebungs-/
   Backupfreigabe aufnehmen. Collection und Forward-Scheduling bleiben aus.
3. Konfiguration und Netzwerkzugang auf dem echten Ziel read-only prüfen;
   private Konfiguration/Identitäten per Hash an die Abnahme binden.
4. Nur die tatsächlich genehmigten Stagingschritte ausführen. Alembic und
   Cutover sind eigene manuelle Entscheidungen; keine automatische Promotion.

### Falls Compose priorisiert wird

Den vorhandenen Preflight und Installationsplan auf dem **Ziel** mit neuen
privaten Belegpfaden erzeugen. Erst nach tatsächlichen getrennten Freigaben
die ausgewiesenen digestgebundenen Kommandos ausführen: neue Volumes,
Infrastruktur, authentifizierter PostgreSQL-TCP-`SELECT 1`, separater
erfolgreicher CA-Export, freigegebene Migration, anschließend explizite
Core-Runtimes. `--no-build --pull never` und exakte Digests bleiben Pflicht.
Kein optionaler ML-/LLM-Dienst wird durch diesen Ablauf freigegeben.

### Falls OpenShift tatsächlich bestätigt und zugänglich wird

Den vollständigen vorhandenen GitOps-Ablauf auf den realen Cluster prüfen:

1. Tatsächliche Operator-/Argo-Version, Namespace und effektive Controller-RBAC
   erfassen; keine Namespaceadmin-/SCC-Erweiterung aus einem Label ableiten.
2. Echte Registry-/Commit-/Configwerte einsetzen und gerenderte Zielressourcen
   prüfen. Lokaler Kustomize-Render bleibt separat; anschließend einen
   **tatsächlichen serverseitigen Cluster-Dry-Run** dokumentieren.
3. Restricted SCC/Admission und echte zugewiesene UID/Gruppen, CSI/PVC,
   SELinux/fsGroup, Persistenz nach Podersatz, Secretmounts und privaten
   Service-CA-/Route-/NetworkPolicy-Pfad prüfen. Keine `anyuid`-, privilegierte
   oder Root-Init-Ausnahme.
4. Nur genehmigte Infrastruktur über dieselbe Application manuell
   synchronisieren; Alembic separat manuell ausführen; erst dann den
   vollständigen Overlaypfad synchronisieren. Keine zwei Applications auf
   denselben Ressourcen, keine automatischen Migrationshooks und kein
   automatisches Prune/Delete von PVCs.
5. API, Web, PostgreSQL, SeaweedFS, Worker und Scheduler auf dem Cluster
   nachweisen; Rollout, Podersatz und datenerhaltenden Rollback mit exakten
   Digests prüfen. Keine Finanzjobs oder Quellenegressregel still aktivieren.
6. Vollständiges quiesziertes Backup mit gehaltener Lease und bewerteter
   Writerinventur, isolierten DB-/S3-Restore, Alarmempfang und Schlüsselrecovery
   tatsächlich durchführen. Der lokale optionale Transporttest ersetzt dies
   nicht.

## 5. Unabhängiger Backup-/Recoveryvertrag

Der vorhandene geschützte C:-Stagingordner ist **nicht** unabhängig. Seine
früheren Platz-/ACL-Prüfungen beweisen keine At-rest-Verschlüsselung, getrennte
Schlüsselverwahrung oder externe Recoveryfähigkeit. Neue Speicherwerte sind
Zeitpunktmessungen; synthetisches Wachstum ist kein realer Depotbedarf.

Die tatsächliche Abnahme umfasst:

- unabhängiges Ziel und dessen unverwechselbare Identität; kein stiller lokaler
  Fallback bei fehlendem Mount/Ziel;
- nachgewiesene aktive Verschlüsselung und getrennte Recovery-Schlüssel;
- Tagesjob unter realem Dienstkonto, Retention und ausreichend Kapazität auf
  Basis tatsächlicher Vollsätze/Archivgrößen;
- Überwachung fehlgeschlagener und verpasster Läufe, Platz-/Restorealter sowie
  **tatsächlichen Alarmempfang**, nicht nur ein Firing im Monitoring;
- quieszierten konsistenten SQL-/S3-/Archivsatz und alle verifizierten
  Dateihashes; getrennte Secrets-/CA-/TOTP-Recovery;
- vollständigen Restore vom unabhängigen Ziel in neuen isolierten Volumes,
  ursprüngliche Archivhashes, historischen CHF-10’180-Stichtag und weiterhin
  explizites `STALE_PRICE` für heute veraltete Daten;
- gemessene Recoveryzeit/-verlustgrenze, echten Neustart und erneute
  erfolgreiche Sicherung. Keine nicht gemessene RPO/RTO-Zusage.

Der implementierte Windows-Zielguard prüft den konkreten privaten
BitLocker-/anderen-physische-Disk-Vertrag. Er bestätigt nicht automatisch die
Verschlüsselung oder administrative Trennung eines NAS-/Cloud-/Linux-Ziels.
Ein abweichender tatsächlicher Recoveryweg benötigt seinen eigenen
nachgewiesenen zulässigen Zielvertrag; bis dahin bleibt das Gate offen.

## 6. Tatsächliche Client- und Betriebsmatrix

Die zwölf vorhandenen Schritt-IDs für private Operatorbelege bleiben nutzbar.
Ohne Ziel sind alle folgenden **TARGET_NOT_AVAILABLE**, nicht fehlgeschlagene
oder bestandene Zieltests:

| Schritt | Eindeutige Abnahme auf dem echten Ziel |
| --- | --- |
| `private_hostname`, `dns` | Erwartete private Auflösung auf Windows und Android, kein öffentlicher Ersatz |
| `vpn` | Anwendung im freigegebenen VPN erreichbar, außerhalb nicht erreichbar |
| `tls_ca` | Echte Browser ohne Warnung; richtiger CA-Fingerprint, falsche CA scheitert; keine deaktivierte Verifikation |
| `windows_client`, `android_client` | Login, Portfolio, Instrument, Import und mobile Navigation auf tatsächlichen Geräten |
| `login_totp` | Eigener Benutzer, TOTP-Fehlversuch, Logout und Sessionwiderruf, keine Tokens/Seeds im Protokoll |
| `backup` | Vollsatz plus fehlendes-Ziel-/Verschlüsselungs-/Zeitplan-Negativprobe ohne Fallback |
| `restore` | Alle ursprünglichen SQL-/S3-/Archivhashverträge in isolierter Infrastruktur und historische Goldenbewertung |
| `secrets_recovery` | DB/S3, ursprünglicher TOTP-Key und CA aus getrenntem verschlüsseltem Backup, falscher Key scheitert |
| `alert_delivery` | Kontrollierter Dienstausfall, Backupfehler und verpasster Lauf mit bestätigtem Alarmempfang und Behebung |
| `host_reboot` | Echter Hostneustart bzw. vereinbarte Cluster-Recoveryprobe; danach Persistenz, Auth, Queue und Tagesbackup |

Jeder Beleg ist eine neue private append-only Aussage zu einem exakten
Manifest; tatsächliche Evidenz und Reviewerentscheidung bleiben erforderlich.
Ein Helper mit `operator_result=PASS` beweist allein keine erfolgreiche Prüfung.
Rollback stoppt Writer, sichert neue Originale und klärt Deltas; kein
`down -v`, kein PVC-Prune und kein automatisches Datenbankdowngrade.

## 7. Ergebnis

`TARGET_DEPLOYED`: **Nein**. `SECURITY_APPROVED`: **nicht durch PR10B erteilt**.
`PRIVATE_CORE_V1_RELEASED`: **Nein**.

Die spätere Installation und Abnahme sind ausführbar vorbereitet. Der fehlende
reale Zielhost/-cluster, die primäre Operatorwahl, unabhängiger verschlüsselter
Recoverybetrieb und tatsächliche Geräte-/Betriebsprüfungen bleiben exakt
benannte externe Voraussetzungen. Ein lokales synthetisches Deployment wird
nicht als erster realer privater Betrieb umetikettiert.
