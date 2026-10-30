# Private Core V1 – Operatorübergabe

Stand **30.10.2026**. **NOT_RELEASED / NOT_APPROVED**.
Für die erste sichere Verwendung mit einem echten Depot fehlen tatsächliche
Securityentscheidungen, ein autorisierter privater Zielbetrieb, unabhängige
Recovery, private Originale und die reale Abnahme. Diese Schritte können
nicht allein durch weiteren Code erledigt werden. Es wurde kein Zielhost
oder Cluster bereitgestellt; der bestehende Auftrag lautet **lokal
vorbereiten**. Die nachstehende Übergabe erteilt keine Freigabe.

Die tatsächlichen neuen Prüfungen stehen im
[PR11.1-Verifikationsbericht](PR11_FINAL_VERIFICATION.md). Frühere Zahlen und
Läufe bleiben im [PR11-Abschlussbericht](PR11_ACCEPTANCE_REPORT.md) datiert;
sie werden nicht zu neuen Erfolgen umetikettiert.

## 1. Entscheidungen und ausführbare nächste Schritte

Jede Entscheidung bindet tatsächlichen Reviewer, UTC-Zeit, Ziel und exakten
Manifest-/Config-/Imagedigest. Namen und Freigabereferenzen privat erfassen;
Passwörter, Brokeroriginale, Tokens, TOTP-Seeds, CA-/Recovery-Schlüssel und
vollständige Secret-/Inspect-/Composeausgaben gehören nicht in GitHub/CI.

| Verantwortung / Entscheidung | Benötigte reale Eingaben | Konkrete Aktion | Überprüfbarer Erfolg | Bis dahin gesperrt |
| --- | --- | --- | --- | --- |
| **Securityreviewer:** Caddy-Restgefahr; danach separat Releaseoperator | Exaktes finales Inventar/SBOM, Caddy-Digest und Profil, tatsächliche Netz-/Adminexposition, Reviewerreferenz und Gültigkeitszeit | `CVE-2026-116587 / GHSA-mgcc-cww5-fp2q` anhand des [Securityreviews](PR11_SECURITY_FINAL_REVIEW.md) und der neuen PR11.1-Nachweise entscheiden: unterstützter getesteter Fix oder echte finding-/digest-/profilbezogene befristete Ausnahme nach Policy. Kein automatisches Approval | Dokumentierter begründeter Entscheid mit Beginn/Ablauf und Re-Reviewtriggern; alle Pflichtfelder echt. Ein Fix hat eigenen Scan sowie TLS-/CA-/S3-/Browser-/Restorenachweis; private Netze und Limits allein gelten nicht als Patch | `SECURITY_APPROVED`, Produktivstart |
| **Security-/Netz-/Zielverantwortliche:** übrige Restgrenzen | Native-/Unknown-/Medium-/Lowbefunde, CSP-Styleattributgrenze, tatsächlicher VPN-/DNS-/TLS-/Adminpfad und CA-Vertrauen | Native Grenzen und übrige Befunde reviewen; auf dem Ziel erlaubte/gesperrte Netzpfade, Adminschutz sowie korrekte/falsche CA prüfen. Windows und echtes Android getrennt prüfen | Tatsächliche, digest-/configgebundene Reviewbelege; Browser ohne TLS-Warnung nur mit richtiger CA, falsche CA scheitert; außerhalb des erlaubten privaten Zugangs kein Zugriff | Security-/Ziel- und echte Clientabnahme |
| **Release-/Runneroperator:** vollständiger Remoteaudit | Autorisierter isolierter Runner/Dockerdaemon, geschützter Transportweg, freigegebene Revision und die acht unveränderten Originalimages | Den [vorhandenen Remote-Auditplan](security/PR11_REMOTE_RELEASE_AUDIT_PLAN.md) und bestehenden Workflow verwenden. Export-/Empfangshashes, Plattform sowie Manifest-/Config-/Digestidentität vor Scan prüfen; erst danach einen ausdrücklich autorisierten Audit ausführen | Alle zwölf notwendigen Dienste aus acht Images mit tatsächlichen Original-SBOMs, aktuellem Scanner/DB und Scope geprüft. Fehlende Bytes/Identityabweichung bleiben `SCAN_INCOMPLETE`; normale API-/Web-CI ist kein vollständiger Releaseaudit | Behauptung vollständiger Remote-Releaseprüfung; nicht autorisierter Dispatch oder Imagetransfer |
| **Ziel-/Netz-/Secretbetreiber:** genau ein Primärziel | Tatsächlicher Composehost **oder** OpenShiftkontext/Namespace, privater Zugang/DNS/VPN, Registry und genaue Images, getrenntes Staging, Secrets und Persistenz | Die unten genannte vorhandene Installationsfolge am echten Ziel prüfen; reale Zielkonfiguration/Preflight/Plan neu erzeugen. Migration und Cutover erst gesondert autorisieren | Tatsächliches Staging, geschützte Secrets, Persistenz nach Neustart/Podersatz, private Clients und datenerhaltender Rollback belegt. Keine Aussage allein aus lokalem Render oder Argo-Sync | Zieldeployment, produktive Migration und Cutover |
| **Backup-/Recoverybetreiber:** unabhängiger Betrieb | Physisch **oder** administrativ getrenntes Ziel, Verschlüsselungsnachweis, getrennte Recoverykeys/Secrets/CA, Dienstkonto, Tageszeitplan, Retention, Kapazität und Alarmempfänger | Vorhandene Backupengine benutzen; Writer quieszieren. Tagesjob wirklich ausführen, fehlendes Ziel/verpassten Lauf kontrolliert prüfen, Alarmempfang bestätigen und von genau diesem unabhängigen Ziel isoliert restaurieren | Original-/SQL-/S3-/Hash-/Loginbelege stimmen; Archivfall erfüllt alle zehn Verträge und 66 Pins ohne alten Python-Start. Fehlendes Ziel erzeugt keinen lokalen Fallback. Tatsächliche Recoveryzeit/-verlustgrenze, Alarmempfang und neue Sicherung nach Neustart dokumentiert | Aufnahme echter Originale und Aussage eines sicheren Dauerbetriebs |
| **Autorisierter Datenoperator**, getrennt Betriebs-/Aktivierungsentscheid | ECB-Rechtebeleg, beide konkreten EXR-Reihen, ganzes Datumsfenster, Abruf-/Rawarchiv-/Analyserechte, Attribution, Quote und nächstes Review; freigegebener Ziel-/Egresspfad | [Vorhandenen Quellenbogen](data/PR11_SOURCE_OPERATOR_REVIEW.md) privat ausfüllen; Review erfassen, separat aktivieren; kurzes erlaubtes Intervall vorschauen/abrufen. Identisch wiederholen und an einem späteren tatsächlichen Veröffentlichungstag erneut prüfen | Echte Rawbytes/SHA-256, Job-/Canonical-/Leg-IDs und Kenntniszeiten; beide ECB-Legs desselben Referenztags, korrekter Decimal-Kreuzkurs CHF je USD = CHF je EUR / USD je EUR, keine Canonicalduplikate. Automatik zusätzlich durch freigegebenen Zeitplan und wirklich geplanten Abruf belegt | Jeder nicht freigegebene Providerrequest, `LIVE_SOURCE_VERIFIED` und `AUTOMATIC_REFRESH_VERIFIED` |
| **Depotinhaber / Importoperator / fachlicher Prüfer:** erstes echtes Depot | Eigener privater Benutzer, unveränderte Brokertransaktionen/Bestands-/Cashauszüge, Gebühren/Steuern, Dividenden/Splits, Listing-/Kurs-/FX-Belege und gleicher Bewertungsstichtag | Nach Security-/Ziel-/Recoveryfreigabe ein Portfolio mit mindestens einem Konto anlegen; bestehenden Preview/Mapping/Commit nutzen. [Realen Abgleich](PR11_REAL_PORTFOLIO_ACCEPTANCE.md) vollständig durchführen, Differenzen belegen und genau dieses Depot unabhängig sichern/restaurieren | Mengen, Cash je Währung, Gebühren/Steuern, Actions ohne Doppelzählung, Einstand, Preise/FX und CHF-Gesamtwert gegen echte Originale erklärt; Korrekturen auditierbar, Originale/Restore erhalten | `REAL_PORTFOLIO_VERIFIED` und Abschluss des echten Piloten |
| **Unabhängige Person / Testleitung:** Bedienbarkeit | Tatsächliche Person, vorhandene isolierte Testumgebung, eigener Testbenutzer und vorhandene klar synthetische Dateien; exakter Build, Gerät/Browser | [PR7-Protokoll](ux/PR7_BEGINNER_TEST.md) ohne Einführung ausführen: Login, Portfolio/Konto, CSV, Position, Bewertung, Datenlücke, Korrektur, Quelle; zusätzlich Einstellungen vor bestehendem Logout finden. Hilfen und Abbrüche tatsächlich beobachten | Privater pseudonymisierter Beobachtungsbogen mit Dauer/Fehlklicks/Verständnis; konkrete reproduzierte Probleme gezielt korrigiert und erneut geprüft. Automatisierte Browserläufe bleiben getrennte Evidenz | Menschliche UX-Abnahme; bis dahin `PENDING_USER_TEST` |

ECB ist der priorisierte automatische FX-Weg, keine Pflicht für eine manuelle
Core-V1-Nutzung. Ein rechtmäßiger manueller Kurs-/FX-/Actions-Import bleibt
zulässig. Allgemeine ISIN-Unterstützung beweist keine konkrete Kurslizenz oder
Listing-/Actionscoverage. OpenFIGI ist separat für Mapping **einschließlich
Speicherung und Identitätsnutzung** zu reviewen und ausdrücklich auszuwählen;
der technische `mapping`-Check allein beweist diese Rechte nicht. Es ist keine
Kursquelle. Quellen-/Modell-/Strategiegates bleiben unabhängig.

## 2. Installation mit den vorhandenen Werkzeugen

1. **Einen echten Zielweg wählen und autorisieren.** Aktueller
   [Core-Scope](../ops/releases/pr11-core-v1-scope.json): zwölf notwendige
   Dienste, acht Images. Finales gültiges Manifest, Inventar, öffentliche
   Configbytes und private Zielinputs gemeinsam binden; keine Digests durch
   CI-Neubauten, Tags oder andere Registries ersetzen.
2. **Compose:** [`ops/core_preflight.py`](../ops/core_preflight.py) mit finalem
   Scope/Inventar, geschütztem Env und neuem Ausgabepfad am Ziel ausführen;
   [`ops/core_install_plan.py`](../ops/core_install_plan.py) mit demselben
   Scope/Inventar/Env, frischem Preflight und finalem Manifest erzeugen.
   Der Plan startet nichts. Erst separat freigegebene Schritte aus der
   [Installationsanleitung](operations/PRIVATE_CORE_INSTALLATION.md) ausführen:
   neue Volumes, Infrastruktur/TCP-DB-Prüfung, CA-Export, manuelle Migration,
   anschließend Core mit `--no-build --pull never`. Alte Root-CA-Volumes
   nicht automatisch rekursiv reparieren.
3. **OpenShift / Red Hat OpenShift GitOps:** vorhandenen
   [GitOps-Ablauf](operations/OPENSHIFT_ARGOCD.md) und
   [`ops/openshift/preflight.py`](../ops/openshift/preflight.py) verwenden.
   Offline-Draft bleibt `DRAFT_NOT_DEPLOYABLE`; echter serverseitiger Dry-Run,
   Operator-/Argo-Version, effektive RBAC, Namespace-UID/Gruppen, restricted
   SCC, Service-CA/Route, NetworkPolicies und CSI/PVC müssen am Cluster geprüft
   werden. Kein `anyuid`, Root-Init, automatischer Migrationshook oder PVC-Prune.
   Manueller Infrastruktur-Sync, separat genehmigte Migration und Runtime-Sync
   derselben Application bleiben getrennt. OpenShiftbackup nutzt die
   [bestehende Transportanbindung](../ops/openshift_backup.py), exakte Pod-
   und Imagebindungen, stillstehende Writer und eine durchgehend gehaltene Lease.
4. **Recovery vor echten Originalen nachweisen.** Die bestehenden
   [`backup.py`](../ops/backup.py)/[`restore_verify.py`](../ops/restore_verify.py)-
   Verträge verwenden. Für vorhandene Researcharchive gilt
   [ADR-029](decisions/ADR-029-private-core-archive-recovery.md): unabhängige
   exakte ursprüngliche RC-/Hashanker, Metadata-TAR und **vor dem Restore**
   gepinnte aktuelle Erwartungen getrennt schützen. CRLF-Originalbytes sind
   nicht durch einen LF-Gitclone ersetzbar. Originalmodell/Locks/66 Pins
   bleiben unverändert; historische numerische Reproduktion wird nicht behauptet.
   Ein neues echtes Depot benötigt seine eigenen Originale/Erwartungen,
   keine künstlichen Researchmodelle. Der alte dynamische Legacypfad bleibt
   außerhalb des täglichen Core-Restores **SECURITY_BLOCKED**.

Der Commit **`bc0f8d8`** ergänzt lediglich das
[`gitops-demo`-Draftoverlay](../ops/openshift/overlays/gitops-demo/README.md).
Null Replikate, Platzhalterregistry und fehlende echte Secret-/Storage-/
Zielinputs sind keine Installation. Namespaceanpassung beweist weder einen
verfügbaren Cluster noch ausreichende Controllerrechte; bei einem geteilten
Namespace zusätzlich tatsächliche NetworkPolicyselektoren und bestehende
Ressourcen prüfen. Die früher bestätigte fehlende Zielverfügbarkeit bleibt
maßgeblich.

## 3. Freigabe, Abschluss und Stop

Ein C:-Stagingordner, eine ACL, ein erfolgreicher lokaler Restore oder grüner
CI-/Argo-Status ersetzen weder unabhängige Verschlüsselung/Schlüsselrecovery
noch echte Security-/Ziel-/Operatorfreigaben. Das historische synthetische
Portfolio bleibt **CHF 10’180 nur am 26.10.2026, 15:18:05.987683 UTC**;
heute veraltete Daten bleiben `STALE_PRICE`, fehlende Daten niemals Null.

Bis zur belegten jeweiligen Abnahme bleiben `SECURITY_APPROVED=false`,
`TARGET_DEPLOYED=false`, `REAL_PORTFOLIO_VERIFIED=false` und
`PRIVATE_CORE_V1_RELEASED=false`. Quellenversorgung und unabhängige
Bedienabnahme bleiben offen. Weder Forecasts noch Empfehlungen werden durch
diese Übergabe validiert oder freigegeben.

**STOP nach den tatsächlich unabhängig ausführbaren technischen Prüfungen.**
Der nächste Schritt sind die oben benannten realen Entscheidungen und
Nachweise. Keine neue Architektur, zusätzlichen synthetischen Testarchive,
automatischen Pushes, Releases, Installation/Migration/Cutover,
Quellenapprovals, Modellpromotion oder Brokerhandel beginnen.
