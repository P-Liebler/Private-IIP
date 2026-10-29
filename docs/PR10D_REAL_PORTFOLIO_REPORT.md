# PR10D – Erster privater Portfolio-Pilot

Stand **29.10.2026**: **REAL_PORTFOLIO_NOT_VERIFIED / ORIGINALS_NOT_PROVIDED**.
Securityfreigabe, abgenommener privater Zielbetrieb und unabhängige Recovery
liegen weiterhin nicht vor. Der Nutzer hat für PR9 lokale Vorbereitung
beauftragt; PR10 enthält keine neue konkrete Host-/Quellenfreigabe und keine
privaten Brokeroriginale. Es wurden keine echten Depotdaten importiert.

## Kleiner verbindlicher Abnahmeumfang

Die erste fachliche Abnahme umfasst **ein echtes Portfolio und mindestens ein
echtes Konto** mit tatsächlichen Originaltransaktionen, belegten Positionen,
gültiger CHF-Bewertung, erklärtem Depotabgleich und geprüftem Backup/Restore.
Allgemeine weltweite Marktabdeckung ist dafür keine Voraussetzung. Ein
rechtmäßiger manueller Kurs-/FX-/Actions-Import ist zulässig; er beweist keine
automatische Liveversorgung. Prognosen und Empfehlungen bleiben gesperrt.

## Reihenfolge vor sensiblen Originalen

1. Separat autorisierte Securityentscheidung zum exakten Kandidaten einholen;
   offene Critical-/High-Befunde und Archiv-Recoveryvertrag tatsächlich entscheiden.
2. [Privaten Zielbetrieb und unabhängige Recovery](PR10B_TARGET_ACCEPTANCE_REPORT.md)
   einschließlich verschlüsselter Originalablage und getrennter Schlüssel abnehmen.
3. Eigenen echten Pilotbenutzer mit Login/TOTP und privaten Zugriffsrechten
   anlegen. Keine synthetische Testhistorie in diesen Benutzer kopieren.
4. Originale unverändert außerhalb Git/CI bereitstellen: Brokerexport,
   Transaktionshistorie, Bestandsauszug, Cash, Gebühren/Steuern, Dividenden/Splits,
   Kurs-/FX-Belege und eindeutiger Bewertungsstichtag mit Zeitzone.
5. ISIN **und** Listing/MIC/Handelswährung anhand vorhandener Belege klären.
   Mehrdeutigkeit ausdrücklich auflösen. Keine Börse aus einem Ticker vermuten.
6. Bestehende Importvorschau, Zuordnung und ausdrückliche Übernahme benutzen.
   Originalhash, Import-/Wiederholungsreceipt und Korrekturbezug privat bewahren.
7. Den folgenden Stichtagsabgleich vollständig durchführen; Abweichungen erst
   nach belegter Ursache korrigieren. Fehlende Inputs sperren betroffene Werte.

## Fachlicher Nachweisbogen

| Bereich | Erforderlicher Beleg | Aktueller Zustand |
| --- | --- | --- |
| Mengen / Käufe / Verkäufe | Konto, Listing, Bruchstücke, Datum und tatsächliche Ausführung gegen Ledger | NICHT VORGELEGT |
| Cash je Währung | Anfangssalden, externe Flüsse, negative Salden und Broker-FX | NICHT VORGELEGT |
| Gebühren / Steuern | Originalposten, Währung und explizite Postingpräzision | NICHT VORGELEGT |
| Dividenden / Splits | Ex-/Zahltag, Faktor, Coverage und einmalige Anwendung | NICHT VORGELEGT |
| Einstandswerte | Tatsächlicher Anschaffungsbeleg; Unbekanntes bleibt unbekannt | NICHT VORGELEGT |
| Kursstand | Konkretes Listing, Preisart, Quelle, Währung und gleicher Bewertungsstichtag | NICHT VORGELEGT |
| FX / CHF-Kreuzkurs | Tatsächliche Inputlegs, gleicher Referenztag, Herkunft und Frische | NICHT VORGELEGT |
| Gesamtwert CHF | Vollständige Inputs, nachvollziehbare Decimal-Rechnung und Brokerabgleich | NICHT VORGELEGT |
| Korrekturen / Voids | Neue Version, Originalreferenz und keine Wiederbelebung durch Retry | NICHT VORGELEGT |
| Backup / Restore | Dasselbe freigegebene Depot auf unabhängiger isolierter Infrastruktur | NICHT AUSGEFÜHRT |

Jede Differenz braucht private Originalreferenz, betroffene Ledger-/Inputversion,
Ursache, tatsächlich geprüfte Korrektur und erneuten Abgleich. Unterschiedliche
Bewertungszeiten oder Spreads sind Untersuchungsansätze, keine unbelegten
Erklärungen. Keine Ausgleichsbuchung und keine fehlenden Kurse/FX als Nullwerte.

## Grenze der technischen Nachweise

Die historische synthetische Goldenbewertung **CHF 10’180** gilt ausschließlich
am belegten Stichtag **26.10.2026 15:18:05.987683 UTC**. Derselbe alte Bestand
muss heute `STALE_PRICE` melden. Er ist kein echtes Depot und wird nicht durch
künstliche neue Kurse aufgefrischt. Die aktuelle technische Regression wird im
[PR10-Gesamtbericht](PR10_ACCEPTANCE_REPORT.md) separat nachgewiesen.

**`REAL_PORTFOLIO_VERIFIED=false`.** Es fehlen genau die tatsächliche
Security-/Ziel-/Recoveryfreigabe, private Originale und der ausgeführte,
belegte Stichtagsabgleich. Diese Voraussetzungen werden nicht durch weitere
synthetische Portfolios ersetzt.
