# PR10 – Legacy-Recovery: Integritätsvertrag und isolierter Entscheid

Prüfdatum: **29.10.2026**. Status: **DRAFT_NOT_APPROVED / SECURITY_BLOCKED**. Keine Ausnahme, normative Runtime-Ablösung, Produktionsfreigabe oder Modellpromotion ist erteilt.

## Exakter Ausgangspunkt

| Gegenstand | Gebundener Stand |
| --- | --- |
| Recovery-Image | `private-iip/backend@sha256:acb9d2027e8925f756ccd7d1a22e1fae989c0db3bf8bf486400e0bc963e21816` |
| Image-Konfiguration | `sha256:29dea27969cb393d244c5a7b309e3a87df62cadda50df5420e56fc5552c5d5c9` |
| Bestehender vollständiger Scan | [PR9-Core-Inventar](pr9-20261028/core-rc1/inventory.json): **1 Critical / 47 High**; Datenbank-/Scanzeit bleiben dessen ursprüngliche Zeiten. Ein endgültiger Release braucht frische eigene Evidenz. |
| Originale Scanbytes | SHA-256 `52527b55262b37bf079d181f42b32d694c15ffde5e9d9993151b52aad28601d1` laut gebundenem PR9-Inventar |
| Originale PR9-SBOM-Bytes | [legacy-verifier.cdx.json](pr9-20261028/core-rc1/legacy-verifier.cdx.json), SHA-256 `4effc6b4680e4ff84f06007c8903e4351d38915a50aba10426f4814ff7f4e22b` |
| Historischer Aufruf | [`ops/verify_legacy_model.py`](../../ops/verify_legacy_model.py): eingebetteter Standardbibliothek-Code, JSON-/Hash-/Lockprüfung; keine Modellinferenz |
| Alte Belege | [PR9-Legacy-Review](PR9_LEGACY_VERIFIER_REVIEW.md), [PR9-Restore](pr9-20261028/restore-core.json), [ursprünglicher Static-Lauf](pr9-20261028/static-archive-metadata-final.json); unverändert erhalten |

## Option A – Moderne Integritätsprüfung

### Tatsächlich benötigte Aussagen und vorhandene Abdeckung

| Archivgegenstand | Ursprünglicher erwarteter Wert | Neuer Nachweis und Grenze |
| --- | --- | --- |
| Unveränderte Modellbytes | Ursprünglicher Artefakthash aus eingefrorenem Static-/Restorebeleg | Neu gelieferte Bytes müssen genau diesen Hash haben. Ein neu berechneter Hash rettet keine Änderung. |
| Trainingskonfiguration und Modellmanifest | Im hashgebundenen ursprünglichen JSON-Artefakt enthalten, mit Registry-Konfiguration abgeglichen exportiert | Inhalt und Begleitmetadaten stimmen überein. Es wird kein Training ausgeführt. |
| Trainingscode-/Dependency-Vertrag | Ursprüngliche Code-/Lockdaten im selben Artefakt und ursprüngliche Lockhashes | Lockbytes, 66 installierte Pins und Metadatenmanifest werden statisch aus dem exakten historischen Image gelesen. Kein archiviertes Package wird importiert. |
| Forecasts und Outcomes | Ursprünglicher `archive_contracts.predictions`-Hash | Gelieferter Bericht muss denselben gemeldeten Hash ausweisen. Keine eigene Prüfung wiederhergestellter DB-/S3-Bytes und keine numerische Neuerzeugung. |
| Dataset und weitere Historien | Alle zehn ursprünglichen Archivhashverträge | Ausschließlich Vergleich der gelieferten Berichtsangaben; dessen tatsächliche SQL/S3-/Datasetprüfungen sind durch den Produzentenlauf getrennt zu belegen. |
| Nachvollziehbarkeit | Unabhängig aufbewahrter ursprünglicher Manifestpin, dessen Quellen-/Artefakthashes und neuer Ergebnisbeleg | Der Leser überprüft die Kette, nicht die Identität des Herausgebers. Manipulierte Erwartungsbelege müssen durch den unabhängig beschafften Pin auffallen. |
| Historische Runtime-Ausführbarkeit | Erfolgreicher alter Python-Prozess im bisherigen Vertrag | **Vom neuen Verifier nicht ausgeführt und nicht bewiesen.** |
| Historische numerische Wiederholung | P7-Eingaben/Code/Runtime und eigener Inferenz-/Trainingslauf | **Weder der alte begrenzte Verifier noch der neue Static-Pfad beweisen dies.** |

### Implementiert und geprüft

[`ops/verify_archive_recovery.py`](../../ops/verify_archive_recovery.py) liefert den neuen additiven Vertrag `PR10_ARCHIVE_INTEGRITY_RECOVERY_V2`. Er verlangt einen erwarteten ursprünglichen Manifest-SHA als explizite Eingabe, prüft dessen Inhaltschecksumme und liest Erwartungen ausschließlich aus darin gebundenen ursprünglichen Belegen. Die gelieferten Modellbytes und die **gemeldeten** Archivhashverträge werden vor Dockerzugriff verglichen. Anschließend verwendet er den bestehenden begrenzten Static-Leser mit `docker create` und `docker cp`; das alte Image wird **niemals gestartet**.

**14 neue Offline-Fixturetests bestanden.** Der [tatsächliche V2-Lauf](pr10-20261029/archive-integrity-original-receipt-recheck-v2.json) bestand für die gelieferten bestehenden synthetischen Modellbytes und **66 Pins**. Der unabhängig zu beschaffende ursprüngliche RC-Manifestpin dieses Laufs lautet `7c30af3861d7c93e847fa8b6daae374d8236186e3f357289259956ed2e270785`. Der gelieferte Bericht ist bytegleich zum ursprünglichen Restorebericht vom **28.10.2026** und wird deshalb als **`ORIGINAL_RECEIPT_RECHECK_ONLY`** ausgewiesen. Die Zahl **1'385** ist ausschließlich `reported_verified_backup_files`, keine neue eigene Dateiprüfung. Der [erste V1-Beleg](pr10-20261029/archive-integrity-original-restore.json) bleibt unverändert; seine allgemeineren Ergebnisnamen begründen keine weitergehende Aussage als die hier präzisierte V2-Grenze.

`integrity_verified=true` besitzt den festen Scope `SUPPLIED_ARTIFACT_BYTES_AND_HISTORICAL_IMAGE_METADATA_ONLY`. Dieser Verifier führt **keinen Restore aus**, greift auf **keine wiederhergestellte Datenbank oder S3-Instanz** zu und prüft **keine wiederhergestellten Archivbytes**. Er prüft die tatsächlich gelieferten Modellbytes und Image-Metadaten und vergleicht separat gelieferte Berichtsangaben. Auch anders datierte oder anders gespeicherte Berichtskopien beweisen weder einen frischen Restore noch unabhängige Kontrolle ihrer Produzentenaussagen. Alle entsprechenden Ergebnisfelder bleiben false. Ein tatsächlich neuer Restore ist durch seinen eigenen unveränderlich gebundenen Produzentenlauf nachzuweisen.

Die ursprüngliche Metadatenprüfung bindet die ältere Original-SBOM aus PR8 (`0dbc717f…`). Die spätere PR9-Scanausgabe besitzt andere SBOM-Bytes (`4effc6b4…`), obwohl Image und ausgewählte Metadaten gleich sind. Der neue Vergleich akzeptiert diese spätere SBOM **nicht still als dieselbe ursprüngliche SBOM**. Für diesen Archivanker ist das ursprüngliche PR8-Inventar zu verwenden; ein frischer Securityscan ist ein separater Nachweis.

Ausführbarer Operatoraufruf; private Originalumschläge bleiben außerhalb Git/CI:

```powershell
python ops/verify_archive_recovery.py --original-manifest ops/releases/pr9-core-v1-rc1-manifest.json --expected-original-manifest-sha256 7c30af3861d7c93e847fa8b6daae374d8236186e3f357289259956ed2e270785 --original-static-reference docs/security/pr9-20261028/static-archive-metadata-final.json --restored-proof docs/security/pr9-20261028/restore-core.json --envelope backups/pr5-legacy-fixture-envelope.json --inventory docs/security/pr8-20261027/core-rc3/inventory.json --workdir backups --output backups/NEUER-ARCHIV-INTEGRITAETSBELEG.json
```

### Normative Entscheidung bleibt offen

[ADR-028](../decisions/ADR-028-archive-integrity-and-historical-runtime.md) dokumentiert die Aussagegrenzen und den noch offenen Bedarf an historischer Runtime-Ausführung. Die neue Integritätsprüfung setzt `required_legacy_runtime_check_satisfied=false` und `security_approval=false`. Restore, Release-Manifest, Archivcheckpoint und vollständiger Core-/Recovery-Scope behalten ihre bisherigen Anforderungen. Das neue Tool beseitigt den Legacy-Blocker daher nicht automatisch.

Für eine tatsächliche Ablösung fehlen: expliziter Architektur-/Kompatibilitätsentscheid über die Runtime-Anforderung, versionierte zentrale Restore-/Releaseverträge, negative Regression dieser Integration und ein tatsächlicher isolierter Restore mit dem neuen Vertrag. Kein vorhandener numerischer Modelllader oder historischer Manifestvertrag darf dafür abgeschwächt werden.

## Option B – Digest- und findingbezogene befristete Recovery

Die [maschinenlesbare Reviewvorlage v2](pr10-20261029/legacy-recovery-review-template-v2.json) enthält **alle 48 Critical-/High-Paketbefunde** des gebundenen PR9-Inventars, **12 unterschiedliche IDs**, jeweils mit Paket/Version, Digest, Advisory, tatsächlichem Prüfpfad, Patchstand, Exposition, Restgefahr, vorgeschlagener Befristung und Review-Triggern. Gemeinsame Schutzmaßnahmen sind explizit referenziert. Reviewer, Approvalreferenz und Gültigkeit sind **leer**, effektive Ausnahmen `[]`. Die Vorlage ist keine genehmigte Exceptionliste. Die [erste vorbereitete Fassung](pr10-20261029/legacy-recovery-review-template.json) bleibt als Stand vor der nachfolgend beschriebenen Runnerkorrektur erhalten.

### Primärdokumentation neu geprüft

**Critical `GHSA-6q48-6c7w-9gw2`, certifi 2026.7.22:** Der [Maintainer](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2) bestätigt den emSign-CA-Befund, Critical und **keine bekannte CVE**. Fix ist 2026.10.18; die [GitHub-Advisory-Datenbank](https://github.com/advisories/GHSA-6q48-6c7w-9gw2) empfiehlt 2026.10.19 oder neuer. Der feste Prüfer importiert keinen HTTP-/TLS-Client und kein certifi, Netzwerk ist `none`. Der vorgesehene MITM-Pfad ist damit im begrenzten Aufruf nicht vorhanden. Diese Code-/Konfigurationsinferenz ist kein Exploitnachweis und keine pauschale Nichtbetroffenheit. Ein Patch würde den historischen installierten Pin ändern.

| IDs / betroffene Paketgruppe im Scan | Neu geprüfter Primärstand und begrenzter Ausführungspfad |
| --- | --- |
| `CVE-2026-76642`, util-linux-Familie | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-76642): privilegierte Mount-Hooks; Trixie weiterhin betroffen, Fix in Unstable. Der feste Prüfer ruft keine Mountwerkzeuge auf. |
| `CVE-2026-78408`, util-linux-Familie | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-78408): `nsenter --join-cgroup`; Trixie betroffen, Unstable 2.42.4-1 gefixt. Kein `nsenter` oder Host-Namespace im festen Prüfer. |
| `CVE-2026-78409`, util-linux-Familie | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-78409): `X-mount.subdir`-Pfadauflösung; Trixie betroffen. Kein Mount-/fstab-Pfad vorgesehen. |
| `CVE-2026-78410`, util-linux-Familie | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-78410): Bind-Mount-Quellpfadrennen/Ownership-Hooks; Trixie betroffen. Keine Hostmounts oder Mountprivilegien vorgesehen. |
| `CVE-2026-54369`, libacl1 | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-54369): privilegierte pathname-basierte ACL-Funktionen; Trixie betroffen, ABI-erweiternder Fix in acl 2.4.0. Keine absichtlichen ACL-Aufrufe; vollständige native Erreichbarkeit nicht gemessen. |
| `CVE-2025-69720`, ncurses-Familie | [Debian](https://security-tracker.debian.org/tracker/CVE-2025-69720): Stackoverflow im `infocmp`-CLI. Kein Terminal-/infocmp-Aufruf. Trixie weiterhin betroffen. |
| `CVE-2026-16742`, libsystemd0/libudev1 | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-16742): systemd-homed-Gruppenzuweisung; Trixie betroffen. Kein homed-Dienst gestartet; native Abhängigkeiten nicht vollständig ausgeschlossen. |
| `CVE-2026-9538`, perl-base | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-9538): Perl Archive::Tar-Speicherverbrauch; Trixie-Update aufgeschoben, Upstreamfix 3.10. Kein Perl-/Archive::Tar-Aufruf. |
| `CVE-2026-115572`, pypdf | [Maintainer](https://github.com/py-pdf/pypdf/security/advisories/GHSA-6c7f-9265-g8fw): wiederholte fehlende PDF-Objekte; Fix 6.21.2. Kein pypdf-Import oder PDF-Eingang im Prüfer. |
| `CVE-2026-115580`, pypdf | [Maintainer](https://github.com/py-pdf/pypdf/security/advisories/GHSA-gmh7-3g9r-mjh5): überhöhte xref-Limits; Fix 6.21.2. Kein PDF-Parsing. |
| `CVE-2026-115585`, pypdf | [Maintainer](https://github.com/py-pdf/pypdf/security/advisories/GHSA-jr96-gvgh-j3r4): wiederholte malformed xref-Streams; Fix 6.21.2. Kein PDF-Parsing. |

Die drei pypdf-Maintainer-Advisories bewerten Moderate; das vorhandene Scannerinventar bewertet High. **Die strengeren inventarisierten High-Befunde bleiben erhalten.** Keine Neubewertung ist allein zur Aufhebung eines Gates übernommen. Fremde Debian-Releasepakete werden nicht in das historische Image eingebaut.

### Tatsächliche Ausführung und fehlende Hostbelege

Der Runner verwendet das exakte Image mit `--pull never`, `--network none`, schreibgeschütztem Root, UID/GID `10001:10001`, `cap-drop ALL`, `no-new-privileges`, keinen Mounts/Ports/Hostsecrets, isoliertem `python -I -B`, begrenztem JSON/Base64-Eingang und festen Standardbibliothek-Imports. Ressourcen: 512 MiB, eine CPU, 32 PIDs, 16 MiB `noexec,nosuid`-tmpfs; angehängte Ausführung höchstens 90 Sekunden, einzelne Create-/Cleanup-Operationen höchstens 30 Sekunden. Modell-, Provider-, PDF- und ausführbare Serialisierungsimporte fehlen im festen Prüfcode.

Dockerzugriff bleibt eine mächtige Operatorberechtigung; der API wird kein Socket gegeben. Ein Container teilt den Hostkernel. Python-/libc-/JSON-Parser und Docker-/Hostgrenzen bleiben Angriffsflächen. `importlib.metadata` liest installierte Metadaten; es beweist nicht, dass andere installierte native Bibliotheken unter jeder denkbaren Eingabe unerreichbar wären. Ein abweichendes Entrypoint oder zusätzlicher Import braucht einen neuen Review.

**Offene Startupgrenze:** Laut [Python-CLI-Dokumentation](https://docs.python.org/3.12/using/cmdline.html#cmdoption-I) impliziert `-I` unter anderem `-s`, jedoch **nicht `-S`**. Die globale [site-Initialisierung](https://docs.python.org/3.12/library/site.html) kann ausführbare `.pth`-Zeilen und `sitecustomize` importieren. Die genannten Standardbibliothek-Imports sind deshalb die expliziten Imports des unveränderten Prüfprogramms, keine vollständig gemessene Prozess-Importliste. Alle globalen Startuphooks des alten Images wurden hier nicht nachverfolgt. Diese Grenze bleibt Bestandteil des noch offenen tatsächlichen Runtime-/Native-Reviews; die historische Programmchecksumme wird nicht durch einen stillen `-S`-Umbau geändert.

**Zusätzlich festgestellte Lücke behoben:** Der alte Hostpfad beendete bei `subprocess.run(timeout=90)` den Docker-CLI-Prozess; `--rm` allein bewies keine daemonseitige Terminierung. Der Runner erzeugt jetzt zuerst einen eindeutig benannten, versuchsbezogen gelabelten Container und kennt dessen vollständige ID **vor** Ausführung. `docker start --attach --interactive` übergibt denselben begrenzten Umschlag an denselben unveränderten Prüfcode. Im `finally`-Pfad wird ausschließlich die zugehörige ID zwangsweise entfernt; erfolgreiche daemonseitige Abfragen müssen anschließend sowohl für Sessionlabel als auch ID Abwesenheit bestätigen. Timeout, fehlgeschlagenes Entfernen, abweichende ID oder nicht überprüfbarer Dockerzustand können keinen erfolgreichen Beleg liefern.

**9 fokussierte Runner-Tests bestanden**, darunter Timeout während Create/Start, fehlgeschlagene Entfernung, unerreichbarer Daemon, falsche Container-ID, unveränderte Isolation und unveränderte historische Prüfcodebytes. Ein [tatsächlicher Docker-Timeoutversuch](pr10-20261029/legacy-timeout-cleanup.json) mit dem modernen vorhandenen Backendimage führte einen festen Standardbibliothek-Sleep aus, erzwang nach zwei Sekunden einen Clienttimeout und wies Force-Remove sowie beide Abwesenheitsabfragen nach. Dabei wurden **weder altes Image noch Modelle oder Finanzdaten ausgeführt**. Die historische eingebettete Programmchecksumme bleibt `c8e41f8a48a5cdc9faaf320b35c0791b2521dcc04d7364d8895427b7ee337799`; bestehende Archiv-/Ergebnisverträge bleiben erhalten, neue Belege ergänzen `container_cleanup_verified=true`. Der tatsächliche isolierte Zielhost bleibt separat abzunehmen.

Vor einer echten Ausnahme fehlen weiterhin die tatsächliche Host-/Kernel-/Docker-Patchlage, überprüfte Laufparameter, komplette native Reachability-/Restrisikobewertung, Allowlist der vorhandenen Umschlaghashes und Aufrufzahl, Start-/Endinventar, gesonderte Securityentscheidung und Operatorentscheidung. Vorschlag für eine spätere Entscheidung: **ein** benannter Restore, je Umschlag höchstens 90 Sekunden, reales Betriebsfenster höchstens 24 Stunden innerhalb sieben Tagen nach tatsächlicher Freigabe. Diese Angaben sind keine erteilte Gültigkeit.

Re-Review ist vor jedem anderen Restore, bei neuem Finding/Advisory/Scannerstand, verändertem Image-/Verifier-/Archiv-/Konfigurationshash, geändertem Host/Docker/Kernel, anderen Imports, Rechten, Netzwerken, Mounts oder Ressourcen sowie nach Ablauf nötig. Keine Ausnahme für Critical genehmigt automatisch die 47 High-Befunde.

### Identifiervertrag

Das Inventar verwendet das historische Feld `cve` auch für den unveränderten GHSA-Identifier. Die in PR10 kontrolliert ergänzte Policy unterstützt deshalb ausdrücklich `finding_id` mit CVE-/GHSA-Syntax und behält `cve` als kompatiblen Alias. Widersprüchliche Aliase werden verworfen; die ID muss exakt zum gebundenen Finding passen. Syntaxprüfung allein bestätigt weder Advisoryherkunft noch Freigabe. Komponenten-/Digestbezug, technische Begründung, Reachability, Mitigations, echte Reviewer-/Approvalreferenz und begrenzte Zeiten bleiben Pflicht. Die Reviewvorlage unterscheidet zusätzlich `identifier_scheme` und bei GHSA `cve_id=null`; sie ist ausdrücklich keine autorisierte Policyeingabe. Eine erfundene CVE ist unzulässig.

## Abschließender neuer PR10-Scope

Der [frische PR10-Scan](pr10-20261029/core-rc1/inventory.json) bestätigt am
29.10.2026 erneut **1 Critical / 47 High** für denselben Recovery-Digest.
Die [Reviewvorlage v3](pr10-20261029/legacy-recovery-review-template-v3.json)
bindet diese neuen Scan-/SBOM-/Inventarbytes und den korrigierten Runner.
Sie ersetzt weder v2 noch deren alte Belege rückwirkend und erteilt keine
Ausnahme: alle 48 Paketzeilen bleiben `DRAFT_NOT_APPROVED`.
Die tatsächlichen [Core-](pr10-20261029/restore-core.json) und
[separaten Produktionsbuild-Restores](pr10-20261029/restore-standard-production.json)
prüfen unabhängig davon je **1’387 Dateien** und melden den bisherigen
Legacycheck sowie `container_cleanup_verified=true`. Diese Produzentenläufe
sind die neuen Restorebelege; der oben beschriebene V2-Integritätslauf bleibt
ausschließlich ein erneuter Vergleich des ursprünglichen Berichts.

## Ergebnis

Die additive Integritätsprüfung ist technisch vorhanden und hat die gelieferten vorhandenen Modellbytes und historischen Image-Metadaten tatsächlich gelesen und geprüft. Der ursprüngliche Restorebericht wurde ausschließlich erneut verglichen; ein frischer Restore oder eine eigene Prüfung wiederhergestellter DB-/S3-Archive ist damit nicht bewiesen. Historische Ausführbarkeit, normative Ablösung und Securityfreigabe bleiben getrennt offen. Der alte erforderliche Recovery-Digest und sämtliche historischen Originale/Hashverträge bleiben erhalten. **LEGACY_VERIFIER_STATUS=SECURITY_BLOCKED; PRIVATE_CORE_V1_RELEASED=false.**
