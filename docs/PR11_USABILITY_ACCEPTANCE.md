# PR11F – Unabhängige Bedienbarkeitsabnahme

Stand **29.10.2026**. **PENDING_USER_TEST**.
Eine unabhängige Person wurde nicht bereitgestellt oder beobachtet. Es gibt
keine erhobene menschliche Erfolgsquote, Dauer, Fehlklickzahl oder Aussage zum
Verständnis. Die PR6-/PR10-Oberfläche und das bestehende Design bleiben erhalten.

## 1. Technische Regression getrennt halten

Aktuell sind alle **31 unterschiedlichen Browserfälle** geprüft:
zuerst 30/31 im vollständigen Lauf, danach der eine korrigierte Fall separat
1/1. Beim zweiten CSV-Commit wartet der Test jetzt auf HTTP 200 und null neue
Buchungen, bevor er denselben Erfolgsstatus prüft. Der ursprüngliche 5s-
Synchronisationsfehler und sein Lauf bleiben erhalten; kein App-/menschliches
UX-Problem wird daraus erfunden. Die bestehende Setupfixture wurde für die
gezielte Wiederholung wiederverwendet. [PR11-Regressionsbeleg](security/pr11-20261029/regression-final.json).
Es wird kein einzelner neuer 31/31-Gesamtlauf behauptet; Testmodus und Rollen
sind anschließend zurückgesetzt.

Die [PR10-Browserregression](security/pr10-20261029/regression-final.json)
umfasst **31 bestandene Fälle** am abgeschlossenen Standalone-Build mit
anschließend zurückgesetztem Testmodus und temporären Rollen. Das ist ein
datierter technischer Nachweis. Tatsächliche neue PR11-Läufe stehen separat
im [Gesamtbericht](PR11_ACCEPTANCE_REPORT.md). Weder ein alter noch ein neuer
automatisierter Lauf ersetzt diesen unabhängigen Benutzertest oder eine echte
Windows-/Android-/VPN-Zielprüfung.

Automatisierte Hauptabläufe und finanzielle Assertions erhalten: Anmeldung,
Portfolio/Konto, CSV-Vorschau/Zuordnung/Commit, Wiederholung, Bewertung/FX,
Korrektur/Voids, Herkunft, Datenlücken, Einstellungen, mobile Navigation und
Gates. Sichtbare UI-Capabilities erteilen keine Quellen- oder Operatorrechte.
Ein Quellen-/LLM-Ausfall muss den vorhandenen fehlenden/gesperrten Zustand
zeigen; kein Nullwert und keine erfundene Erklärung darf ihn verdecken.

## 2. Bestehendes PR7-Protokoll ausführen

Das [PR7-Anfängerprotokoll](ux/PR7_BEGINNER_TEST.md) bleibt das Aufgaben- und
Beobachtungsformat. Die dortige Abmeldung wird erhalten; PR11 ergänzt im selben
Ablauf die ausdrücklich geforderte Suche nach den Einstellungen **vor** dem
Logout. Kein neues paralleles Testframework und kein neues synthetisches
Archiv wird dafür angelegt.

Solange Security/Zielbetrieb offen sind, nur die vorhandene isolierte
synthetische Umgebung und vorhandene klar bezeichnete Testdaten verwenden.
Eigener Testbenutzer und vorberechnete Erwartungswerte bleiben getrennt von
echten Depotdaten. Die Person arbeitet ohne technische Einführung; jede
tatsächlich nötige Hilfe wird dokumentiert.

| Aufgabe | Erfolg im unabhängigen Test | Aktuell |
| --- | --- | --- |
| Anmelden | Eigenständig zum vorbereiteten Konto gelangen | NICHT BEOBACHTET |
| Portfolio erstellen | CHF-Portfolio ohne verdeckte Hilfe anlegen | NICHT BEOBACHTET |
| Konto hinzufügen | Tatsächliche Zuordnung zum vorgesehenen Testportfolio verstehen | NICHT BEOBACHTET |
| CSV importieren | Vorschau, Zuordnung und ausdrückliche Übernahme verstehen | NICHT BEOBACHTET |
| Position finden | Entstandene Menge und zugehöriges Konto zeigen | NICHT BEOBACHTET |
| Bewertung verstehen | Wert, Zeitpunkt, Quellen und unvollständige Inputs in eigenen Worten erklären | NICHT BEOBACHTET |
| Datenlücke erkennen | Fehlenden/veralteten Kurs erkennen, ohne ihn für Null zu halten | NICHT BEOBACHTET |
| Korrektur durchführen | Vorhandene Korrekturdatei richtig nutzen und Ergebnis prüfen; Original bleibt erhalten | NICHT BEOBACHTET |
| Datenquelle prüfen | Quelle, Alter, Freigabestatus und tatsächliche Aktualisierungsmöglichkeit erkennen | NICHT BEOBACHTET |
| Einstellungen finden | Einstellungen ohne vorherigen Navigationshinweis finden | NICHT BEOBACHTET |
| Abmelden | Logout und nicht mehr zugängliches privates Portfolio prüfen | NICHT BEOBACHTET |

## 3. Konkrete Übergabe und Auswertung

| Entscheidung | Handlung | Wer autorisiert? | Geschützte Eingaben | Erfolg | Bis dahin gesperrt |
| --- | --- | --- | --- | --- | --- |
| Unabhängige Testperson | Eine tatsächlich nicht an der Implementierung beteiligte Person und Testleitung benennen | Person und Testleiter | Einverständnis, pseudonymisierte Kennung, tatsächlicher Termin/Gerät | Vollständiger Hauptablauf ohne Einführung beobachtet | Behauptete menschliche UX-Abnahme |
| Sicherer Testzugang | Vorhandene isolierte synthetische Umgebung und eigenen Testbenutzer bereitstellen | Verantwortlicher Test-/Umgebungsbetreiber | Zugangsdaten privat, Build/Digest, Browser und Startzustand | Kein Kontakt mit echten Depotoriginalen oder automatischen Finanzquellen | Test mit realen Originalen ohne separate Freigaben |
| Beobachtete Fehler | Pro Aufgabe Dauer, Hilfen, Fehlklicks, Unsicherheit, Fehlermeldung und Abbruch erfassen | Testleitung / Person | Privater Beobachtungsbogen, redigierte Reproduktionsschritte | Tatsächliche priorisierte Probleme nachvollziehbar reproduzierbar | Erfundenes UX-Backlog und pauschales Redesign |
| Gezielte Nachbesserung | Nachgewiesenen Fehler beheben und betroffene Hauptaktion erneut prüfen | Produktverantwortlicher innerhalb des konkreten Befunds | Fehlerbeleg, exakter getesteter Build, erneute Beobachtung | Finanziell korrektes und verstandenes Ergebnis ohne zusätzliche Hilfe | UX-Gate bei offenem blockierendem Befund |

Personenbezogene Rohprotokolle, Zugangsdaten und private Originale bleiben
außerhalb Git/CI. Nur redigierte Befunde und zulässige Evidenzbezüge publizieren.
Ein tatsächlich bestandener Anfängertest mit synthetischen Daten bleibt
separat von Security, Quellenfreigabe, echtem Brokerabgleich und Recovery.

**Menschliche Bedienbarkeit bleibt unvalidiert.** Nach technischer Regression
ist die konkrete unabhängige Beobachtung der nächste Schritt; weitere
automatisierte Fälle werden nicht als Ersatz gezählt.

---

## Ergänzung PR11.1 – Vollständiger Browserlauf am 30.10.2026

**FULL_BROWSER_REGRESSION_PASSED: 31/31 in einem einzigen neuen vollständigen
Standalone-Lauf.** Frontend-Lint, Typecheck und Build sind zuvor erfolgreich
abgeschlossen. Das bestehende Setup wurde wiederverwendet; fachliche
Bewertungs-/Idempotenzassertions bleiben erhalten. Testmodus und temporäre
Rollen sind danach zurückgesetzt. Neue tatsächliche Belege und die gesonderte
Kontrolle der Collector-/Forward-Schalter stehen im
[PR11.1-Verifikationsbericht](PR11_FINAL_VERIFICATION.md).

Der vorherige Bericht bleibt datiert richtig: Am 29.10. waren es zunächst
30/31 und danach der gezielte korrigierte Fall mit 1/1. Beide ursprünglichen
Läufe und der nachgewiesene Synchronisationsfehler bleiben erhalten. Erst der
hier ergänzte tatsächliche Gesamtlauf begründet die neue 31/31-Aussage.

Eine unabhängige Person wurde weiterhin nicht beobachtet. **PENDING_USER_TEST**
bleibt bestehen; automatische Browserfälle sind keine menschliche Bedien-
oder echte Android-/VPN-Zielabnahme. Das vorhandene PR7-Protokoll, die Suche
nach Einstellungen vor dem Logout und die
[konkrete Operatorübergabe](PRIVATE_CORE_V1_OPERATOR_HANDOVER.md) bleiben der
nächste reale Schritt. Kein neues Design oder synthetisches Testarchiv wurde
als Ersatz begonnen.

Die [tatsächliche Read-only-Nachkontrolle](security/pr11-1-20261030/source-registry-readonly.json)
bestätigt danach deaktivierte Collection/Forward-Schalter und Testmodus,
leere temporäre Operatorlisten sowie ECB/OpenFIGI weiterhin UNKNOWN und aus.
Die [Settingsproben der vier Dienste](security/pr11-1-20261030/runtime-settings-reset.json)
prüfen deren Containerumgebung über denselben Settingscode in Kindprozessen;
sie behaupten keine Inspektion des Speichers laufender Prozesse.

Der 31/31-Browserbefund bleibt an seinen tatsächlich geprüften Stand gebunden.
Die während des Auftrags hinzugekommenen Nutzercommits bis `64f7445b4aef10a7b7dabe6a9a62dd051a53d1a1`
ändern OpenShift-PVC-Konfiguration, nicht die geprüften Anwendungsimagebytes.
Ihre [neue lokale Renderprüfung](security/pr11-1-20261030/gitops-demo-offline-v2.json)
ist kein neuer Browserlauf und keine reale Cluster-/Bedienabnahme.

Der nun vollständige [PR11.1-Regressionsbeleg](security/pr11-1-20261030/regression-final.json)
bindet den neuen 31/31-Gesamtlauf, 210 nach den PVC-Änderungen erneut bestandene
Hosttests und die tatsächlichen Backend-/Restoreprüfungen. Zusätzlich bestätigt
der [neue HEAD-CI-Beleg](security/pr11-1-20261030/head-ci-final.json) den Lauf
41021964813 auf `64f7445…` mit 321/210/31. Sein vollständiger Core-/Recoveryaudit
war nicht angefordert. Diese technischen Nachweise ersetzen weiterhin keine
unabhängige Person oder echte Ziel-/Portfolioabnahme.
