# Eigene Transaktionen importieren

Im Portfolio **Transaktionen → CSV-Transaktionen importieren** öffnen. Der Import nutzt denselben Decimal-Ledger wie manuelle Buchungen. Es gibt keine zweite Bewertungsengine und keine behaupteten offiziellen Brokerformate.

## Datei vorbereiten

Die Oberfläche bietet eine leere Kopfzeilenvorlage. CSV: **UTF-8, Komma als Trennzeichen, Datum `YYYY-MM-DD`, Dezimalpunkt**. Andere Spaltennamen sind möglich: in der Vorschau zuordnen. Einen semikolongetrennten Export ausdrücklich als Komma-CSV speichern; keine stillschweigende Annahme über Broker- oder Länderformate.

| Fachlicher Inhalt | Zielfeld | Wann benötigt |
|---|---|---|
| Buchungsart | `type` | Immer; BUY, SELL, DIVIDEND, INTEREST, DEPOSIT, WITHDRAWAL, FEE, TAX, TRANSFER_IN, TRANSFER_OUT, SPLIT, CASH_ADJUSTMENT oder OPENING_POSITION |
| Handels-/Buchungsdatum | `trade_date` | Immer; bei Startbestand Stichtag |
| Valuta | `settlement_date` | Optional, nicht vor Buchungstag |
| Instrument | ISIN, FIGI, Ticker oder `instrument_id` | Trades, Dividenden, Splits und Startpositionen; unklare Kennungen ausdrücklich auswählen |
| Stückzahl | `quantity` | BUY/SELL/OPENING_POSITION; bei SPLIT Verhältnis |
| Ausführungspreis | `price` | BUY/SELL; kein ausgedachter Preis für Startpositionen |
| Währung | `currency` | CHF, EUR oder USD; keine automatische Änderung bei falschem Instrument |
| Gebühr / Steuer | `fee`, `tax` | Absolute Beträge in Buchungswährung; keine Prozentangaben |
| Cashbetrag | `amount` | Cash-/Ertragsereignisse; BUY/SELL werden aus Menge und Preis abgeleitet. Bei OPENING_POSITION ausschließlich optionaler gesamter Einstand, kein Cashflow |
| Brokerreferenz | `external_id` | Wenn vorhanden verwenden; ermöglicht sichere Wiedererkennung |
| Konto | `account` | Optional; muss zum in der Oberfläche gewählten Konto passen |
| Herkunft | `notes` | Bei OPENING_POSITION Pflicht; sonst optional |

DIVIDEND enthält den belegten Bruttobetrag, Gebühren und Quellensteuer getrennt. Eine bereits manuell gebuchte Ausschüttung nicht zusätzlich automatisch anwenden. Cashkorrekturen und negative Cashbestände sind sichtbar; nicht als Lösung für ungeklärte Differenzen einsetzen.

## Vorschau und Bestätigung

1. Importkonto und Datei wählen, **Vorschau prüfen**.
2. Erkannte Spalten kontrollieren. Für unklare Instrumente lokal suchen und die richtige Börse/MIC, Währung und Kennung ausdrücklich wählen. Eine Auswahl kann widersprüchliche Originalkennungen nicht überstimmen.
3. Nach jeder Änderung **Vorschau erneut prüfen**. Das Original und der Vorschauvertrag bleiben gebunden.
4. Datum, Instrument, Stückzahl, Preis, Betrag, Kosten, Duplikate und Fehler prüfen. Keine Buchung wurde bisher übernommen.
5. Bestätigung setzen und **Import übernehmen**. Fehler verhindern den vollständigen Commit; Duplikate werden übersprungen.

Wiederholter Import erzeugt keine erneute Buchung. Ohne externe Referenz erfolgt der Vergleich anhand der Buchungsfelder; zwei tatsächlich gleiche Einzelorders benötigen unterschiedliche belegte Referenzen. Eine vorhandene externe ID mit anderen Buchungswerten ist ein Konflikt. Unter **Buchungen → Korrigieren** ausdrücklich korrigieren: ursprüngliche/stornierte Versionen bleiben nachvollziehbar. Ein späterer Import der alten Datei darf sie nicht reaktivieren.
