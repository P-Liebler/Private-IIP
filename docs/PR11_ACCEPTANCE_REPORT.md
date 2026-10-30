# PR11 – Final Release Gates und erste reale Abnahme

Stand **29.10.2026**: **LOCAL_TECHNICALLY_VERIFIED /
SECURITY_OPERATOR_DECISION_REQUIRED / NOT_RELEASED**.
Die unabhängig lokal lösbaren Arbeiten sind abgeschlossen. Die verbleibenden
realen Entscheidungen werden nicht durch eine neue Entwicklungsphase ersetzt.

## 1. Releaseentscheidung

**Private-IIP ist noch nicht mit einem echten privaten Portfolio abgenommen.**
Der Core-Archivrestore benötigt den verwundbaren historischen Python-Prozess
jetzt fachlich und technisch nicht mehr. Vollständige Wiederherstellung und
Originalprüfung bleiben zwingend. Caddy und die tatsächlichen Betriebs-/
Daten-/Benutzerabnahmen benötigen weiter echte Entscheidungen.

| Zustand | Tatsächlicher Stand |
| --- | --- |
| `TECHNICALLY_VERIFIED` | Ja, für dokumentierte lokale Verträge und exakte Images; keine reale Zielabnahme |
| `SECURITY_TECHNICALLY_RESOLVED` | **Nein als Gesamtaussage**; Core-Legacy-Abhängigkeit vertragstreu getrennt, Caddyentscheidung offen |
| `SECURITY_OPERATOR_DECISION_REQUIRED` | **Ja**; keine automatische Securityfreigabe |
| `SECURITY_APPROVED` | Nein |
| `TARGET_DEPLOYED` | Nein – `TARGET_NOT_AVAILABLE` |
| `LIVE_SOURCE_VERIFIED` / `AUTOMATIC_REFRESH_VERIFIED` | Nein – `LIVE_SOURCE_BLOCKED_BY_APPROVAL` |
| `REAL_PORTFOLIO_VERIFIED` | Nein – `REAL_PORTFOLIO_PILOT_PENDING` |
| Menschliche Bedienabnahme | `PENDING_USER_TEST` |
| `PRIVATE_CORE_V1_RELEASED` | **Nein** |
| `FORECASTS_VALIDATED` / `RECOMMENDATIONS_VALIDATED` | Nein; bisherige unabhängige Gates bleiben erhalten |

## 2. Technisch abgeschlossene Arbeiten

- Tatsächlichen HEAD und `origin/main` geprüft: **d0feaa67f1505ef247fb5dd199938f0f592230d7**.
  [Angeforderter CI-Lauf](https://github.com/P-Liebler/Private-IIP/actions/runs/40900032608)
  erfolgreich mit 321/192/31; vollständiger Core-/Recovery-Audit war nicht
  angefordert. Originalartefakt und Hashes gesichert, Ergebnis nicht mit einer
  Releasefreigabe gleichgesetzt.
- [ADR-029](decisions/ADR-029-private-core-archive-recovery.md): expliziter
  Scope V2 mit **zwölf notwendigen Diensten / acht Images**. V1-Pflichten,
  ursprüngliche Modelle, Locks, Scanberichte und Archivhashes bleiben erhalten.
  Das alte Image ist separat archiviert und sein dynamischer Researchpfad
  weiterhin **SECURITY_BLOCKED**; historische Inferenz wurde nicht behauptet.
- Vorhandenen Restoreproducer erweitert: tatsächliche SQL-/S3-Wiederherstellung,
  vollständiger Raw-Readback, alle zehn Archivverträge, Modelloriginale,
  historische Locks/SBOM/66 Pins. Alte Modellanker und aktuelle, vorab unabhängig
  gepinnte Backuperwartungen sind getrennt. Spätere Backups und wachsende
  Aggregate werden nicht fälschlich auf den PR10-Snapshot festgeschrieben.
- Caddy neu anhand offizieller Patches, Importkette und konkreter Profile
  geprüft. Kein belegter v3-Fix und keine sichere kleine Entfernung ohne
  CA-Vertragsänderung. Keine ungeprüfte Kryptografie- oder Infrastrukturmigration.
- Alle erforderlichen unveränderten Imagebytes frisch gescannt, **12/12
  Original-SBOMs** formal validiert; normaler Produktionsbuild separat gescannt.
  Kein Neubau oder Digestersatz. Core über acht Images: **0 Critical / 1 High**
  bei Caddy. Optionales Legacyimage weiterhin 1 Critical/47 High laut
  unverändertem historischem Scan.
- Installationsplan und neuer geschützter lokaler Preflight konsistent:
  **TECHNICAL_CONFIGURATION_VALID / SECURITY_BLOCKED / NOT_APPROVED**.
  OpenShift-/Argo-CD-Vorbereitung erhalten und Offlineprüfung durchgeführt;
  kein Clusterzugriff oder simuliertes Zieldeployment.
- Quellenstatus nach den kontrollierten Browserläufen tatsächlich read-only
  geprüft: ECB/OpenFIGI UNKNOWN und deaktiviert, ohne Reviewfreigabe.
  Collection, Forward-Scheduling, Testmodus und temporäre Operatorrollen aus.
  Keine externen Finanzendpunkte aufgerufen oder Quellen freigegeben.

## 3. Tatsächliche Regression und Aussagegrenzen

[Maschinenlesbarer Abschlussbeleg](security/pr11-20261029/regression-final.json).

| Prüfung | Neues tatsächliches Ergebnis |
| --- | --- |
| Backend | **321 Tests je unverändertem Core- und normalem Produktionsimage**, ursprüngliche Pins davor/danach gleich |
| Host | **210 Tests**, einschließlich 18 begründeter neuer Archiv-/Checkpoint-/Producerfälle; PR10-Baseline 192 erhalten |
| Browser | **31 unterschiedliche Fälle geprüft**: zuerst 30/31 erfolgreich; der korrigierte verbleibende Fall danach separat 1/1 erfolgreich |
| Statische Prüfung | Backend-Ruff/Format/Mypy und geänderte Ops-Dateien erfolgreich |
| Frontend | Lint, Typecheck und abgeschlossener Standalone-Build erfolgreich; Lint/Typecheck nach Testkorrektur erneut erfolgreich |
| Native / Schema | Beide nativen Runtimeproben, Fresh Migration und Schema Drift erfolgreich; weiterhin `0021_ui_requests` |
| Core-Restore | **1’387 Dateien / 1’378 aus S3 zurückgelesene Objekte / zehn Archivverträge / 66 Pins**, erfolgreiche Bereinigung, kein historischer Python-Start |
| Separater Produktionsbuild-Restore | Dieselben vollständigen Prüfungen separat erfolgreich |

Der Browserfehler war ein nachgewiesener Test-Synchronisationsfehler:
Beim zweiten CSV-Commit lief die HTTP-Anfrage noch, während der Test bereits
nach fünf Sekunden den Erfolgsstatus erwartete. Der Test wartet nun die
tatsächliche Antwort ab, verlangt HTTP 200 und **null neue Buchungen**, danach
denselben UIstatus. Kein Produktfehler oder menschliches UX-Problem wurde
daraus erfunden; Oberfläche und Anwendungsimages bleiben unverändert.
Die ursprüngliche 30/31-Datei bleibt erhalten. **Es wird kein einzelner neuer
31/31-Gesamtlauf behauptet.** Für die gezielte Wiederholung wurde die bestehende
Setupfixture wiederverwendet.

Für beide vollständigen Restores wurde derselbe vorhandene versiegelte
PR10-Backupsatz unverändert kopiert. Keine neuen manuellen synthetischen
Finanzarchive zur Erhöhung der Testzahlen. Die historischen **CHF 10’180**
gelten weiterhin ausschließlich am **26.10.2026, 15:18:05.987683 UTC**;
heute bleibt der alte Preisstand **STALE_PRICE**. Forecasts, Outcomes,
Dokument-/Quellen-/Modell-/Ledgerhistorien bleiben erhalten. Der Masterplan
behält seine **212 Hauptabschnitte**; nur die begründete Recoverytrennung ist
in 152/157 ergänzt.

## 4. Konkrete Operatorübergabe

| Was entscheiden / handeln? | Wer autorisiert? | Geschützte Eingaben und überprüfbarer Erfolg | Bis dahin gesperrt |
| --- | --- | --- | --- |
| Caddyfix oder echte begrenzte finding-/digest-/profilbezogene Entscheidung; weitere native/Unknown-/CSP-/TLS-/Netzreviews | Autorisierter Securityreviewer; getrennt Releaseoperator | Exaktes Manifest, Inventar, echte Reviewerreferenz und Gültigkeit; alle Policyanforderungen tatsächlich erfüllt | `SECURITY_APPROVED`, Produktivstart |
| Genau einen tatsächlich vorhandenen Composehost oder OpenShift-Namespace bereitstellen und Staging abnehmen | Ziel-/Netz-/Secretbetreiber | Privater Zugang, DNS/VPN/TLS, Registry und exakte Images, persistente Volumes, Secrets; echte Windows-/Androidprüfung, Neustart und Rollback | Zieldeployment, produktive Migration/Cutover |
| Unabhängige verschlüsselte Recovery samt getrennten Schlüsseln, Originalankern/Metadata-TAR und Zeitplan betreiben | Backup-/Recoveryverantwortlicher | Tatsächliche unabhängige Zielidentität, Verschlüsselung, Tagesjob/Retention/Kapazität, bestätigter Alarmempfang und isolierter Restore von diesem Ziel | Sicherer Betrieb echter Originale |
| Optional automatische ECB-Versorgung aktivieren | Quellenrechteoperator; danach separater Aktivierungsoperator | Exakte CHF-/USD-Serien, Datumsbereich, Archiv-/Analyserechte und Review; echter Abruf mit Originalhash, beide Beine am gleichen Referenztag, USD/CHF-Kreuzkurs, idempotente Wiederholung und späteres echtes Update | `LIVE_SOURCE_VERIFIED`, `AUTOMATIC_REFRESH_VERIFIED` |
| Erstes kleines echtes Depot erfassen und abgleichen | Depoteigentümer und nach Freigaben verantwortlicher Operator | Geschützte Brokeroriginale, ein Portfolio/mindestens ein Konto, tatsächliche Transaktionen/Cash/Aktionen/Kurse/FX/Stichtag; alle Differenzen erklären, echten Backup-/Restorebeleg prüfen | `REAL_PORTFOLIO_VERIFIED` |
| Zehn PR7-Aufgaben ohne Einführung tatsächlich beobachten | Unabhängige Testperson und verantwortlicher Tester | Geschütztes pseudonymes Protokoll mit Gerät/Version, Hilfen, Fehlklicks/Abbrüchen; begründete Probleme gezielt nachprüfen | Menschliche Bedienabnahme |

Der bereits bekannte Nutzerentscheid bleibt: **kein Zielhost verfügbar;
lokal vorbereiten**. Ein C:-Ordner ist kein unabhängiges Recoveryziel.
OpenShift/Red Hat OpenShift GitOps mit Argo CD ist vorbereitet, nicht verfügbar
oder automatisch autorisiert. Kein erneutes Erfragen bereits beantworteter
Host-/ISIN-Fragen.

ECB ist der priorisierte automatische Weg. **Rechtmäßiger manueller Import
bleibt ein gültiger Core-V1-Weg** und benötigt keine fiktive universelle
Kursquelle oder automatische Collection. OpenFIGI benötigt einen eigenen
Mapping-/Speicherrechteentscheid und explizite Listingwahl; es ist keine
Kursquelle. Reale Listing-/Lizenz-/Corporate-Action-Abdeckung wird nicht aus
allgemeiner ISIN-Unterstützung abgeleitet. Private Originale und Schlüssel
gehören nicht nach Git oder CI.

## 5. Verbindliche Berichte und Abschluss

- [Securityfinalreview](PR11_SECURITY_FINAL_REVIEW.md)
- [Installations-/Releasecheckliste](PR11_CORE_RELEASE_CHECKLIST.md)
- [Livequellenabnahme](PR11_LIVE_SOURCE_ACCEPTANCE.md)
- [Echter Portfolio-Pilot](PR11_REAL_PORTFOLIO_ACCEPTANCE.md)
- [Unabhängige Bedienabnahme](PR11_USABILITY_ACCEPTANCE.md)

Der [neue lokale RC1](../ops/releases/pr11-core-v1-rc1-manifest.json) bindet
finale Arbeitsbytes, Scope, Digests, aktuelle Erwartungen, Security-/SBOM-/
Restore-/Regressionsbelege und unveränderte Locks. Er bleibt
**NOT_RELEASED_OPERATOR_AND_SECURITY_GATES_REQUIRED**, kein Remote- oder
Operatorapproval. Alte PR8-/PR9-/PR10-Manifeste werden nicht nachträglich
repariert. Alle eigenen Restoreprojekte sind bereinigt, eigene Prüfdienste
gestoppt und kontrollierte Rollen zurückgesetzt.

**STOP.** Keine zusätzliche Architektur, künstliche Entwicklungsphase,
automatische Installation/Migration, Quellenapproval, Modellpromotion,
Brokerhandel, Push oder Veröffentlichung. Der nächste Schritt ist die oben
konkret benannte reale Autorisierung und Abnahme.

---

## Ergänzung PR11.1 – Tatsächliche Nachweise vom 30.10.2026

Dieser datierte Zusatz ergänzt den unveränderten Bericht vom 29.10.; die
ursprünglichen 30/31 im Gesamtlauf und die anschließenden 1/1 bleiben mit ihren
Originalbelegen erhalten. Der **neue vollständige Standalone-Browserlauf
besteht mit 31/31 in einem einzigen Lauf** (`FULL_BROWSER_REGRESSION_PASSED`).
Er verwendet das vorhandene Setup, behält die finanziellen Assertions und
bestätigt die Rücksetzung des Testmodus und der temporären Rollen. Beide
unveränderten Backendimages bestehen erneut mit **je 321 Tests**; Frontend-
Lint, Typecheck und der vor dem Browserlauf abgeschlossene Build sind erfolgreich.
Die neuen tatsächlichen Abschlussbelege sind im
[PR11.1-Verifikationsbericht](PR11_FINAL_VERIFICATION.md) zusammengeführt;
weitere Prüfungen werden nicht aus älteren Läufen als neu abgeleitet.

Der [neue CI-Originalindex](security/pr11-1-20261030/remote-ci.json) bindet den
angeforderten Run **40907365492** auf `cb1489962c92fdd8fcb8fed4133cea11e836e28c`
und den tatsächlichen HEAD-Run **41018607349** auf
`bc0f8d8872e879c01bcbe05198fc9095575fab6d`. Beide bestätigen
**Verify/Security erfolgreich mit 321/210/31**. Der vollständige Core-/
Recoveryaudit ist bei beiden **SKIPPED_NOT_REQUESTED_NOT_VERIFIED**; normale
CI-Erfolge erteilen keine vollständige Release- oder Securityfreigabe.

`bc0f8d8` ergänzt ein deaktiviertes `gitops-demo`-Draftoverlay, keinen
verfügbaren Cluster und keine Zielabnahme. Es wurden keine tatsächlichen
Security-/Quellenapprovals, privaten Originale oder unabhängige Testperson
bereitgestellt. `SECURITY_OPERATOR_DECISION_REQUIRED`, `TARGET_NOT_AVAILABLE`,
`LIVE_SOURCE_BLOCKED_BY_APPROVAL`, `REAL_PORTFOLIO_PILOT_PENDING` und
`PENDING_USER_TEST` bleiben bestehen; **PRIVATE_CORE_V1_RELEASED=false**.
Die [konkrete Operatorübergabe](PRIVATE_CORE_V1_OPERATOR_HANDOVER.md) benennt
Rollen, reale Eingaben, Aktionen und Erfolgskriterien. Danach gilt weiterhin
STOP statt einer neuen künstlichen Entwicklungsphase.

Die inzwischen abgeschlossenen [frischen vollständigen Imagescans](security/pr11-1-20261030/core-rc1/inventory.json)
und die [formale SBOM-Prüfung](security/pr11-1-20261030/core-rc1/sbom-validation.json)
belegen **12/12 notwendige Dienste, acht verschiedene exakte Images und zwölf
gültige Original-SBOMs**. Über die acht Imageidentitäten ergibt sich
**0 Critical / 1 High**, weiterhin Caddy; keine Securityfreigabe.

**Nachträgliche Repositoryänderung am 30.10.:** `bc0f8d8` bezeichnet den
anfangs beobachteten HEAD und seinen oben dokumentierten CI-Lauf. Während der
lokalen Prüfung kamen die Nutzercommits `41249ee` und anschließend
**`64f7445b4aef10a7b7dabe6a9a62dd051a53d1a1`** hinzu; letzterer ändert drei
OpenShift-PVC-JSONdateien auf `storageClassName=truenas-nfs`. Das ist kein
Nachweis eines verfügbaren Clusters. Der [neue Namespace-/Renderbeleg V2](security/pr11-1-20261030/gitops-demo-offline-v2.json)
prüft die tatsächlich geänderten Dateien: acht Workloads mit null Replikaten,
Namespace `gitops-demo` und drei gerenderte PVCs mit dieser StorageClass.
Deren tatsächliche Existenz, CSI-/UID-/Persistenzverhalten und Clusteradmission
bleiben ungetestet. Der anfängliche Beleg bleibt erhalten; der neue Commit
wird nicht mit dem alten CI-Lauf gleichgesetzt.

**Abschluss der tatsächlichen PR11.1-Regression:** Der
[neue Gesamtbeleg](security/pr11-1-20261030/regression-final.json) bestätigt
321 Backendtests je Image, **210 Hosttests erneut nach den PVC-Änderungen**,
31/31 im vollständigen Browserlauf, Ruff/Format/Mypy, Frontend-Lint/Typecheck/
Build sowie native Proben und Fresh Migration/Drift für beide Backendimages.
[Core-Restore](security/pr11-1-20261030/restore-core.json) und
[separater Produktionsbuild-Restore](security/pr11-1-20261030/restore-standard-production.json)
bestehen jeweils mit **1’387 Dateihashes, 1’378 S3-Readbackobjekten, zehn
Archivverträgen, 66 Metadatenpins und erfolgreicher Bereinigung**. Derselbe
unveränderte Backupsatz und unabhängig gepinnte Erwartungen wurden verwendet;
keine historische Python-Ausführung und keine unabhängige reale Zielrecovery
werden behauptet.

Der [erste fehlgeschlagene Standardrestore](security/pr11-1-20261030/restore-standard-production-attempt-v1.json)
bleibt fehlgeschlagen erhalten. Die [Diagnose](security/pr11-1-20261030/windows-path-diagnosis.json)
beweist die Windows-Pfadgrenze: 683 unveränderte Dateien mit 261 Zeichen langen
Vollpfaden waren über den normalen Win32-Pfad unsichtbar; über den erweiterten
Pfad bestehen alle 1’378 strengen Hashprüfungen. Ein weiterer Kopierversuch
scheiterte vor Docker an WinError 3. Erst der neue vollständige Lauf mit kurzem
Stagingroot besteht unverändert; **kein S3-Datenverlust und keine gelockerten
Archivgates**. Der historische CHF-10’180-Stichtag und heutiges `STALE_PRICE`
bleiben erhalten.

Der [tatsächliche neue HEAD-CI-Lauf 41021964813](security/pr11-1-20261030/head-ci-final.json)
auf `64f7445…` ist ebenfalls erfolgreich mit 321/210/31; sein vollständiger
Core-/Recoveryaudit bleibt **NOT_REQUESTED_NOT_VERIFIED**. Spätere lokale
Arbeitsbytes werden dadurch nicht nachträglich als remote getestet ausgegeben.
