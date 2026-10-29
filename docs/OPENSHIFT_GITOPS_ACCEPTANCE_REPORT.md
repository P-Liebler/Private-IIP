# OpenShift / Red Hat OpenShift GitOps – Vorbereitungsabnahme

Stand **29.10.2026**: **LOCAL_PREPARATION_VERIFIED / CLUSTER_NOT_AVAILABLE /
NOT_APPROVED**. Der Nutzer hat Argo CD Applications über den Red-Hat-Operator
bestätigt. Kein Clusterzugriff, Sync, Apply, Imagepush oder Cutover wurde ausgeführt.

## Implementiert

- Kustomize-Basis für acht Core-Workloads, deaktiviertes Beispiel sowie explizite
  Staging- und Infrastruktur-Overlays. Eine Application verwaltet dieselben
  Ressourcen; Infrastrukturstart, manuelle Migration und vollständiger Start
  sind getrennte Schritte.
- AppProject/Application, eingeschränkte manuelle Controller-RBAC, externe
  Secrets, Service-CA, interne TLS-Endpunkte, private Route als getrenntes
  Beispiel und interne NetworkPolicies mit Default-Deny.
- Keine festen UID/GID-/SCC-Ausnahmen; tokenlose Pods, entfernte Capabilities,
  schreibgeschützte Root-Dateisysteme, getrennte beschreibbare Pfade und neue
  geschützte PVCs. Kein automatisches Prune oder Migrationshook.
- Optionaler `oc`-Transport für den vorhandenen Backupmotor: exakte Laufzeit-
  und Reviewbindung, externe Lease, stillstehende Writer, begrenzte Dump-/Tar-
  Streams, unveränderte Prüfsummen-/Manifest-/Retentionlogik. Separater manueller
  Backup-Client/PVC-Entwurf; kein installierter CronJob oder Restoreerfolg.
- Masterplan Abschnitt 197, ADR-027, Betriebsanleitung und Implementierungsstatus
  ergänzt. Alle **212 nummerierten Hauptabschnitte** und die bestehende Roadmap
  bleiben erhalten. Docker Compose bleibt der bisher geprüfte lokale Zielpfad.

## Tatsächlich geprüft

| Prüfung | Ergebnis und Grenze |
| --- | --- |
| Manifestverträge | **13/13** Offlinefälle; vier echte lokale Kustomize-Render einschließlich optionalem Prometheus, keine übersprungenen Tests |
| Backuptransport | **14/14** Fixturefälle; CLI verwendet den bestehenden Motor ohne Docker-Fallback; fehlende Reviews, aktive Writer/Jobs, Identitätswechsel, Ablauf, unsichere Archive und Größenüberschreitungen scheitern geschlossen |
| Gesamte Hostsuite | **155/155**, einschließlich bestehender Core-/Security-/Restore-/Sourceverträge; [Regressionsbeleg](security/pr9-20261028/regression-final.json) |
| Arbiträre UID | **7/7** tatsächliche unveränderte Images, UID 1000720000/GID 0, read-only, Capabilities entfernt, Netzwerk aus; [Nachweis](security/pr9-20261028/openshift-uid-probes-final.json) |
| Tatsächlicher S3-Client-Tar | Einfacher BusyBox-Header und exakte synthetische Bytes durch den begrenzten Parser geprüft; [Beleg](security/pr9-20261028/openshift-mc-tar.json) |
| Draft-Preflight | `OFFLINE_CONTRACTS_VALID`, erwarteter Exitcode **2**, weiterhin `DRAFT_NOT_DEPLOYABLE`; [Dateihashes](security/pr9-20261028/openshift-offline-preflight.json) |
| Cluster / SCC / CSI / GitOps / TLS | **Nicht geprüft**; lokal kein `oc`, kein Zielcluster und keine tatsächliche Admission-/Service-CA-/Route-/Controllerabnahme |
| Clusterbackup / Restore / Alarmierung | **Nicht ausgeführt**; unabhängiges verschlüsseltes Ziel, Statusübergabe, Zeitplan, Retention, Schlüsselrecovery und isolierter Restore bleiben offen |

Die ersten UID-Proben scheiterten an unvollständigen Testsettings, einem
abweichenden Testport und falscher Test-Caddyfile-Syntax. Korrigierte Proben
bestehen mit unveränderten Images; ursprüngliche Fehlerbelege bleiben erhalten.
Der erste tatsächliche Client-Tar-Test fand einen vom Fixture abweichenden
BusyBox-Header. Der Parser unterstützt dessen einfachen Header jetzt explizit;
Links, Erweiterungen, Traversal und andere verbotene Typen bleiben gesperrt.
Zu lange Namen oder nicht passende Transfergrenzen erzeugen einen Fehler,
keinen unvollständigen Backup-Erfolg.

## Vor echter Bereitstellung erforderlich

1. Tatsächlichen privaten Cluster, Operator-/Argo-CD-Version, eingeschränkten
   Controllerscope und private Registry bestimmen; unveränderliche Commit- und
   Imagedigests sowie vollständige gerenderte Zielkonfiguration reviewen.
2. Bestehende [PR9-Sicherheitsblocker](PR9A_SECURITY_CLOSURE_REPORT.md) entscheiden.
   Ein Compose-RC oder erfolgreicher Render genehmigt keine OpenShift-Installation.
3. Neue CSI-Volumes, UID-/SELinux-/fsGroup-Rechte, SCC-Zulassung, Persistenz über
   Podersatz, externe Secrets, Service-CA/Rotation und privaten Zugriff prüfen.
4. Infrastruktur manuell synchronisieren, Alembic separat ausführen und erst
   anschließend dieselbe Application auf den vollständigen Overlaypfad setzen.
5. Authentifiziertes S3, vollständiges quiesziertes Backup, unabhängigen Restore,
   Alarmempfang und Schlüsselrecovery tatsächlich testen. Kein laufendes
   PostgreSQL-PVC als konsistentes Backup ausgeben.
6. Getrennte Cluster-/Security-/Operatorfreigabe dokumentieren. Quellen-, Modell-
   und Strategiegates bleiben unabhängig; Collection und Forward-Scheduling aus.

[Konkrete Dateien und Operatorablauf](operations/OPENSHIFT_ARGOCD.md),
[Architekturentscheidung](decisions/ADR-027-openshift-gitops.md),
[PR9-Gesamtstatus](PR9_ACCEPTANCE_REPORT.md).
