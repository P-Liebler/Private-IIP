# PR9D – Echter Portfolio-Pilot und unabhängige Benutzerabnahme

Stand **28.10.2026**: **REAL_PORTFOLIO_PILOT_PENDING / PENDING_USER_TEST**. Ein Zielhost, private Depotoriginale und eine unabhängige Testperson wurden weiterhin nicht bereitgestellt. Es werden keine Personen, Finanzdaten oder Benutzererfolge erfunden. Die bisherige Entscheidung „Zielhost noch nicht verfügbar; lokal vorbereiten“ bleibt gültig; eine neue Host- oder Liste bestimmter ISIN wird hier nicht verlangt.

## Vorbereitung ist vorhanden, reale Abnahme steht aus

Das bestehende Designsystem und die Portfolio-/Import-/Quellen-/Abgleichfunktionen bleiben der Arbeitsweg. PR9 bereitet Installation, tatsächliche Holdings-Aktualisierung und Quellenentscheidungen konkreter vor. Neue grundlegende UX-Architektur oder Investmentmodelle sind kein Gegenstand dieser Phase.

Automatisierte Tests verwenden eigene ausdrücklich synthetische Benutzer und die lokale API. Die ursprüngliche PR9-Browserbaseline erreichte 29/30; der endgültige gesamte Standalone-Lauf besteht **31/31**. [Tatsächliche technische Belege](PR9E_RELEASE_CANDIDATE_REPORT.md). Weder ein später erfolgreicher Browserlauf noch eine synthetische Goldenbewertung wird als menschliche Bedienbarkeitsprüfung oder realer Brokerabgleich bezeichnet.

## Aufnahme eines echten Depots

Vor sensiblen Originalen müssen separate Security- und Zielhostfreigaben des exakten Kandidaten vorliegen. Danach führt der Operator diese vorbereitete Reihenfolge aus:

1. Eigenen tatsächlichen Pilotbenutzer mit geprüftem Login/TOTP, passenden privaten Konten und sicherem Zugriff anlegen. Keine E2E-Fixtures in diesen Benutzer kopieren.
2. Transaktionshistorie einschließlich Anfangsbeständen, Gebühren, Steuern, Dividenden, tatsächlicher Broker-FX, Konto-/Währungszuordnung und Stornierungen privat sichern. Originale, Kennungen, Screenshots und personenbezogene Abnahmeprotokolle bleiben außerhalb von GitHub/CI.
3. Einen tatsächlichen Depotauszug mit eindeutigem Bewertungsstichtag und Zeitzone bereitstellen. Instrumente anhand von ISIN **und konkretem Listing/MIC/Handelswährung** zuordnen; Mehrdeutigkeit vor dem Commit klären.
4. Rechte und tatsächliche Quellen-/Listing-/Zeitraumabdeckung für Kurse und FX dokumentieren oder rechtmäßig verfügbare manuelle Originalexporte verwenden. ECB-Referenzkurse ersetzen keine Broker-Ausführungskurse. Fehlende Actions-/Kurs-/FX-Intervalle bleiben offen.
5. CSV-Vorschau und Mapping kontrollieren, anschließend ausdrücklich übernehmen. Rohoriginal, Hash, Commit-/Wiederholungsreceipt und spätere Korrekturversion erhalten. Keine Originaldatei durch eine bereinigte Fassung ersetzen.
6. Vor automatischer Aktualisierung den [Quellenablauf](PR9C_REAL_DATA_ENABLEMENT_REPORT.md) mit initialem und einem tatsächlich späteren Livezeitpunkt vollständig prüfen. Kein unbelegter Wechsel auf einen anderen Provider.

## Reconciliation am selben Stichtag

Für jeden Punkt die tatsächlichen Original- und Ledgernachweise privat referenzieren. Ein geöffnetes Formular oder eine technische Importantwort gilt nicht als finanzieller Abgleich.

| Prüfpunkt | Erforderlicher tatsächlicher Nachweis | Zustand |
| --- | --- | --- |
| Mengen | Pro Konto und Listing Brokerbestand gegen Ledgerposition, inklusive Bruchstücken und Shorts | AUSSTEHEND |
| Cash | Jede Währung und negative Salden separat, Ein-/Auszahlungen vollständig | AUSSTEHEND |
| Gebühren und Steuern | Originalposten, Währung, Datum und Postingpräzision gegen Buchung | AUSSTEHEND |
| Käufe/Verkäufe und Korrekturen | Tatsächliche Ausführung, historische Korrektur-/Voidversionen, keine Wiederbelebung durch Retry | AUSSTEHEND |
| Dividenden | Brutto/netto, Steuer, Währung, Ex-/Zahltag und einmalige Buchung | AUSSTEHEND |
| Splits | Faktor, Effektivdatum, angepasste Menge/Einstand und explizite Actioncoverage | AUSSTEHEND |
| Kurse | Roh/adjustiert getrennt, konkretes Listing, Datum, Quelle und Gültigkeit | AUSSTEHEND |
| FX | Brokertransaktion gegen Referenzbewertung unterscheiden, Inputlegs/Datum/Carry sichtbar | AUSSTEHEND |
| Einstandswerte | Übertragene Anschaffungskosten nur mit Beleg; unbekannt bleibt unbekannt | AUSSTEHEND |
| Gesamtportfolio CHF | Gleicher Bewertungsstichtag, nachvollziehbare Rundungsregeln und vollständige Bewertungsgrundlagen | AUSSTEHEND |

Jede Brokerdifferenz erhält Originalreferenz, betroffene Buchung/Version, Ursache und tatsächlich geprüfte Korrektur. Unterschiedliche Bewertungszeitpunkte, Spreads oder aufgelaufene Gebühren sind mögliche Untersuchungsansätze, keine ohne Beleg akzeptierten Erklärungen. Keine erfundenen Ausgleichsbuchungen und keine Datenänderung, um einen gewünschten Gesamtwert zu erreichen. Fehlende Belege lassen den jeweiligen Abgleich offen.

## Unabhängiger Anfänger-Test

Das vorhandene [PR7-Aufgabenblatt und Beobachtungsprotokoll](ux/PR7_BEGINNER_TEST.md) wird wiederverwendet. Es enthält tatsächliche Aufgaben für Anmeldung, Portfolio/Konto, Importvorschau, Position, Bewertungsverständnis, Kurslücke, Korrektur, Quellen-/Datenalterstatus und Abmeldung. Zusätzlich vorhandene Einstellungen und mobile Navigation beobachten.

Solange Security/Host nicht abgenommen sind, verwendet die tatsächliche Testperson ausschließlich den vorbereiteten isolierten **synthetischen** Testaccount. Eine menschliche UX-Abnahme mit synthetischen Daten wäre eine echte Bedienbarkeitsbeobachtung, aber weiterhin keine reale Portfolioabnahme. Vorab keine Einführung geben; Hilfen, Fehlklicks, unklare Begriffe, Abbrüche und tatsächliche Dauer aufzeichnen. Anschließend die beobachteten gravierenden Probleme gezielt beheben und mit der Person erneut prüfen.

Aktuell wurde niemand beobachtet. Daher gibt es keine Erfolgsquote, Dauer oder fingierte Problemliste. Die technische Browserabweichung ist als automatisierter Testbefund eingeordnet. Jede wesentliche Hauptaktion muss im finalen technischen Lauf tatsächlich funktionieren; menschliche Verständlichkeit bleibt separat zu beurteilen.

## Konkrete nächste Operatoraktionen

1. Nach abgeschlossenem lokalem Kandidaten getrennte Security-/Host-/Operatorentscheidungen zum exakten Manifest erfassen und Zielzugang abnehmen.
2. Rechtmäßige private Depotoriginale außerhalb des Repositorys bereitstellen; eigenen Pilotaccount und Stichtag festlegen.
3. Den obigen Import-/Reconciliationablauf vollständig mit tatsächlichen Nachweisen ausführen; offene Differenzen sichtbar belassen.
4. Eine tatsächlich unabhängige Person terminieren und das bestehende Aufgabenblatt ohne Einführung durchführen. Protokoll privat bewahren, nur anonymisierte Ergebnisse zusammenfassen.

`REAL_PORTFOLIO_PILOT_STATUS=REAL_PORTFOLIO_PILOT_PENDING`. `UX_USER_TEST_STATUS=PENDING_USER_TEST`. [Gesamtstatus und weitere offene Gates](PR9_ACCEPTANCE_REPORT.md).
