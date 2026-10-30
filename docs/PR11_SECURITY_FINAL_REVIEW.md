# PR11 – Abschließender Securityreview

Stand **29.10.2026**. Ergebnis: **SECURITY_OPERATOR_DECISION_REQUIRED /
SECURITY_BLOCKED / NOT_APPROVED**. Keine wirksame Ausnahme oder
Produktionsfreigabe wurde erteilt.

## 1. Tatsächlicher Repository- und CI-Stand

HEAD und abgefragtes `origin/main`: **d0feaa67f1505ef247fb5dd199938f0f592230d7**.
Der angeforderte [GitHub-Lauf 40900032608](https://github.com/P-Liebler/Private-IIP/actions/runs/40900032608)
ist abgeschlossen: **Verify success / Security success**, mit 321 Backend-,
192 Host- und 31 Browserfällen. Dependency-Audits, Sourceprüfung, Scanner/DB,
API-/Web-Imageaudit und deren High-/Critical-Paketgate sind erfolgreich.
Der vollständige Core-/Recovery-Audit war **übersprungen, nicht angefordert**.
[Originaler Artefaktindex](security/pr11-20261029/remote-ci.json).

Der ZIP-SHA wurde gegen GitHub geprüft, die 13 Originaldateien begrenzt
extrahiert und ihre Hashes erhalten. Negative Unitfälle mit
`SCAN_INCOMPLETE`-/`SECURITY_BLOCKED`-Ausgaben sind keine Jobfehler.
Die lokalen PR11-Änderungen sind nicht gepusht oder remote geprüft.

Der vorhandene vollständige manuelle Workflow zeigt jetzt auf den neuen
PR11-Scope und alle zwölf erforderlichen Dienste. Keine privaten Images
werden dabei nachgebaut oder durch andere Digests ersetzt. Fehlende Bytes
ergeben **SCAN_INCOMPLETE**. Es fehlt ein autorisierter privater Transfer-/
Runnerweg; kein sinnloser Dispatch wurde ausgelöst.
[Konkreter Remote-Auditplan](security/PR11_REMOTE_RELEASE_AUDIT_PLAN.md).

## 2. Technischer Entscheid zum historischen Modellprüfer

**Der historische Python-Start ist für die Core-Archivintegrität fachlich
nicht erforderlich.** Der alte begrenzte Prüfer prüft JSON, Hashes und
installierte Metadaten; er führt selbst keine historische Inferenz oder
Training aus. Eine echte wissenschaftliche Wiederholung bleibt separat.

[ADR-029](decisions/ADR-029-private-core-archive-recovery.md) und MASTER 152/157
begründen die explizite Vertragsänderung. **PRIVATE_CORE_SCOPE_V2** verwendet
**PRIVATE_CORE_ARCHIVE_RECOVERY_V1**. Der alte V1-Pfad behält seine dynamische
Legacy-Pflicht; ursprüngliche Scope-/Manifest-/Scan-/Modelldateien wurden
nicht umgeschrieben. Das alte Image bleibt archiviert und im getrennten
`legacy-research`-Profil **SECURITY_BLOCKED**. Seine **1 Critical/47 High**
bleiben sichtbar; sie wurden weder entfernt noch als behoben bewertet.

### Welche Nachweise erhalten bleiben

Der vorhandene Restoreproducer stellt PostgreSQL/S3 tatsächlich neu her,
liest alle Rohobjekte zurück, führt den unveränderten Backendprüfer für alle
zehn Archivverträge aus und exportiert das Modell aus genau der neuen Instanz.
Modellbytes, Trainingskonfiguration, Locks, historische SBOM und alle **66 Pins**
werden gegen unabhängig aufbewahrte Originalanker geprüft. Das geschützte
Metadata-TAR wurde einmalig mit `docker create/cp` aus dem **niemals gestarteten**
alten Image gewonnen; tägliche Archivprüfungen benötigen dieses Image danach
nicht mehr. [Tatsächlicher Exportindex](security/pr11-20261029/archive-metadata-export.json).

Ein ursprünglicher Restorebericht ist nur ein historischer Erwartungsanker,
kein neuer Produzentennachweis. Der PR10-Berichtsvergleich bleibt unverändert
begrenzt. Für jeden aktuellen Backupstand verlangt PR11 zusätzlich einen
**vor Restorebeginn unabhängig gepinnten Erwartungsbeleg** mit aktuellem
Backupmanifest-SHA, Run-ID, Datei-/Objektzahl und allen zehn aktuellen
Archivhashes. Neue Backupnamen und wachsende Historien sind zulässig;
ungepinnt geänderte Erwartungen scheitern. Der ursprüngliche Modellhash
bleibt trotzdem unveränderlich. [Vorab gepinnter Abnahmecheckpoint](security/pr11-20261029/restore-expectations.json).

Originale werden bytegenau gebunden. Der CRLF-Originalmanifestpin ist kein
Hash eines LF-Gitclones; Normalisierung rechtfertigt keine Hashänderung.
Originalbelege, ihre relative Struktur, Metadata-TAR und unabhängige Pins
gehören zum geschützten Recoverymaterial. Dessen unabhängige Sicherung ist
noch eine echte externe Betreiberpflicht.

### Regression und unabhängige Gegenprüfung

**18 gezielte neue Tests** sowie die bestehenden betroffenen V1-/Metadata-/
Scope-/Releasefälle bestehen. Abgelehnt werden veränderte Originalanker,
Locks, Pins, TAR-Pfade/Links/Duplikate/Größen sowie fehlende oder manipulierte
aktuelle Checkpoints, Rawobjekte und Producerprüfungen. Der unabhängige Review
fand und beseitigte vor dem tatsächlichen Restore zwei Fehler: zu feste
Bindung an den alten Backupstand und einen schreibgeschützten Readbackpfad.
Nur ein frisches Readbackverzeichnis wird jetzt eng schreibbar gebunden;
das Backup bleibt read-only. Kein Root-/777-Fallback auf Unix.

Die [tatsächliche Core-Wiederherstellung](security/pr11-20261029/restore-core.json)
und der [separate Produktionsbuild-Restore](security/pr11-20261029/restore-standard-production.json)
prüfen jeweils **1’387 Dateien, 1’378 zurückgelesene S3-Objekte, zehn
Archivhashverträge und 66 Pins**, mit erfolgreicher Bereinigung. Der historische
Python-Prozess wird in beiden Fällen **nicht gestartet**; historische
numerische Reproduktion bleibt **NOT_EXECUTED_NOT_PROVEN**.

Dies ist der vorhandene explizite Archiv-/Portfolio-Abnahmeprüfer, keine neue
automatische Recoveryengine. Ein neu eröffnetes reales Depot muss keine
synthetischen Researchmodelle anlegen. Sein eigener echter Restore bleibt
mit seinen tatsächlichen Originalen und Erwartungen abzunehmen.

## 3. Caddy: verbleibender tatsächlicher Securityentscheid

[Frischer offizieller Patch-/Import-/JWK-Review](security/PR11_CADDY_REVIEW.md),
geprüft 29.10.2026: Für **CVE-2026-116587 / GHSA-mgcc-cww5-fp2q** ist weiter
kein unterstützter v3-Fix belegt. Das Entfernen allein des optionalen
ACME-Servermoduls entfernt die interne CA-/Smallstep-/JOSE-Kette nicht.

Die aktuelle Konfiguration aktiviert keinen ACME-Server oder On-Demand-Issuer.
Im untersuchten aktiven Corepfad wurde kein fremder JWK-Eingang gefunden;
vollständige Nichterreichbarkeit ist damit nicht bewiesen. Das Paket bleibt
im Image. Ein Kryptografiefork oder eine neue Zertifikatsverwaltung wurde
nicht als ungeprüfte Lösung eingebaut. Extern verwaltete Zertifikate brauchen
einen tatsächlichen CA-/Renewal-/Recoverybetreiber; dieser fehlt weiterhin.

Die neue tatsächliche Offline-Profilprobe ist bytegleich zu PR10, mit
Netzwerk `none`, read-only Root und UID 10001. Neun vorhandene Profilfälle
bestehen erneut. Die bestehenden Routing-/Nonroot-/CA-/S3-TLS-Nachweise bleiben
datierte PR10-Evidenz; kein weiterer synthetischer Canary wurde erfunden.

**Erforderlich:** unterstützter getesteter Fix oder echte autorisierte,
digest-/finding-/profilbezogene, befristete Entscheidung nach bestehender
Policy. Reviewer, Approvalreferenz, Beginn und Ablauf dürfen nicht aus einer
Vorlage entstehen. Bis dahin bleibt der Paket- und Produktivstart gesperrt.

## 4. Neues vollständiges exaktes Inventar

[PR11-Scope](../ops/releases/pr11-core-v1-scope.json) und
[neues Inventar](security/pr11-20261029/core-rc1/inventory.json):
**12 notwendige Dienste / 8 unterschiedliche unveränderte Images**.
Alle erforderlichen Runtime- und Recoveryimages wurden tatsächlich neu
gescannt. **12/12 Original-SBOMs** sind
[formal gültig](security/pr11-20261029/core-rc1/sbom-validation.json).
[Scanursprünge](security/pr11-20261029/core-rc1/scan-origins.json) erlauben
Aliase ausschließlich für identische Imagebytes.

| Umfang | Critical | High |
| --- | ---: | ---: |
| api / worker / scheduler / web / postgres / valkey / minio / prometheus / backup | jeweils 0 | jeweils 0 |
| caddy / ca-export / storage-init | jeweils 0 | jeweils 1 |
| Über acht unterschiedliche erforderliche Images | **0** | **1** |
| Optionaler alter Legacy-Prozess, außerhalb des neuen Core-Scope | **1** | **47**, weiterhin gesperrt laut unverändertem PR10-Scan |

Die drei Caddyzeilen sind derselbe High-Befund. Medium-/Low-/Unknown-Zeilen
bleiben sichtbar und reviewpflichtig. Der separate unveränderte normale
[Produktionsbuild](security/pr11-20261029/standard-production/inventory.json)
hat einen eigenen neuen Scan und eine formal gültige SBOM; keine Bitidentität
zum Core-Backend wird behauptet. Es wurden keine neuen Images gebaut,
numerischen Pins migriert oder historischen Versionen umdeklariert.

Trivy **0.76.0**, Executable-SHA
`51e50a34f8739424bc88282602d10945b25249ffdb51703fe3c9453c20217c42`;
validierte DB vom **29.10.2026 13:09:46.269823229 UTC**, SHA
`162d88bff697bee519561c90bb5766f2b9d27e3f0f0eb051b7a3d7bf1df42ff7`.
Die frischen Scans benutzen diese geprüfte aktuelle DB; Paketanalysatoren
beweisen keine vollständige beliebige native Exploitability.

## 5. Übrige Gates und Ergebnis

[Regression](security/pr11-20261029/regression-final.json),
[unveränderte Locks / tatsächlicher Remote-Dependency-Audit](security/pr11-20261029/dependency-audit.json),
[finaler Source-Secretscan](security/pr11-20261029/source-security.json),
[Preflight](security/pr11-20261029/core-preflight-final.json) und
[neuer lokaler RC](../ops/releases/pr11-core-v1-rc1-manifest.json) binden
die konkreten Arbeitsbytes. Kein Scan oder Manifest erteilt automatisch eine
Securityfreigabe. Native Restgrenzen, Unknown-/niedrigere Findings und die
bestehende CSP-Styleattributgrenze benötigen weiterhin berechtigten Review.

Private VPN-/DNS-/TLS-/Host-/Clientgrenzen, Secretverwaltung, unabhängig
verschlüsselte Recovery samt Schlüsseln, Tagesjob und tatsächlicher
Alarmempfang sind nicht auf einem realen Ziel geprüft. Die technische
Legacytrennung schließt keine dieser Voraussetzungen und keine Quellen-,
Forecast- oder Strategiegates. **SECURITY_APPROVED=false.**

---

## Ergänzung PR11.1 – Aktueller Review vom 30.10.2026

Die obigen 29.10.-Scans, Hashes und Restores bleiben historische Originale.
Der [neue CI-Originalindex](security/pr11-1-20261030/remote-ci.json) bestätigt
für Run **40907365492** auf `cb1489962c92fdd8fcb8fed4133cea11e836e28c` sowie
HEAD-Run **41018607349** auf `bc0f8d8872e879c01bcbe05198fc9095575fab6d`
Verify/Security erfolgreich mit **321/210/31**. Der vollständige Core-/
Recoveryaudit wurde jeweils **nicht angefordert** und bleibt
**SKIPPED_NOT_REQUESTED_NOT_VERIFIED**. Ein nicht autorisierter Dispatch oder
Imagetransfer wurde nicht ausgeführt. Der Scope bleibt zwölf notwendige
Dienste aus acht exakten Images; fehlende Runnerbytes ergeben `SCAN_INCOMPLETE`.

Der [erneute offizielle Caddy-Review](security/pr11-1-20261030/caddy-review.json)
bestätigt am 30.10. weiterhin **keinen belegten unterstützten v3-Fix** für
`CVE-2026-116587 / GHSA-mgcc-cww5-fp2q`. Der dokumentierte v4-Fix ersetzt den
v3-Paketpfad nicht. Aktive Konfiguration und exakte Binaryidentität stimmen
mit den vorherigen Profilbelegen überein; diese Hashprüfung ist kein neuer
Canary- oder Serverlauf. Im aktiven Profil ist weiterhin kein fremder
JWK-Eingang nachgewiesen; vollständige Nichterreichbarkeit bleibt unbewiesen.

Der [konkrete Ausnahmeentwurf](security/pr11-1-20261030/caddy-exception-review-draft.json)
ist **DRAFT_NOT_APPROVED**, ohne tatsächlichen Reviewer, Approvalreferenz oder
Beginn/Ablauf und mit **effective_exceptions=[]**. Die vorgeschlagene Dauer
von höchstens sieben Tagen ab echter Autorisierung ist keine bereits erteilte
Gültigkeit. Native-/Unknown-/niedrigere Befunde, CSP, TLS, Netzwerk und
Zielbetrieb benötigen weiter ihre eigenen echten Reviews.

Tatsächliche neue lokale Scan-/SBOM-/Restore-/Regressionsbelege und ihre
Aussagegrenzen stehen im [PR11.1-Verifikationsbericht](PR11_FINAL_VERIFICATION.md).
`PRIVATE_CORE_ARCHIVE_RECOVERY_V1` bleibt verbindlich; historische Python-
Ausführung und numerische Reproduktion werden nicht behauptet. Das
`gitops-demo`-Draftoverlay schließt keine Cluster- oder Sourcegates.
**SECURITY_APPROVED=false / SECURITY_OPERATOR_DECISION_REQUIRED** bleibt
gültig; [Operatorübergabe](PRIVATE_CORE_V1_OPERATOR_HANDOVER.md).

Der abgeschlossene [30.10.-Coreaudit](security/pr11-1-20261030/core-rc1/inventory.json)
prüft **zwölf Dienste aus acht exakten Images: 0 Critical / 1 High** über die
acht unterschiedlichen Imageidentitäten; [12/12 Original-SBOMs sind formal gültig](security/pr11-1-20261030/core-rc1/sbom-validation.json).
Die drei Caddydienstzeilen zählen denselben High-Befund. Der
[aktuelle Entwurf V2](security/pr11-1-20261030/caddy-exception-review-draft-v2.json)
bindet diese neuen Scan-/SBOM-/Scanner-/DB-/Configbytes und den final ergänzten
Caddy-Review; der oben verlinkte V1-Entwurf bleibt als Vorgänger erhalten.
V2 ist ebenfalls **DRAFT_NOT_APPROVED / effective_exceptions=[]**;
`SECURITY_BLOCKED` und die getrennten menschlichen Reviews bleiben bestehen.

**Revisionsnachtrag am 30.10.:** Der oben genannte `bc0f8d8`-HEAD/CI-Stand war
der anfänglich gelesene Stand. Neue Nutzercommits führten über `41249ee` zu
**`64f7445b4aef10a7b7dabe6a9a62dd051a53d1a1`** mit drei geänderten OpenShift-
PVC-JSONdateien (`storageClassName=truenas-nfs`). Der
[erneute Offline-Namespace-/Kustomizebeleg](security/pr11-1-20261030/gitops-demo-offline-v2.json)
bindet diese tatsächlichen Configbytes und neue Revision; er ist kein
serverseitiger Dry-Run oder Storage-/Clusterapproval. Die vorhandenen
Caddyprofil-/Imagebytes und die Anwendung wurden dadurch nicht geändert;
der alte CI-Erfolg wird nicht als CI-Prüfung dieser neuen Revision ausgegeben.

Der [abschließende tatsächliche Regressionsbeleg](security/pr11-1-20261030/regression-final.json)
bindet **210 erneut bestandene Hosttests nach den geänderten PVC-Configs**,
321 Backendtests je Image, den neuen 31/31-Gesamtlauf und beide vollständigen
neuen Restores. [Core](security/pr11-1-20261030/restore-core.json) und
[separater Produktionsbuild](security/pr11-1-20261030/restore-standard-production.json)
prüfen jeweils **1’387 Dateien, 1’378 zurückgelesene S3-Objekte, zehn
Archivverträge und 66 Pins**, mit erfolgreicher Bereinigung und ohne alten
Python-Start. Die [erhaltene erste Fehlprobe](security/pr11-1-20261030/restore-standard-production-attempt-v1.json)
und die [belegte Windows-MAX_PATH-Diagnose](security/pr11-1-20261030/windows-path-diagnosis.json)
werden nicht als Erfolg umetikettiert: 261-Zeichen-Pfade, kein S3-Datenverlust;
ein zweiter Kopierversuch brach vor Docker ab. Der vollständige neue Lauf im
kurzen Root benutzt denselben strengen unveränderten Restoreproducer und
dieselben unabhängigen Erwartungspins. Kein Archivgate wurde abgeschwächt.

Der [neue HEAD-Beleg](security/pr11-1-20261030/head-ci-final.json) bestätigt
CI **41021964813** auf `64f7445…` mit Verify/Security erfolgreich und 321/210/31.
Der vollständige private Core-/Recoveryaudit bleibt auch dort ausdrücklich
**NOT_REQUESTED_NOT_VERIFIED**; lokaler technischer Erfolg, normale CI und
tatsächliche menschliche Securityfreigabe bleiben getrennte Zustände.
