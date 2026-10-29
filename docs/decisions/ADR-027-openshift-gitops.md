# ADR-027 – Optionales OpenShift-Ziel mit Red Hat OpenShift GitOps

Datum: 28.10.2026. Status: **IMPLEMENTED_PREPARATION / TARGET_CLUSTER_NOT_VERIFIED**.

## Auftrag und Entscheidung

Der Nutzer möchte die Anwendung zusätzlich über den Red-Hat-OpenShift-GitOps-
Operator als Argo CD Application bereitstellen. Derselbe Stack und dieselben
Backendsettings, Finanzdienste, Quellengates und unveränderlichen Archive werden
verwendet. Docker Compose bleibt verfügbar. Argo Workflows und eine zweite
Finanz- oder Jobpipeline sind kein Teil dieses Auftrags.

Die additive Kustomize-Basis hat keine aktiven Replikas. Ein explizites
Staging-Overlay beschreibt den startbaren Ein-Replica-Core und verlangt echte
Registry-, Namespace-, Storage-, HTTPS- und Secretkonfiguration. Argo CD erhält
ein eingeschränktes AppProject; Namespace/RBAC, Secrets, Migration und private
Routes sind separate Operatoraktionen. AutoSync, Prune, destruktive Replace-
oder Force-Verfahren und kaskadierende PVC-Löschung werden nicht aktiviert.

## Laufzeit und Daten

OpenShift bestimmt UID, SELinux-Kontext und zulässige Volumegruppe. Die
Anwendung fordert `runAsNonRoot`, `RuntimeDefault`, `drop: ALL`,
`allowPrivilegeEscalation: false` und schreibgeschützte Root-Dateisysteme.
Gezielte temporäre Mounts ersetzen keine pauschal beschreibbaren Apppfade.
Es gibt keine `anyuid`-SCC und keinen privilegierten Storage-Initcontainer.

PostgreSQL 17/pgvector, Valkey und SeaweedFS bleiben getrennte Einzelinstanzen
auf neuen PVCs. Mehr Replikas würden eine eigene HA-Architektur verlangen.
Service-Serving-Zertifikat und injizierte Service-CA schützen den S3-Clientpfad
über Caddy auf hohen Ports. DNSname, Secretmountrechte, Rotation und Neustart
der langlebigen Clients werden am Ziel geprüft. Ein privater Hostname oder
eine TLS-Route allein beweist keine private Netzexposition.

## Betrieb und Freigaben

Die bestehenden Backup-Artefakt-/Hash-/Archivverträge gelten weiter. Ein
OpenShift-Transport darf nur die Sammlung/Übertragung dieser Artefakte ändern;
er erfindet keine zweite Backupengine oder Erfolgsmeldung. SQL/S3 benötigen
einen belegten gemeinsamen ruhenden Stand und eine gemeinsame gehaltene
Clustersperre. Unabhängiges verschlüsseltes Sicherungsziel, Zeitplan,
Fehler-/Missed-Run-Alarme und getestete Recovery bleiben Pflicht.

Der bestehende `PRIVATE_CORE_SCOPE_V1` ist an Compose und dessen Recovery-
Dienste gebunden. Für OpenShift sind gerenderte Manifeste, Registrydigests,
SCC-/CSI-/Ingress-/TLS- und Recoverybelege in einem eigenen unveränderlichen
Zielvertrag zu prüfen. Ein Argo-Status `Healthy/Synced`, lokale UID-Probes oder
der Compose-RC erteilen keine Cluster- oder Securityfreigabe. Bestehende
Legacy-/Caddy-Befunde bleiben sichtbar. Fehlende Quelle, LLM oder Finanzdaten
behalten ihre bisherigen Abstention-/Unavailablezustände.

## Nachweise

[Betriebsablauf und Operatorbeispiele](../operations/OPENSHIFT_ARGOCD.md),
[Kustomize-Paket](../../ops/openshift/README.md),
[PR9-Sicherheitsgrenzen](../PR9A_SECURITY_CLOSURE_REPORT.md).
Ein Zielcluster wurde nicht bereitgestellt; tatsächliche SCC-, CSI-, GitOps-,
Client- und unabhängige Recoveryabnahme bleiben offen.
