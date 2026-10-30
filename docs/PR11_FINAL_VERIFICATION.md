# PR11.1 – Final Verification & Operator Handover

Stand **30.10.2026**. **FULL_BROWSER_REGRESSION_PASSED**.
**SECURITY_OPERATOR_DECISION_REQUIRED / NOT_RELEASED / NOT_APPROVED**.
Dieser Auftrag schließt die lokal möglichen technischen Prüfungen und die
[Operatorübergabe](PRIVATE_CORE_V1_OPERATOR_HANDOVER.md) ab. Keine neue
Produktphase, keine Finanzdaten- oder Architekturänderung.

## 1. Tatsächlicher Git- und CI-Stand

HEAD, `origin/main` und Remote-main sind beim abschließenden CI-Abgleich
**`64f7445b4aef10a7b7dabe6a9a62dd051a53d1a1`**. Zu Beginn war es
`bc0f8d8872e879c01bcbe05198fc9095575fab6d`, dessen direkter Vorgänger der
angegebene Commit `cb1489962c92fdd8fcb8fed4133cea11e836e28c` ist.
Die zwischenzeitlichen Nutzercommits `41249ee` und `64f7445` übernehmen
Teile der Dokumentation und setzen in drei OpenShift-JSONs
`storageClassName: truenas-nfs`. Diese Änderungen bleiben erhalten; sie
ändern weder Appcode/Images noch Core-/Recoveryverträge.
Nach ihnen wurden die **210 Hosttests erneut vollständig bestanden** und
Namespacevertrag sowie echtes Kustomize-Render erneut geprüft. Der neue
[Offlinebeleg V2](security/pr11-1-20261030/gitops-demo-offline-v2.json)
bindet die tatsächlichen Configbytes: acht Workloads mit null Replikaten,
drei PVCs mit diesem Klassennamen. Existenz und Eignung von StorageClass/CSI
sind damit nicht am Cluster bewiesen. Der ursprüngliche Offlinebeleg bleibt erhalten.

| Tatsächlich gelesener Actions-Lauf | Revision | Verify / Security | Vollständiger privater Core-/Recoveryaudit |
| --- | --- | --- | --- |
| [40907365492](https://github.com/P-Liebler/Private-IIP/actions/runs/40907365492) | `cb148996…` | Erfolgreich, 321 Backend / 210 Host / 31 Browser | Übersprungen, nicht angefordert |
| [41018607349](https://github.com/P-Liebler/Private-IIP/actions/runs/41018607349) | `bc0f8d8…` | Erfolgreich, 321 Backend / 210 Host / 31 Browser | Übersprungen, nicht angefordert |
| [41021964813](https://github.com/P-Liebler/Private-IIP/actions/runs/41021964813) | `64f7445…` | Erfolgreich, 321 Backend / 210 Host / 31 Browser | Übersprungen, nicht angefordert |

Der [Originalindex](security/pr11-1-20261030/remote-ci.json) bindet Lauf-/Artefakt-IDs,
Status und Originalartefakt-/Mitgliedshashes der ersten beiden ausgewerteten
Läufe. Der [abschließende HEAD-Beleg](security/pr11-1-20261030/head-ci-final.json)
bindet zusätzlich Job-IDs, tatsächliche Logbelege und Status des neuen HEAD-Laufs;
dessen Artefakt ist metadatiert, kein neuer Download wird behauptet.
`full_inventory` war jeweils nicht angefordert:
**NOT_REQUESTED_NOT_VERIFIED**, keine Remote-Releasefreigabe. Die zusätzlichen
PR11.1-Arbeitsbytes sind lokal und wurden nicht gepusht oder remote ausgeführt.

## 2. Neue lokale Verifikation

| Prüfung am 30.10. | Tatsächliches Ergebnis |
| --- | --- |
| Backend, unverändertes Coreimage | **321 bestanden**, numerische Pins vorher/nachher unverändert |
| Backend, separates normales Produktionsimage | **321 bestanden**, numerische Pins vorher/nachher unverändert |
| Hostverträge | **210 bestanden** |
| Ruff / Format / Mypy, zusätzliche Prüfung des bestehenden Namespace-Skripts | Bestanden |
| Frontend-Lint / Typecheck / abgeschlossener Standalone-Build | Bestanden, Entwicklungsserver vorher gestoppt |
| Neuer vollständiger Standalone-Browserlauf | **31/31 in einem einzigen Lauf**, 3,7 Minuten, keine abgeschwächten Assertions |
| Native Proben, Fresh Migration und Drift, jeweils beide Backendimages | Bestanden; unverändert `0021_ui_requests` |
| Vollständige isolierte Restores | **Zwei bestanden**, je 1’387 Dateien, 1’378 Raw-Readbackobjekte, zehn Archivverträge, 66 Pins und erfolgreiche Bereinigung |
| Neue exakte Imagescans und formale Original-SBOM-Prüfung | **12/12 Dienste, acht unveränderte Images, 12 gültige SBOMs**; normales Produktionsimage separat ebenfalls gültig |

Der Browserlauf verwendet `ops/docker-compose.e2e.yml` und das geprüfte
vorhandene Setup. Es wurden keine neuen manuellen synthetischen Setuparchive
erzeugt. Die Testfälle selbst üben weiterhin ihre ausdrücklich synthetischen
Importe aus. Der alte 29.10.-Fehler mit 30/31 und der gezielte 1/1-Nachlauf
bleiben unverändert erhalten. Erst dieser neue Gesamtlauf begründet
**FULL_BROWSER_REGRESSION_PASSED**.

Nach dem Browserlauf sind Normalmodus, leere temporäre DATA-/ML-Operatorlisten,
deaktivierter Assistententestmodus sowie deaktivierte Collection und
Forward-Scheduling geprüft. Der zusätzliche
[Viercontainerbeleg](security/pr11-1-20261030/runtime-settings-reset.json)
bindet tatsächliche Container-/Image-IDs und Startzeiten. Er prüft die
gemeinsame Settingsfunktion in jeweils einem Childprozess derselben
Containerumgebung, keine Hauptprozess-Speicherinspektion. Die tatsächliche
[Quellenregistry](security/pr11-1-20261030/source-registry-readonly.json)
bestätigt read-only: **ECB und OpenFIGI UNKNOWN, deaktiviert und
SOURCE_NOT_APPROVED**, ohne Rechte-/Aktivierungsentscheid oder Providerrequest.

Neuer [lokaler Preflight V2](security/pr11-1-20261030/core-preflight-final-v2.json)
ist technisch gültig; der
[Installationsplan V2](security/pr11-1-20261030/core-install-plan-v2.json) ist nur
**STAGING / NOT_APPROVED / executed=false**, zunächst ohne Manifest.
V2 bindet die geschützten Inputs mit dem abschließenden HEAD; die vorherigen
Pläne bleiben erhalten.
Die [OpenShift-Offlineprüfung](security/pr11-1-20261030/openshift-offline-preflight.json)
hat keine Konfigurationsfehler und bleibt **DRAFT_NOT_DEPLOYABLE**.
Der [Dependencybeleg](security/pr11-1-20261030/dependency-audit.json) bindet
die tatsächlichen aktuellen CI-Originalreports: 66 Core-Abhängigkeiten,
94 im getrennten optionalen MLflow und NPM jeweils ohne bekannte Auditbefunde.
Vier Lockfiles stimmen im LF-Inhalt exakt mit HEAD überein; unterschiedliche
CRLF-Dateihashes sind ausdrücklich ausgewiesen. Das ersetzt keinen Imagescan.

Der [neue vollständige Regressionsbeleg](security/pr11-1-20261030/regression-final.json)
bindet die tatsächlichen neuen Läufe und privaten Loghashes, einschließlich
des zusätzlichen Hostlaufs nach den Nutzercommits und des erhaltenen
fehlgeschlagenen Restoreversuchs. Keine Remote-, Realdepot- oder menschliche
UX-Abnahme wird daraus abgeleitet.

## 3. Archiv- und Recoveryvertrag

Verwendet wird derselbe vorhandene PR10-Backupsatz
`20261029T141550Z-8532`, Manifest-SHA-256
`9ef36872d9c43f306ff0720a881760e3de135566c5c134d4ad0c2134c1829ab5`.
Die beiden neuen Restoreziele liegen getrennt unter C:-Staging; das originale
Backup bleibt unverändert. Diese lokale Kopie ist kein unabhängiges Backupziel.

Der vor beiden Läufen unabhängig bekannte aktuelle
[Erwartungsbeleg](security/pr11-20261029/restore-expectations.json) bleibt exakt
SHA-256 **`87e4a709e49c9f4948445111e9b00f29a89e6ae7302d7e9c3975105972496e5a`**;
der CLI-Aufruf verwendet diesen festen Erwartungshash. Er wird nicht erst aus
dem wiederhergestellten Zustand hergeleitet. Historischer Modellanker,
ursprünglicher Manifestdateihash und Metadata-TAR bleiben getrennt erhalten.
CRLF-Originalbytes dürfen nicht durch LF-Gitbytes ersetzt werden.

Die tatsächlichen neuen Belege für
[Core](security/pr11-1-20261030/restore-core.json) und
[normale Produktion](security/pr11-1-20261030/restore-standard-production.json)
bestätigen PostgreSQL-Restore, S3-Restore und unabhängigen vollständigen
Readback: **je 1’387 geprüfte Dateihashes, 1’378 Rawobjekte, alle zehn
Archivverträge, 66 Originalpins und erfolgreiche Bereinigung**. Es wurde
kein `--legacy-image` übergeben, kein historisches Image gestartet und kein
archivierter Pythoncode importiert. Historische numerische Reproduktion bleibt
**NOT_EXECUTED_NOT_PROVEN**; die gesperrte dynamische Forschungsruntime wird
nicht freigegeben.

**Erhaltener Fehlversuch und konkrete Ursache:** Der erste normale
Produktionsrestore blieb wegen `ValueError` fehlgeschlagen und wurde
erfolgreich bereinigt. Sein
[Originalstatus](security/pr11-1-20261030/restore-standard-production-attempt-v1.json)
bleibt erhalten. Im langen Windows-Readbackpfad hatten genau 683
`__pr7_archive/`-Dateien jeweils **261 Zeichen** lange Vollpfade; der normale
Win32-Zugriff sah nur 695 Dateien. Über den erweiterten Windows-Absolutpfad
waren **dieselben unveränderten 1’378 Dateien mit allen korrekten Hashes**
sichtbar; der unveränderte strenge Prüfer besteht dort. Die
[read-only Diagnose](security/pr11-1-20261030/windows-path-diagnosis.json)
beweist die Pfadgrenze, keinen S3-/Uploadverlust. Ein weiterer längerer
Staging-Kopierversuch scheiterte bereits vor Docker mit `WinError 3`.

Der anschließend tatsächlich neu ausgeführte vollständige Restore benutzt
den kurzen frischen Stagingroot
`C:/Users/liebler/Private-IIP-Local-Staging-Backups/pr11s1`, denselben
unveränderten Producer, dieselben Images/Originalbytes und die festen
Erwartungen. Er besteht vollständig einschließlich aller Hashes und Cleanup;
die read-only Diagnose wurde nicht als neuer Restore gezählt. Für weitere
Windowsläufe müssen **auch die vollständigen verschachtelten Backup- und
Readbackpfade** unter der normalen Pfadgrenze bleiben; ein kurzer Rootname
allein ist kein Nachweis. Keine Prüfung von Hashes, Originalität oder
Vollständigkeit wurde abgeschwächt.

CHF **10’180** gilt ausschließlich für das bestehende synthetische Portfolio
am **26.10.2026, 15:18:05.987683 UTC**. Dieselben heute veralteten Daten ergeben
weiterhin **STALE_PRICE**; fehlende Daten werden nicht als Null ausgegeben.
Modelle, Locks, zehn Archivverträge, Migrationen, alte Scopes/Manifeste und
historische Scan-/Restore-JSONs bleiben unverändert. Der Masterplan behält
alle **212 Hauptabschnitte**. Die ursprünglichen Bytes der ergänzten
Abschlussdokumente wurden vorher separat hashgeprüft aufbewahrt.

## 4. Security und exakter Remoteaudit

Autorität bleibt der unveränderte
[V2-Scope](../ops/releases/pr11-core-v1-scope.json): **zwölf notwendige Dienste
aus acht unterschiedlichen Images**. Der optionale dynamische Legacypfad bleibt
separat **SECURITY_BLOCKED**; seine historischen Befunde werden nicht gelöscht.

Das neue [Coreinventar](security/pr11-1-20261030/core-rc1/inventory.json)
und die [formale SBOM-Prüfung](security/pr11-1-20261030/core-rc1/sbom-validation.json)
belegen alle zwölf Dienste. Gemeinsame Imagebytes werden nur über exakt
identische Digests zugeordnet; die
[Herkunftszuordnung](security/pr11-1-20261030/core-rc1/scan-origins.json) bindet
die jeweiligen Originalrecords. Alle acht unterschiedlichen Images und das
zusätzliche normale Produktionsimage wurden tatsächlich neu gescannt.
Trivy **0.76.0**, Binary-SHA-256
`51e50a34f8739424bc88282602d10945b25249ffdb51703fe3c9453c20217c42`,
verwendet die frisch offiziell bezogene DB mit **UpdatedAt 30.10.2026,
07:16:25 UTC**; Scanrecords binden ihre tatsächlichen Bytes und Metadaten.

Ergebnis über die **acht unterschiedlichen Coreimages: 0 Critical / 1 High**.
Der eine High-Befund betrifft das gemeinsame Caddyimage in `caddy`, `ca-export`
und `storage-init`; das Inventar enthält deshalb drei dienstbezogene Zeilen
desselben Befunds. Die beiden Backendimages haben jeweils 0 Critical / 0 High;
Medium-/Low-/Unknown- und native Befunde bleiben ausdrücklich offen.
**SECURITY_BLOCKED** bleibt der Corestatus; der
[normale Produktionsbuild](security/pr11-1-20261030/standard-production/inventory.json)
steht separat auf **SECURITY_REVIEW_REQUIRED**. Ein vollständiger Scan ist
keine menschliche Securityfreigabe.

Die [offizielle Upstreamnachprüfung](security/pr11-1-20261030/caddy-review.json)
vom 30.10. zeigt weiterhin keinen belegten unterstützten v3-Fix für
**CVE-2026-116587 / GHSA-mgcc-cww5-fp2q**. Caddy 2.11.7 führt über
Certificates/Crypto weiterhin `go-jose/v3` 3.0.5; der dokumentierte v4-Fix
behebt diesen v3-Pfad nicht. Im aktiven Profil wurde kein fremder JWK-Eingang
nachgewiesen. Das ist kein Beweis vollständiger Nichterreichbarkeit; Exposition,
Limits und getrennte Profile sind im [Caddy-Review](security/PR11_CADDY_REVIEW.md)
beurteilt. Kein neuer Binarybuild oder Canarylauf wird behauptet.

Der [neue Ausnahmeentwurf V2](security/pr11-1-20261030/caddy-exception-review-draft-v2.json)
bindet exakt das neue Inventar, alle drei betroffenen Dienst-/Config-/Imagedigests,
neue Scan-/SBOM-/Scanner-/DBhashes und den final ergänzten Caddy-Review.
Die V1-Vorlage bleibt als vorheriger Beleg erhalten. **DRAFT_NOT_APPROVED**:
Reviewer, Genehmigung und tatsächliche Gültigkeitszeiten sind leer,
`effective_exceptions=[]`. Die unveränderte bestehende Policy weist alle
drei vorgeschlagenen Einträge tatsächlich zurück. Die vorgeschlagenen
höchstens sieben Tage beginnen erst nach einer echten passenden Autorisierung;
sie sind keine heute erteilte Ausnahme.

Die [lokale Verfügbarkeitsprüfung](security/pr11-1-20261030/head-and-image-availability.json)
bestätigt alle acht exakten Pins mit Image-ID, Plattform und RepoDigests.
**Remote: NOT_VERIFIED_NO_AUTHORIZED_RUNNER_OR_TRANSFER_PROVIDED.** Es wurde
kein zugänglicher autorisierter Runner samt privaten Originalbytes bereitgestellt.
Der vorhandene `ubuntu-latest`-Workflow enthält keinen privaten Imageimport.
Normale API-/Web-CI-Neubauten dürfen die Releasepins nicht ersetzen.

Es fehlen konkret: autorisierter isolierter Runner/Dockerdaemon, geschützter
Transportweg und Übertragungsfreigabe, vorab unabhängige Payload-/Confighashes,
erhaltene Manifest-/Config-/Plattformidentität sowie der bestätigte Eingang
dieser Originalbytes in denselben Auditdaemon. Anschließend die reviewte
Revision mit V2-Scope und zwölf Pflichtnamen über den
[bestehenden Auditablauf](security/PR11_REMOTE_RELEASE_AUDIT_PLAN.md) prüfen.
Verlorene Digestreferenzen, fehlende Bytes oder fehlgeschlagene Scans bleiben
**SCAN_INCOMPLETE**. Der bisher nicht angeforderte Audit wird dadurch nicht
nachträglich als fehlgeschlagen oder bestanden umetikettiert. Kein Dispatch,
Imagetransfer, Rebuild, Tag-Pull oder produktiver Start erfolgte.

## 5. Was für das erste echte Depot noch fehlt

Die [ausführbare Operatorübergabe](PRIVATE_CORE_V1_OPERATOR_HANDOVER.md) enthält
für jeden Punkt Rolle, reale Eingaben, Aktion, Erfolgskriterium und gesperrte
Funktion. Erforderlich bleiben:

1. Tatsächliche Caddyentscheidung und getrennte Native-/Unknown-/CSP-/TLS-/
   Netzreviews sowie Security- und Releaseoperatorfreigaben für exakte Bytes.
2. Ein tatsächlich bereitgestellter und autorisierter privater Composehost
   oder OpenShiftcluster mit VPN/DNS/CA/Secret-/Storage-/Clientabnahme.
3. Unabhängiges verschlüsseltes Recoveryziel, getrennte Schlüssel, echter
   Tagesjob und Alarmempfang sowie isolierter Restore von genau diesem Ziel.
4. Für automatische ECB-FX-Versorgung konkrete Rechteprüfung, getrennte
   Aktivierung, begrenzter echter Erstabruf und tatsächliche spätere Aktualisierung.
   Rechtmäßiger manueller Import bleibt ein zulässiger Coreweg.
5. Eigener Benutzer, echte unveränderte Brokeroriginale, nachvollziehbarer
   Mengen-/Cash-/Actions-/Preis-/FX-/CHF-Abgleich und unabhängiger Depotrestore.
6. Beobachteter Anfängertest mit unabhängiger Person nach dem bestehenden PR7-Protokoll.

Diese Infrastruktur, Originale und menschlichen Entscheidungen **kann Code
allein nicht bereitstellen oder genehmigen**. Die Quellen-, Modell- und
Strategiegates bleiben unabhängig; weder Forecasts noch Empfehlungen sind
hierdurch validiert. Keine Geheimnisse oder Brokeroriginale gehören in GitHub.

## 6. Abschluss und Stop

Die abschließenden Git-sichtbaren Arbeitsbytes erhalten ein eigenes
[PR11.1-Verifikationsmanifest](../ops/releases/pr11-core-v1-final-verification-manifest.json)
über die bestehende Manifestengine. Es bindet Scope, öffentliche Configbytes,
Images, neues Inventar/SBOMs, beide tatsächlichen Restores, unveränderte
unabhängige Erwartungen und die neuen Prüfberichte. Der
[Source-Secrets-Beleg](security/pr11-1-20261030/source-security.json) erfasst
die gescannten Quelldateihashes mit **NO_KNOWN_SECRET_FINDINGS**; nur dieser
nach dem Scan erzeugte sichere Hashindex und das neue Manifest sind als
nachträgliche Evidenzoutputs deklariert. Rohmatches oder Secrets werden nicht
publiziert. Die anschließende bestehende Manifest-/Installationsplanprüfung
validiert Bytes und erteilt weiterhin **keine Freigabe oder Ausführung**.

Alte Manifeste und ihre Originalbytes bleiben Archivbelege ihres jeweiligen
damaligen Stands. Ergänzte aktuelle Dokumente werden über das neue Manifest
gebunden; alte Sourcehashes werden dafür nicht umgeschrieben. Jede weitere
Änderung an gebundenen Bytes erfordert einen eigenen neuen Beleg.

**PRIVATE_CORE_V1_RELEASED=false.** Kein tatsächliches Zieldeployment, keine
produktive Migration oder Cutover, Quellenapproval, Modellpromotion, Handel,
Push oder Veröffentlichung. **STOP:** Die technisch unabhängigen Prüfungen
und die Übergabe schließen diesen Auftrag ab; als nächstes folgen die
benannten realen Operatorentscheidungen und Nachweise.
