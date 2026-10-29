# PR11C – Private Core V1: Installation und Operatorübergabe

Stand **29.10.2026**. **TARGET_NOT_AVAILABLE / PREPARED_NOT_DEPLOYED /
NOT_APPROVED**. Der Nutzer hat lokale Vorbereitung autorisiert; ein Zielhost
oder erreichbarer OpenShift-Cluster steht weiterhin nicht zur Verfügung.
Red Hat OpenShift GitOps / Argo CD Applications ist der gewünschte zusätzliche
Bereitstellungsweg. Das ist noch keine Ziel- oder Installationsfreigabe.

## 1. Technische Nachweise richtig verwenden

Die [PR10-Zielabnahme](PR10B_TARGET_ACCEPTANCE_REPORT.md) und der
[PR10-Regressionsbeleg](security/pr10-20261029/regression-final.json) bleiben
historische Evidenz: 321 Backendtests je geprüftem Image, 192 Hosttests,
31 Browserfälle sowie zwei isolierte synthetische Restores mit je 1’387
Dateihashes. Sie werden nicht als neue PR11-Läufe bezeichnet. Die aktuellen
PR11-Ergebnisse und das tatsächlich benötigte Recoveryinventar gehören in den
[Gesamtbericht](PR11_ACCEPTANCE_REPORT.md) und das
[Securityreview](PR11_SECURITY_FINAL_REVIEW.md). Geänderte Images oder
Verträge benötigen ihre eigene Evidenz.

Weiterhin dieselben Werkzeuge verwenden:

| Werkzeug | Verbindlicher Umfang |
| --- | --- |
| [`core_preflight.py`](../ops/core_preflight.py) | Konfiguration, exakte lokale Images, Scope und geschützte Pfade lesen; kein Start und keine Hostfreigabe |
| [`core_install_plan.py`](../ops/core_install_plan.py) | Konkrete digestgebundene Reihenfolge ausgeben; Preflight höchstens 24 Stunden alt, unveränderte Config-/S3-/Scope-/Inventarbytes; keine Applyfunktion |
| [`backup.py`](../ops/backup.py), [`restore_verify.py`](../ops/restore_verify.py) | Bestehende SQL-/S3-/Original-/Archivverträge; isolierter Restore und explizite Writerquieszenz |
| [`openshift/preflight.py`](../ops/openshift/preflight.py) | Offlineprüfung des vorbereiteten Clustervertrags; auch ohne Draftfehler `DRAFT_NOT_DEPLOYABLE` mit Exitcode 2 |
| [`openshift_backup.py`](../ops/openshift_backup.py) | Expliziter Transport der bestehenden Backupengine bei exakten Pod-/Runtimebindungen und während der gesamten Operation gehaltener Lease |

Ein lokales synthetisches Projekt ist kein reales Ziel. Ein grüner Argo-Sync,
ein lokaler Arbitrary-UID-Test und Compose-Evidenz autorisieren keinen
Clustereinsatz. Quellen-, Modell- und Strategieentscheidungen bleiben getrennt.

## 2. Konkrete noch erforderliche Operatorübergabe

Aktuelle lokale PR11-Belege: [Preflight](security/pr11-20261029/core-preflight-final.json)
und [Installationsplan](security/pr11-20261029/core-install-plan.json) sind
technisch konsistent, **SECURITY_BLOCKED / NOT_APPROVED**, ohne Dienste zu
starten. Der Scope V2 umfasst zwölf notwendige Dienste und acht unveränderte
Images; beide neuen vollständigen Archivrestores bestehen mit je 1’387 Dateien,
1’378 S3-Readbackobjekten und 66 Pins ohne historischen Python-Prozess.
[Regression](security/pr11-20261029/regression-final.json) und
[Offline-OpenShiftprüfung](security/pr11-20261029/openshift-offline-preflight.json)
bleiben lokale Nachweise. Reale Infrastruktur und unabhängige Recovery sind
weiterhin nicht vorhanden oder abgenommen.

Alle Angaben und Belege werden privat gehalten. Keine Passwörter, Schlüssel,
Tokens, TOTP-Seeds, Finanzoriginale oder Cluster-Secretinhalte in Git/CI oder
öffentliche Abnahmeberichte aufnehmen.

| Entscheidung | Erforderliche Handlung | Autorisierung | Geschützte Eingaben | Überprüfbarer Erfolg | Bis dahin gesperrt |
| --- | --- | --- | --- | --- | --- |
| Tatsächliches Primärziel | Genau einen vorhandenen Composehost oder OpenShift-Namespace priorisieren und dessen Staging-/Produktionsgrenze dokumentieren | Verantwortlicher Betreiber | OS/Clusterkontext, privater Zugang, tatsächlicher VPN-/DNS-Name, Operatorrollen | Ziel ist mit vereinbartem privaten Zugriff tatsächlich erreichbar; getrenntes Staging vorhanden | Zielinstallation, Migration, Cutover |
| Security und exaktes Release | Vollständigen aktuellen Core-/Recovery-Scope, SBOMs und offene Befunde aus PR11 getrennt entscheiden | Autorisierter Securityreviewer und Releaseoperator | Unveränderliches Manifest, tatsächliche Risikobelege, private Registry-/Mirrorbelege | Manifest-/Config-/Imagedigests stimmen überein; erforderliche echte Entscheidungen gültig | `SECURITY_APPROVED`, Produktionsstart |
| Netzwerk und TLS | VPN, privates DNS, private Route/Ingress sowie CA-Vertrauen und Rotation am echten Ziel prüfen | Netzwerk-/Zielbetreiber | VPN-/DNS-Konfiguration, CA-Schlüssel geschützt, öffentliche CA-Fingerprints | Windows und Android erreichen nur den freigegebenen privaten Pfad; korrekte CA ohne Warnung, falsche CA scheitert | Öffentliche Freigabe und echte Clientabnahme |
| Secrets und Persistenz | Externe Secretablage, getrennte Recovery und neue isolierte Volumes bereitstellen; beim Cluster CSI/StorageClass/UID/Gruppen/SELinux prüfen | Ziel-/Secretbetreiber | DB-/S3-/TOTP-Schlüssel, Secretidentitäten, Storage- und Kapazitätswerte | Keine Secrets im Git; Persistenz nach tatsächlichem Neustart/Podersatz; begrenzte Rechte | Aufnahme echter Originale |
| Unabhängige Recovery | Physisch oder administrativ getrenntes verschlüsseltes Ziel und getrennte Schlüssel bereitstellen; Vollsatz isoliert restaurieren | Backup-/Recoveryverantwortlicher | Echte Zielidentität, Dienstkonto, Verschlüsselungs- und Schlüsselbelege | SQL, Raw-Objekte, Archivhashes, Login/TOTP und ursprüngliche Stichtagsbewertung geprüft; tatsächliche RPO/RTO gemessen | `INDEPENDENT_ENCRYPTED_RECOVERY_VERIFIED` und echter Pilot |
| Regelbetrieb | Tagesbackup, Retention, gemessenes Wachstum, Monitoring und Alarmempfänger festlegen; Fehler/verpassten Lauf kontrolliert auslösen | Betriebsverantwortlicher | Dienstkonto, Alarmziel und private Zeitplan-/Retentionbelege | Tatsächlich ausgeführte Tagesjobs, empfangene Alarme und erfolgreiche Behebung; kein lokaler Fallback bei fehlendem Backupziel | Behauptung dauerhafter Betriebssicherheit |
| Migration und Rollback | Installationsplan am echten Ziel neu erzeugen, Writergrenzen und datenerhaltenden Rückweg prüfen | Gesonderte Migrations-/Cutoverfreigabe des Betreibers | Gültiger Zielpreflight, Config-/Manifesthashes, überprüfter Recoverybestand und Deltaliste | Freigegebene Alembic-Migration, Neustart und Rollbackprobe mit erhaltenen Originalen | Produktive Migration, Sync/Apply und Cutover |

Der vorhandene geschützte C:-Stagingordner ist kein unabhängiges Recoveryziel.
Eine ACL ist kein Verschlüsselungsnachweis. Der bestehende Windows-Zielguard
beweist ausschließlich seinen konkreten BitLocker-/anderen-Disk-Vertrag;
ein tatsächlicher anderer Zieltyp benötigt nachgewiesene Zielbedingungen.

## 3. Ausführung nach tatsächlicher Ziel- und Stagingfreigabe

### Compose

Die [bestehende Installationsanleitung](operations/PRIVATE_CORE_INSTALLATION.md)
benutzen. Preflight und Plan mit dem **finalen** Scope, Inventar, Manifest und
privaten Zielinputs neu erzeugen. Alte datierte Planbeispiele sind keine
aktuelle Startanweisung. Nur separat freigegebene Schritte ausführen:
isolierte neue Volumes, Infrastruktur und authentifizierter PostgreSQL-Test,
erfolgreicher CA-Export, ausdrücklich genehmigte Alembic-Migration und danach
Core-Runtimes mit exakten Digests, `--no-build --pull never`.

Collection, Forward-SHADOW und optionale ML-/LLM-Dienste bleiben aus, sofern
keine eigene gültige Freigabe vorliegt. Neue Caddy-Volumes und UID-/Portvertrag
prüfen; alte nichtleere Root-CA-Volumes nicht automatisch rekursiv umschreiben.

### Red Hat OpenShift GitOps / Argo CD

Die [vorhandene GitOps-Anleitung](operations/OPENSHIFT_ARGOCD.md) verwenden:
tatsächliche Operator-/Argo-Version, Namespace, Controller-RBAC, Registry und
gerenderte Zielwerte prüfen, danach echten serverseitigen Dry-Run. Restricted
SCC, namespacezugewiesene UID/Gruppen, Service-CA/Route, NetworkPolicy und
PVC-/CSI-Persistenz auf dem Cluster nachweisen. Keine `anyuid`-/Root-Init- oder
privilegierte Ausweichkonfiguration.

Manueller Infrastruktur-Sync, separat genehmigte manuelle Migration und erst
danach Runtime-Sync derselben Application bleiben getrennte Schritte. Keine
automatischen Migrationshooks, zweite Application auf denselben Ressourcen
oder PVC-Prune/-Delete. Backuptransport setzt Writerinventur, Quieszenz und
gehaltene Lease voraus; Offlinechecks ersetzen keine Cluster-Recoveryprobe.

## 4. Abnahme und Stop

Jede reale Abnahme bindet Manifest, Ziel, UTC-Zeit, tatsächliche Evidenz und
Reviewer. Ein manuell eingetragenes `PASS` allein beweist keine Messung.
Beim Rollback Writer stoppen, neue Originale sichern und Deltas abgleichen;
kein `down -v`, PVC-Prune oder automatisches Datenbankdowngrade.

**`TARGET_DEPLOYED=false`, `PRIVATE_CORE_V1_RELEASED=false`.** Nach Abschluss
der lokal ausführbaren Verträge folgen die oben benannten tatsächlichen
Entscheidungen. Kein weiterer synthetischer Zielaufbau schließt diese Gates.
