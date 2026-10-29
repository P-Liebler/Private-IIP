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
