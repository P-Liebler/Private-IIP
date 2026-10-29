# OpenShift mit Red Hat OpenShift GitOps

Stand: 2026-10-29. **DRAFT / NOT_APPROVED.** Zusätzliches Ziel für denselben
Private-Core-Stack; keine neue Finanz-, Quellen-, Modell- oder Backupengine.
Der Nutzer hat Red Hat OpenShift GitOps mit Argo CD Applications bestätigt.
Ein Zielcluster steht noch nicht zur Verfügung. Ein erfolgreicher Offline-Render
belegt weder SCC-Zulassung noch einen erfolgreichen Start oder eine Freigabe.

Die unveränderten fachlichen Zustände bleiben `REAL_DATA_LIMITED`,
`FORECASTS_SHADOW_ONLY` und `RECOMMENDATIONS_GATED`. PR9-Sicherheit und
Zielbetrieb benötigen ihre getrennten Entscheidungen. Die in PR11 unverändert übernommenen PR10-Core-Digests bilden
eine technische Ausgangsbasis, keine OpenShift-Freigabe; insbesondere bestehende
Recovery- und Caddy-Befunde dürfen durch dieses zusätzliche Ziel nicht entfallen.

PR11 trennt den optionalen historischen Python-Prozess über
[ADR-029](../decisions/ADR-029-private-core-archive-recovery.md) vom vollständigen
Core-Archivrestore. Die tatsächlichen DB-/S3-/Original-/Archivprüfungen bleiben
erforderlich; geschützte ursprüngliche Metadaten und vorab unabhängig gepinnte
aktuelle Erwartungen werden separat aufbewahrt. Diese lokale Vertragsprüfung
beweist keine Cluster-Recovery oder Freigabe des alten Researchimages.

PR10 ergänzt die terminale Sperre interner Pfade vor dem Frontendproxy und
beschränkt Caddy auf HTTP/1.1 und HTTP/2, weil kein UDP-Zugang bereitgestellt
wird. Das Backend-Draftimage enthält den erneut geprüften ECB-Scopefix.
Die frühere [PR9-Vorbereitungsabnahme](../OPENSHIFT_GITOPS_ACCEPTANCE_REPORT.md)
bleibt mit ihren damaligen Images erhalten; aktuelle getrennte Grenzen und
Zielvoraussetzungen stehen in [PR10B](../PR10B_TARGET_ACCEPTANCE_REPORT.md).
Keine dieser lokalen Änderungen ersetzt einen serverseitigen Cluster-Dry-Run.

## Enthaltene Vorbereitung

| Pfad | Verhalten |
| --- | --- |
| `ops/openshift/base` | API, Celery Worker, einzelner Beat, Next.js, PostgreSQL 17 mit pgvector, Valkey, SeaweedFS unter Dienstname `minio`, Caddy; alle Replikas 0 |
| `ops/openshift/overlays/example` | Renderbare, deaktivierte Basiskonfiguration |
| `ops/openshift/overlays/staging` | Manueller Opt-in mit Replikas 1; unersetzte Registry-, Host-, Storage- und Code-Platzhalter verhindern verwendbare Zielkonfiguration |
| `ops/openshift/overlays/staging-infra` | Dieselben Zielinputs; API/Web/Worker/Beat bleiben 0 für den manuellen Infrastrukturstart vor Alembic |
| `ops/openshift/bootstrap` | Namespace und eingeschränkte GitOps-Rolle/-Bindung; ausschließlich manuell und außerhalb der Application |
| `ops/openshift/manual/migration-job.json` | Separater, suspendierter Alembic Job ohne Sync-Hook, Retry oder automatische Löschung |
| `ops/openshift/manual/backup-agent.json` | Gesonderte Backup-Staging-PVC, tokenloser Clientpod und eng begrenzte S3-NetworkPolicies; außerhalb der Application, ungeprüfter Node-/Storage-/Registry-Platzhalter |
| `ops/openshift/components/prometheus` | Optionaler interner Prometheus; weiterhin Replikas 0, keine Alarmzustellung behauptet |
| `ops/openshift/examples/argocd` | AppProject und Application für den OpenShift-GitOps-Operator; manuelle Synchronisierung, kein AutoSync/Prune |
| `ops/openshift/examples/private-route` | Gesondertes privates Reencrypt-Route-Beispiel mit Platzhaltern; nicht Teil einer Kustomization |

JSON ist hier die YAML-1.2-kompatible Ressourcenserialisierung. Die Offline-Tools
benötigen nur die Python-Standardbibliothek. Es werden keine Secrets mit Werten,
SCCs, privilegierten Pods, festen UIDs/GIDs, HostPath-, NodePort- oder
LoadBalancer-Zugänge erzeugt. MLflow, ML-Worker, Ollama, Grafana, Collection-
und Forward-Automatik bleiben außerhalb des aktiven Ziels. Provider-Egress
ist nicht erlaubt; eine spätere NetworkPolicy ersetzt keine Quellenfreigabe.

## Lokal prüfen

Aus dem Repository-Stamm, ohne Clusterzugriff:

```powershell
kubectl kustomize ops/openshift/overlays/example
kubectl kustomize ops/openshift/overlays/staging
kubectl kustomize ops/openshift/overlays/staging-infra
python ops/openshift/preflight.py
python -m unittest discover -s ops/tests -p test_openshift_manifests.py -v
```

Der Preflight bindet die Vorbereitungsdateien an SHA-256-Werte und endet immer
mit Exitcode **2** / `DRAFT_NOT_DEPLOYABLE`. `OFFLINE_CONTRACTS_VALID` beschreibt
nur die geprüften Draft-Verträge. Es gibt keinen Apply-, Sync-, Start- oder
Freigabebefehl in diesem Werkzeug. Die Kustomize-Render sind keine Server-
Dry-Runs und keine Schema- oder SCC-Abnahme.

Tatsächlich lokal geprüft am 2026-10-29: 13 Manifesttests erfolgreich, ohne
übersprungene Tests; vier echte Render mit lokalem `kubectl v1.36.1` /
`Kustomize v5.8.1` für example, staging, staging-infra und die optionale
Prometheus-Komponente. Der CLI-Preflight lieferte den erwarteten Exitcode 2.
Es gab keinen Clusterzugriff, Apply, Imagebuild oder finanziellen Providerabruf.

Die [lokalen UID-Proben](../security/pr9-20261028/openshift-uid-probes-final.json)
prüfen sieben unveränderte Kandidatenimages mit UID 1000720000/GID 0,
schreibgeschütztem Root-Dateisystem, entfernten Capabilities und ohne Netzwerk:
API/Celery/Nativimporte, Web-Login-SSR, PostgreSQL/pgvector, Valkey, Seaweed,
Caddy und S3-Client. Die ersten drei fehlgeschlagenen Probeaufbauten bleiben
erhalten; korrigierte Testsettings, Port und Caddyfile bestehen. Weder SCC-
Admission noch CSI, Service-CA oder GitOps wurden dadurch am Cluster geprüft.

## Zielkonfiguration vorbereiten

Eine eigene Kopie des Staging-Overlays erstellen und jede Änderung reviewen.
Die Datei `draft-contract.json` kann keine Genehmigungen erteilen. Die endgültige
gerenderte Konfiguration und alle verwendeten Images benötigen ihren eigenen
unveränderlichen Release-/Security-Nachweis nach den bestehenden PR4-/PR9-Regeln.

1. Zielnamespace und GitOps-Instanz festlegen. Das Beispiel verwendet
   `investment-staging` und den Operator-Standardnamespace `openshift-gitops`.
   Namespace im Overlay, im Bootstrap, in Application/AppProject, im manuellen
   Migrationsjob und im TLS-Endpunkt gemeinsam anpassen. Die Basis selbst heißt
   `investment-draft`. Das Staging-Overlay ersetzt den S3-Endpunkt ausdrücklich
   durch `caddy.investment-staging.svc:9002`; Kustomize ersetzt beliebige
   Zeichenketten in ConfigMaps nicht automatisch.
2. Die vorhandenen Images unverändert in eine private erreichbare Registry
   spiegeln. `registry.invalid/...` ist absichtlich nicht auflösbar. Die sechs
   unterschiedlichen Basisimages tragen echte Kandidaten-Digests; geänderte
   Images brauchen neue Scans. Tags allein sind unzulässig. ImagePullSecrets
   werden vom Operator außerhalb dieses Repositorys verwaltet und dem
   tokenlosen `iip-runtime` ServiceAccount im Zielnamespace zugeordnet.
3. `storageClassName` jeder PVC im eigenen Overlay auf eine geprüfte CSI-
   StorageClass patchen. Größen 20 GiB/2 GiB/100 GiB bzw. optional 5 GiB sind
   Planungsbeispiele, keine Kapazitätsmessung. Nur neue Claims verwenden.
   ReclaimPolicy `Retain`, Expansion, Verschlüsselung, Snapshotmöglichkeiten,
   Volume- und Namespace-Löschrechte sowie Kapazität durch den Clusteroperator
   nachweisen. Argo-PVC-Annotationen verhindern keine manuelle Clusterlöschung.
4. Den tatsächlichen privaten HTTPS-Origin in `FRONTEND_ORIGIN` und
   `API_PUBLIC_ORIGIN` gleich setzen; keine Pfade oder abweichenden Ports
   verschweigen. Das Web verwendet `INTERNAL_API_BASE_URL=http://api:8000/api/v1`.
   `NEXT_PUBLIC_API_BASE_URL` ist im Browser-Bundle eingebaut: ein zur Zieladresse
   passendes oder mit `/api/v1` gebautes Webimage verwenden und dessen neue
   Digest-/Security-Evidenz erfassen. Runtime-Env repariert ein falsches Bundle
   nicht. `CODE_COMMIT` muss zum tatsächlich gestarteten Code gehören.
5. Rechte, Secrets und Zertifikate außerhalb Git bereitstellen; anschließend
   die gerenderte exakte Zielkonfiguration und die getrennten Freigaben binden.

## Secrets und interner TLS-Vertrag

`iip-runtime-secrets` wird außerhalb Git erstellt. Die Tabelle nennt ausschließlich
Schlüsselnamen, keine Beispielgeheimnisse:

| Schlüssel | Vertrag |
| --- | --- |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Neu initialisierte PostgreSQL-Instanz; einzigartige starke Zugangsdaten |
| `DATABASE_URL` | Passende `postgresql+asyncpg://`-URL zu `postgres:5432`; Sonderzeichen korrekt URL-kodieren, kein Klartext in Kommandohistorie |
| `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` | Passend zur getrennten S3-Identität, mindestens die Produktionsvalidierung erfüllen |
| `TOTP_ENCRYPTION_KEY` | Tatsächlicher Fernet-Schlüssel mit getrennter verschlüsselter Wiederherstellung |

`iip-s3-identities` enthält `s3.json` nach dem vorhandenen SeaweedFS-
Identitätsvertrag. Nur die benötigten Bucket-/Objektrechte vergeben; die
Anwendung benötigt für ihren bestehenden `ensure_bucket`-Vertrag bei fehlendem
Bucket die entsprechende Erstellberechtigung oder einen vorab erstellten Bucket.
Keine anonymen Identitäten, Fixtures oder Fakewerte einsetzen.

Der Dienst `caddy` fordert mit
`service.beta.openshift.io/serving-cert-secret-name` ein Serving-Zertifikat in
`iip-caddy-serving-cert` an. Caddy liest `/certs/tls.crt` und `/certs/tls.key` und
lauscht ohne Low-Port-Capability auf 8443 und 9002. Die dedizierte ConfigMap
`iip-service-ca` fordert per `service.beta.openshift.io/inject-cabundle` die
Service-CA in `service-ca.crt` an. API, Worker, Beat und Migration prüfen damit
den FQDN `caddy.<namespace>.svc:9002`. `MINIO_SECURE=true` bleibt verbindlich;
kein `--insecure`, kein HTTP-Ersatz und kein Zertifikat nur für den Kurznamen.
S3-Verkehr von Caddy zum einzelnen Seaweed-Pod bleibt namespace-intern und durch
die NetworkPolicies auf Port 9000 eingeschränkt.

Das Service-CA-ConfigMap bleibt ausschließlich für den injizierten Bundleinhalt
reserviert. Vor Freigabe prüfen, ob die konkrete GitOps-Version injizierte Daten
als Unterschied meldet; anschließend einen eng auf diese ConfigMap und diesen
Pfad begrenzten Ignore-Vertrag reviewen. Kein globales Ignorieren von TLS- oder
Secret-Unterschieden und kein automatisches Löschen injizierter Daten.

Zertifikate und Secrets im Ziel unabhängig überwachen. Mountaktualisierung
garantiert keinen Prozessreload: Caddy lädt PEM-Dateien beim Start; nach Rotation
ist ein geplanter manueller Neustart mit TLS-Prüfung nötig. Python-Clients und
Celery-Prozesse ebenfalls kontrolliert neu starten, damit alle Prozesse den
aktuellen CA-Bundle und dieselben Settings verwenden. PostgreSQL-Passwörter
ändern sich bei einer vorhandenen Datenbank nicht durch eine Secret-Änderung:
Rollenänderung und Secret-/Client-Rollout müssen koordiniert erfolgen. S3-
Identitätsrotation muss den tatsächlichen Seaweed-Ladevertrag berücksichtigen.
Keine alten Archive, TOTP-Keys oder Modellmanifeste überschreiben. Rotation
ändert weder Quellenrechte noch Modell-/Strategiefreigaben.

## restricted-v2 und Datenvolumes prüfen

Die Pods fordern `runAsNonRoot`, `RuntimeDefault`, `allowPrivilegeEscalation=false`,
`capabilities.drop=ALL` und schreibgeschützte Root-Dateisysteme an. OpenShift
weist UID, SELinux-Kontext und zulässige Gruppenzuordnung zu. Es gibt keinen
`anyuid`-Fallback und keinen Root-Initcontainer. Die Docker-Compose-
`storage-init`-Operation mit `chown` wird nicht übernommen.

Backend-HOME und Caches liegen in `/tmp`; die shellfreie Backend-Runtime benutzt
direkte Python-Probes. Web erhält ausschließlich `/app/.next/cache` als
zusätzliches `emptyDir`. PostgreSQL erhält separate schreibbare Daten- und
Socketpfade. Seaweed annonciert die tatsächliche Pod-IP statt einer Service-IP
für seine internen Master-/Filer-/Volume-Verbindungen. Diese Komponenten
bleiben jeweils einzeln. Eine höhere Replikazahl ist kein implementierter
PostgreSQL-/S3-HA-Vertrag.

Vor einer Zielabnahme sind tatsächliche SCC-Zulassung, Namespace-UID-Bereich,
CSI-/fsGroup-Verhalten, Dateirechte von Secretmounts und Datenpersistenz über
Podersatz nachzuweisen. Ein lokaler Test mit zufälliger UID oder TMPFS ist
zusätzliche Image-Evidenz, kein bestandener SCC- oder CSI-Test. Startfehler
müssen durch passende Images/Volume-Rechte gelöst werden; Sicherheitsanforderungen
dürfen dafür nicht gelockert werden.

API-Liveness verwendet `/api/v1/health/live`; Readiness verwendet
`/api/v1/health/ready` mit Timeout oberhalb der viersekündigen Dependencyprobes.
Der Worker prüft gezielt seinen eigenen `worker@hostname`; Beat bleibt eine
Replica mit `Recreate`, PID-/Schedule-Dateien in `/tmp`. Eine globale Worker-
Antwort darf einen defekten eigenen Worker nicht gesund melden.

## Netzwerk und privater Zugriff

Die Basis verbietet zunächst sämtlichen Ingress/Egress und öffnet nur interne
Abhängigkeiten und DNS. DNS-Regeln sind auf Namespace `openshift-dns`, Podlabel
`app=dns` und TCP/UDP 53/5353 beschränkt. Die tatsächlichen Labels, Ports,
Service-DNAT-/OVN- und gegebenenfalls NodeLocalDNS-Verhältnisse sind am Ziel
read-only zu prüfen; keine allgemeine Internet- oder DNS-Freigabe ergänzen.

Das separate Route-Beispiel verlangt Reencrypt-TLS zu Caddy:8443, eine echte
Destination-CA, privates Hostname-/Zertifikatsmanagement, VPN-CIDRs und eine
nachgewiesen private IngressController-Auswahl. Ein Routelabel allein macht
einen öffentlichen Router nicht privat: Operator-Routeselectors müssen den
privaten Controller einschließen und öffentliche Controller ausschließen.
Erst danach eine gezielte Router-NetworkPolicy erstellen. Vorher bleiben
8443 und die Application von außen nicht erreichbar. S3:9002 und Prometheus
erhalten keine Route. `/internal/*` bleibt durch Caddy gesperrt; kein direkter
API-Ingress, der `/internal/metrics` offenlegt. Keine öffentliche Route wird
durch Argo mitgeliefert oder automatisch erzeugt.

## Mit dem GitOps-Operator bereitstellen

Nach separat dokumentierter Security-, Cluster- und Operatorfreigabe erfolgt
die Bereitstellung manuell. Die folgenden Schritte beschreiben die Reihenfolge;
das Draft-Paket führt sie nicht aus.

1. Der Clusteroperator installiert bzw. prüft Red Hat OpenShift GitOps und die
   gewünschte Argo-CD-Instanz. Das Beispiel verwendet den Standardcontroller
   `openshift-gitops-argocd-application-controller`. Bei eigener Instanz den
   tatsächlich vorhandenen ServiceAccount und dessen Scope prüfen.
2. Der Clusteroperator legt den privaten Zielnamespace und die geprüfte
   Namespace-RBAC aus `bootstrap` manuell an. Die zusätzliche Rolle erlaubt
   nur die benötigten namespaced Ressourcentypen und deren technische
   Beobachtung; keine Secrets, Jobs, SCCs, Clusterrollen, Route oder Löschverben.
   Vorhandene Operator-/Managed-Namespace-Rollen zusätzlich auf effektiv
   weitergehende Rechte prüfen. Ein `managed-by`-Label ist absichtlich nicht
   gesetzt, weil Operator-Automatik zusätzliche Namespace-Rechte gewähren kann.
   Die konkrete Instanz muss den Scope mit expliziten Rollen verwalten können;
   kein Namespace-Admin als Ersatz. Bei einer Instanz mit eingeschränktem
   Ressourcencache müssen `resourceInclusions`/`resourceExclusions` im Argo-CD-CR
   zu den tatsächlich erlaubten Ressourcentypen passen; andernfalls kann der
   Controller beim Beobachten ausgeschlossener Typen an fehlenden Rechten
   scheitern. Diese Änderung betrifft die konkrete Operatorinstanz und ist
   nicht Teil der Application. Die [Red-Hat-Dokumentation zur Multitenancy](https://docs.redhat.com/en/documentation/red_hat_openshift_gitops/1.21/html-single/multitenancy/index)
   beschreibt die automatischen Namespace-Admin-Bindungen und diese Cache-Grenze.
3. Secrets, Pullrechte, neue PVC-/Storagefreigabe und interne TLS-Voraussetzungen
   vorbereiten. In einer ersten manuell reviewten Synchronisierung nur die
   notwendigen Infrastrukturteile aktivieren: den Application-Quellpfad zunächst
   auf das eigene Gegenstück zu `overlays/staging-infra` setzen. Dort bleiben
   API/Web/Worker/Beat auf 0. PostgreSQL, Valkey, Seaweed und Caddy müssen
   tatsächlich bereit sein. Dieselbe Application verwenden; keine zweite
   Application mit gemeinsam verwalteten Ressourcen erzeugen.
4. Den separaten Migrationsjob auf den freigegebenen Namespace und denselben
   Backenddigest patchen. Nach vorhandenem Backup und geprüftem Alembic-Ziel
   `suspend` ausdrücklich manuell auf `false` ändern und als eigenes
   Operatorkommando ausführen. Ergebnis/Code-/Imagedigests archivieren. Der Job
   gehört weder zum Application-Pfad noch zum erlaubten AppProject. Kein
   PostSync-/PreSync-Hook, kein automatischer Wiederholungsversuch.
5. AppProject und Application prüfen: tatsächliches privates Repository,
   unveränderliche vollständige Commit-SHA, eigener Overlaypfad, Cluster und
   Namespace einsetzen. Kein Branchname als Release-Pin. Den AppProject-Scope
   auf denselben Namespace und die aufgeführten Ressourcentypen begrenzen.
   Application- und Project-Erstellung bleiben manuelle Operatoraktionen.
6. Die vollständige Zielkonfiguration reviewen, den Pfad derselben Application
   nach erfolgreicher Migration auf das eigene `staging`-Overlay setzen und
   in Argo CD manuell ohne Prune synchronisieren. Das Staging-Overlay hat Replikas 1,
   insbesondere nur einen Beat. AutoSync, SelfHeal, automatisches Prune und
   kaskadierende Application-Finalizer bleiben aus. PVCs haben zusätzlich
   `Prune=false,Delete=false`. Schutzmechanismen im echten Operator prüfen.
7. Tatsächliche Readiness, Login/TOTP/Sessions, interne TLS-Verifikation,
   Neustart/Persistenz, Restore und private Erreichbarkeit abnehmen. Daten-
   und Modellfreigaben bleiben getrennt. Eine Argo-Anzeige `Healthy/Synced`
   entscheidet nicht über Quellenrechte oder finanzielle Validierung.

Für Rücknahme zuerst API, Worker und Beat kontrolliert stoppen. Ein älterer
Appdigest darf erst nach geprüftem Alembic-/Schema-Kompatibilitätsvertrag
zurückkehren. Kein automatischer Alembic-Downgrade, keine PVC-Löschung und
kein Namespace-Prune als Rollback. Korrekturen und Abnahmeprotokolle ergänzen
bestehende Evidenz, statt sie zu überschreiben.

## Backup, Restore und weiter offene Gates

Die bestehenden `ops/backup.py`-/`ops/restore_verify.py`-Verträge schützen
PostgreSQL, exakte S3-Originale und bestehende Archive samt neuen Validierungs-
und technischen Prüfsummen. Ihre bisherigen Standardtransporte verwenden
Docker Compose. `ops/backup.py --openshift-config` stellt jetzt zusätzlich den
expliziten `oc`-Transport aus `ops/openshift_backup.py` bereit; Artefakt-, Hash-,
Manifest-, Lock- und Retentionlogik bleiben derselbe bestehende Backupmotor.
Es gibt hier keinen fingierten Backup-CronJob und keine neu erfundene
erfolgreiche Restoreabnahme.

Ein zulässiger manueller Operatortransport muss dieselben bestehenden
Artefaktverträge bedienen: `pg_dump` aus dem exakt geprüften PostgreSQL-Pod,
S3-Kopie über den geprüften privaten `iip-mc`-Client mit `S3_CA_REQUIRED=true`,
Abgleich der vollständigen Originalbytes/Metadaten und SHA-256-Werte,
SQL-/Archivprüfungen und ein isolierter logischer Restore in neue Volumes.
Kein Kopieren des laufenden PostgreSQL-PVC als scheinbar konsistenter Dump.
Schreibende Anwendung und Scheduler müssen für den belegten gemeinsamen
SQL-/S3-Cutoff kontrolliert stillstehen; `pg_dump` allein fixiert keine
gleichzeitig veränderte Objektspeicherung. Originale dürfen nicht gelöscht,
überschrieben oder als bereits lokal vorhandene Historie umdatiert werden.

Der zusätzliche Client benötigt eine getrennte private Backup-PVC unter
`/backup`, schreibbares `/tmp`, Secret-basierte `MC_HOST_local`,
`MC_CONFIG_DIR=/tmp/.mc` und den injizierten Service-CA-Bundle unter
`/trusted-ca/root.crt` (`ConfigMap.items`: `service-ca.crt` auf `root.crt`
abbilden). Der Wrapper `/usr/local/bin/iip-mc` prüft diese CA und legt sie in
seinen Client-Truststore. Er darf keine Source-/Operatorrechte aus einem
technisch funktionierenden S3-Zugang ableiten. Ein separat vorhandener
Clustertransport muss seine tatsächlichen Aufrufe und Grenzen dokumentieren.

### Manueller oc-Transport

Dieser Transport ist lokal mit Fixtures geprüft, **noch nicht am Cluster**.
`oc` ist hier nicht installiert. Er darf nur gegen den später separat
freigegebenen Zielcluster verwendet werden und führt ausschließlich `get` und
die drei bestehenden Backup-Exec-Verträge aus. Er erstellt oder skaliert keine
Ressource und übernimmt keine Freigabe. Ohne gültigen Konfigurations-/Review-
und Zielnachweis endet er vor der ersten Artefakterstellung mit Exitcode 2;
es gibt keinen Docker-Fallback.

1. Den manuell getrennten Client/PVC-Entwurf prüfen und Registry, Namespace,
   StorageClass und Nodeauswahl setzen. `iip-backup-client` enthält außerhalb
   Git den einzigen benötigten Schlüssel `MC_HOST_local`, mit authentifizierter
   HTTPS-URL zum exakten `caddy.<namespace>.svc:9002`. Die zusätzliche PVC ist
   nur Staging und erfüllt keine unabhängige Recoveryanforderung. Client und
   PostgreSQL müssen bereit sein; ihre Pod-UID, Container-ID, Spec-Imagedigest
   und tatsächlich gestartete Plattform-Image-ID werden getrennt gebunden.
   Ein OCI-Indexdigest darf von der Plattform-Image-ID abweichen; beide müssen
   aus dem reviewten Registry-/Clusterinventar stammen, niemals aus einem Tag.
2. Vollständiges Writerinventar einschließlich optionaler ML-/Migrations- und
   manueller Jobs prüfen. API, Web, Worker und Beat kontrolliert auf 0 bringen,
   ausstehende Jobs stoppen, laufende Writerpods vollständig beenden. Argo-
   Sync und andere Operatoren dürfen diese währenddessen nicht starten.
   Eine externe Lease mit eindeutigem Session-Halter halten und rechtzeitig
   erneuern. Dieses Werkzeug erzeugt und erneuert die Lease nicht.
3. `examples/backup-transport.json` in einen geschützten lokalen Configpfad
   kopieren und ausschließlich anhand tatsächlicher Metadaten ausfüllen.
   Namespace-/Lease-/Pod-/Containeridentitäten, Writerselector und vollständige
   Deploymentliste pinnen. Das Beispiel ist unfreigegeben und nicht ausführbar.
   Das existierende unabhängige BitLocker-Ziel aus
   `ops/windows-backup-destination.example.json` gesondert nachweisen; der
   Windows-Client muss es als physisch getrenntes verschlüsseltes Laufwerk
   verifizieren können. Andere Zielsysteme benötigen einen gesonderten Adapter.
4. Der echte Operator prüft `Config.operator_scope()` und schreibt eine
   zeitlich begrenzte Reviewreceipt nach dem Vertrag
   `OPENSHIFT_BACKUP_OPERATOR_SCOPE_V1`, Status
   `OPERATOR_REVIEWED_BACKUP_SCOPE`, tatsächlicher Name, Reviewzeit und Ablauf
   höchstens 24 Stunden später. Der Scope umfasst auch Transfergrenzen und
   Zielpolicyhash. Deren exakte Dateihashes werden in der Transportconfig
   erfasst. `examples/backup-operator-receipt.json` erteilt keine Genehmigung.
5. Den bestehenden Motor mit gleichen Root-/Bucket-/DB-Erwartungen ausführen:

   ```powershell
   python ops/backup.py --openshift-config C:/PROTECTED/backup-transport.json --root E:/Private-IIP-Backups --database investment --bucket raw-ingestions
   ```

   Pfade sind Beispiele; diese Konfiguration wird hier nicht ausgeführt.
   Nicht mit Compose-/Environment-/Destination-CLI-Overrides mischen. Der
   Transport prüft Review, Ziel, Lease, Writer, alle Namespace-Jobs und beide
   exakten laufenden Container vor und nach jedem Transfer. Eine Podersetzung,
   ein Neustart oder eine abgelaufene Lease macht den Lauf ungültig. `oc exec`
   hat keine atomare UID-Vorbedingung; deshalb bleibt externe Exklusivität
   zwingend. Keine Credentials werden ausgelesen oder in Fehlertexten geloggt.

Dump und exakte Objektbytes werden mit festen Kommandos und Grenzen gestreamt.
Der Parser akzeptiert POSIX-USTAR und den tatsächlich geprüften einfachen
BusyBox-Header; Links, Geräte, Sparse-/PAX-/GNU-Erweiterungen, Pfadtraversal,
Windows-Aliase, doppelte Pfade, Übergrößen und unvollständige Archive scheitern
geschlossen. Insbesondere zu lange Namen, die eine GNU-Erweiterung benötigen,
führen zu einem fehlgeschlagenen Backup, keinem Erfolg mit fehlenden Objekten.
Grenzen müssen zur realen Objektmenge passen und mitreviewt werden. Keine
Dateibesitzrechte oder Archivmetadaten werden auf den Host angewendet.
Der [Test mit dem tatsächlichen gepinnten Clientimage](../security/pr9-20261028/openshift-mc-tar.json)
bestätigt den einfachen Header-/Bytevertrag; er ist kein S3- oder Clusterbackup.
Fehlgeschlagene Artefakte bleiben als fehlgeschlagen erhalten. Remote-Staging-
Retention, unabhängiger isolierter Restore und sichere Statusübernahme nach
`/app/runtime` sind vor Freigabe separat zu prüfen; nichts davon wird durch
die Host-Manifestdatei automatisch installiert.

Unabhängiges verschlüsseltes Backupziel außerhalb des Clusterfehlerbereichs,
Aufbewahrung, Laufzeitplan, Fehler-/Kapazitätsalarm, getestete Wiederherstellung,
TOTP-/Schlüsselwiederherstellung und bewiesene Statusübergabe nach
`/app/runtime` bleiben offene Betreiberaufgaben. Eine PVC ist kein unabhängiges
Backup. Fehlende Statusbelege bleiben `UNAVAILABLE`; keine Erfolgseinträge
vorab erzeugen. Der optionale Prometheus ersetzt weder diese Belege noch
getestete Alarmzustellung.

Grundlagen: [OpenShift Service Serving Certificates](https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/security_and_compliance/configuring-certificates#add-service-serving),
[OpenShift DNS Operator](https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/networking_operators/dns-operator),
[Argo CD Sync Options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/)
und [Red Hat OpenShift GitOps](https://docs.redhat.com/en/documentation/red_hat_openshift_gitops/).

Die genannten Red-Hat-/Argo-Primärdokumentationen wurden am **29.10.2026**
gegen die Namespace-/RBAC-, Service-CA- und PVC-Aufbewahrungsverträge geprüft.
Zielversionen bleiben vor Clusterbetrieb separat zu bestimmen und abzugleichen.
