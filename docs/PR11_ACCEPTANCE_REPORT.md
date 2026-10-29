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
