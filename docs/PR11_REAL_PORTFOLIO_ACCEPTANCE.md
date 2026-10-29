# PR11E – Erste reale Portfolioabnahme

Stand **29.10.2026**. **REAL_PORTFOLIO_PILOT_PENDING**.
Es liegen weder ein abgenommener sicherer Zielbetrieb noch echte private
Brokeroriginale vor. Eine tatsächliche Depotanlage, ein Brokerabgleich oder
ein unabhängiger Restore echter Depotdaten wurde nicht ausgeführt.

## 1. Voraussetzungen und Übergabe

Ein echtes Portfolio mit mindestens einem tatsächlichen Konto genügt für den
ersten begrenzten Pilot. Zulässige manuelle Markt-/FX-/Actions-Originale sind
ein vollwertiger Datenweg; sie belegen keine automatische Liveversorgung.
Prognosen und Empfehlungen bleiben unabhängig gesperrt.

| Entscheidung | Handlung | Wer autorisiert? | Geschützte Eingaben | Erfolg | Bis dahin gesperrt |
| --- | --- | --- | --- | --- | --- |
| Sichere Aufnahme echter Originale | Exaktes Release, privaten Zielbetrieb und unabhängige verschlüsselte Recovery gemäß [Releasecheckliste](PR11_CORE_RELEASE_CHECKLIST.md) abnehmen | Securityreviewer, Ziel-/Backupbetreiber und Depotinhaber | Tatsächliche Manifest-/Ziel-/Recoverybelege, getrennte Schlüssel | Eigener privater Zugriff, gültige Freigaben und ausgeführter isolierter Recoverylauf | Upload echter Originale und realer Pilot |
| Privater Benutzer | Eigenen Benutzer mit Login/TOTP und Eigentumsgrenzen einrichten | Depotinhaber / autorisierter Benutzeroperator | Zugangsdaten und TOTP ausschließlich privat | Login, Fehlversuch, Logout/Sessionwiderruf und fremde Eigentumsgrenze geprüft | Nutzung eines synthetischen QA-Benutzers als echtes Depot |
| Belegte Depoterfassung | Unveränderte echte Exporte bereitstellen, Identitäten klären, bestehende Importvorschau und ausdrücklichen Commit nutzen | Depotinhaber und autorisierter Importoperator | Brokertransaktionen, Bestands-/Cashauszug, Gebühren/Steuern, Actions, Kurs-/FX-Belege und Stichtag | Raw-Hash, Mapping, Ledger-/Korrektur-/Retryreceipts privat vollständig | `REAL_PORTFOLIO_VERIFIED` |
| Fachlicher Abgleich | Alle unten genannten Bereiche am selben Stichtag vergleichen und Differenzen belegen | Fachlicher Prüfer / Depotinhaber | Private Originalreferenzen, tatsächliche Posting-/Bewertungsversionen | Jede Differenz nachvollzogen; fehlende Inputs sichtbar gesperrt | Unbelegte CHF-Gesamtbewertung oder Ausgleichsbuchung |
| Reale Wiederherstellung | Genau dieses Depot unabhängig sichern und in neuen isolierten Volumes restaurieren | Backupoperator und Depotinhaber | Vollsatz, Originalhashes, getrennte Secrets-/CA-/TOTP-Recovery | Gleiche Ledger-/Original-/Archivhashes und gleiche belegte Stichtagsbewertung, Login wiederhergestellt | Abschluss des echten Piloten |

Private Finanzoriginale und personenbezogene Depotprotokolle gehören nicht
in GitHub oder CI. Ein öffentlicher Bericht enthält nur zulässige redigierte
Statusangaben, Evidenzhashes und Entscheidungsbezüge.

## 2. Tatsächlich auszuführender Stichtagsabgleich

1. Bewertungsstichtag einschließlich Zeitzone, Konto-/Depotumfang und
   Originalexporte festhalten. Keine synthetische QA-Historie übernehmen.
2. ISIN **und** tatsächliches Listing/MIC, Handelswährung, Instrumenttyp und
   Gültigkeitszeitraum prüfen. Keine Börse aus dem Ticker vermuten; ungeklärte
   Zuordnung vor dem Commit auflösen.
3. Originale unverändert speichern, SHA-256/Raw-ID sichern, Vorschau und
   explizite Zuordnung prüfen, danach übernehmen. Identische Wiederholung darf
   keine zweite Buchung erzeugen. Korrekturen/Voids bleiben auditierbar.
4. Die folgende Tabelle mit echten privaten Belegen abschließen.

| Abgleich | Erforderlicher konkreter Nachweis | Aktuell |
| --- | --- | --- |
| Positionen | Mengen und Bruchstücke, Kauf/Verkauf, echtes Listing, Ausführungsdatum und Konto gegen Ledger | NICHT VORGELEGT |
| Cash | Anfangssalden, externe Flüsse, negative Beträge und Cash je Währung | NICHT VORGELEGT |
| Gebühren / Steuern | Originalposten, Währung und nachvollziehbare Decimal-/Postingpräzision | NICHT VORGELEGT |
| Broker-FX | Tatsächliche Umtauschbuchungen, Gebühren und Spreads gegen Brokerbeleg | NICHT VORGELEGT |
| Dividenden / Splits | Ex-/Zahltag, Faktor, instrument-/intervallspezifische Coverage, genau einmal angewandt; keine manuell/kanonische Doppelzählung | NICHT VORGELEGT |
| Einstand | Tatsächlicher Anschaffungsbeleg; unbekannter Einstand bleibt unbekannt | NICHT VORGELEGT |
| Preise | Unadjustierter Kurs, Quelle, Listing, Währung, tatsächlicher Zeitpunkt, Frische und Konfliktstatus | NICHT VORGELEGT |
| Bewertungs-FX | Original-/Leg-IDs, Quelle, richtiger Referenztag und Richtung; ECB-Kreuzkurs nach [Quellenabnahme](PR11_LIVE_SOURCE_ACCEPTANCE.md) | NICHT VORGELEGT |
| CHF-Gesamtwert | Vollständige Datenbasis und nachvollziehbare Rechnung gegen den gleichzeitigen Brokerstand | NICHT VORGELEGT |
| Korrektur und Restore | Belegte neue Version, erneuter Abgleich und echtes unabhängiges Backup/Restore mit erhaltenen Originalen | NICHT AUSGEFÜHRT |

Jede Abweichung braucht betroffene Original-/Ledger-/Inputversion, belegte
Ursache, konkrete Korrektur und neuen Abgleich. Unterschiedliche Kurszeiten,
FX-Referenzen oder Spreads sind zunächst zu prüfende Möglichkeiten, keine
erfundene Erklärung. Keine fehlenden Preise/FX als Null und keine unbelegte
Ausgleichsbuchung. Fehlende Actionscoverage sperrt die betroffenen Metriken.

## 3. Technische Goldenprüfung ist kein reales Depot

Das historische synthetische Goldenportfolio bleibt **CHF 10’180 ausschließlich
am 26.10.2026 um 15:18:05.987683 UTC**. Am heutigen Datum veraltete Kurse
bleiben `STALE_PRICE`; sie werden nicht künstlich aktualisiert. Die zwei
PR10-Restores mit je 1’387 Dateihashes sind historische technische Evidenz,
keine unabhängige Wiederherstellung eines echten Nutzerdepots. Neue technische
PR11-Ergebnisse werden im [Gesamtbericht](PR11_ACCEPTANCE_REPORT.md) getrennt
ausgewiesen.

**`REAL_PORTFOLIO_VERIFIED=false`.** Nach Abschluss der lokal lösbaren Arbeit
warten die konkret benannten Freigaben, sichere Infrastruktur und tatsächlichen
Originale. Weitere synthetische Pilotdepots schließen dieses Gate nicht.
