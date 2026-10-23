# PR5B – Portfolio-Workflow

Prüfdatum: 22.10.2026. **Technisch implementiert; Echtdaten-Pilot nicht abgenommen.**

## Umsetzung

Der achtteilige Einstieg verbindet Portfolio, CHF-Basiswährung, Konten, Startbestand, CSV, Instrumentenprüfung, Kurse/FX, Datenqualität und Auszugsvergleich. Sämtliche Buchungen verwenden den bestehenden P4-Ledger; es gibt keine zweite Bewertungs- oder Importengine und keine neue Datenbanktabelle.

Die generische UTF-8-CSV unterstützt frei zugeordnete Spalten für Handels-/Valutadatum, Typ, Kennungen, Menge, Preis, Währung, Betrag, Gebühren, Steuern, externe Buchungs-ID und Herkunft. Das Importkonto wird ausdrücklich ausgewählt. Komma, ISO-Datum und Dezimalpunkt sind dokumentierte Eingabevoraussetzungen; es wird kein offizielles Brokerformat behauptet.

Die Vorschau zeigt geparste Werte, Fehler, Duplikate und aufgelöste Instrumentnamen. Mehrdeutige Kennungen brauchen eine bewusste Auswahl, die weiterhin allen datierten CSV-Kennungen entsprechen muss. Eine geänderte Zuordnung verlangt eine neue Vorschau. Originalbytes werden vor der Verarbeitung archiviert; ein Hash bindet Mapping und Auswahl an die Vorschau. Die Oberfläche fordert die ausdrückliche Buchungsbestätigung.

Commit und Wiederholung prüfen unter Portfoliosperre bestehende externe IDs und Fingerprints, einschließlich korrigierter/voidierter Originale. Gleiche Daten werden übersprungen, abweichende Werte unter gleicher externer ID abgewiesen. Korrekturen verwenden die vorhandene versionierte Korrekturfunktion; ein alter Import reaktiviert keine voidierte Buchung.

## Startbestand und Rechnungslegung

`OPENING_POSITION` ist eine explizite Stückzahl mit Stichtag, Instrumentwährung und belegbarer Herkunft, ohne erfundenen Kaufpreis oder Cashflow. Der optionale Betrag bezeichnet den gesamten bekannten Einstand. Leer bedeutet unbekannt: Durchschnittskosten, betroffene Gewinne und historische Renditen bleiben unverfügbar. Ein nachweisbarer aktueller Marktwert darf trotzdem angezeigt werden. Der Startbestand muss vor der weiteren Positionshistorie liegen. Bestehende Decimal-Präzision, Gebühren, Steuern, Splits, Dividenden und Korrekturen bleiben maßgeblich.

Der neue Depotabgleich liest denselben Ledger und dieselbe Bewertung. Er vergleicht manuell eingegebene Auszugswerte für ein Konto und Datum. Nicht eingegebene Werte werden nur bei ausdrücklich als vollständig bezeichnetem Auszug als fehlende Position/Cash behandelt. Veraltete oder fehlende Bewertungsdaten verhindern einen vollständigen Wertvergleich. Ergebnis enthält Eingabehash, Wissenszeitpunkt und Transaktions-IDs; es verändert keine Buchung. `MATCHED_ENTERED_FIELDS` bestätigt nur die eingegebenen Felder, keine Echtheit eines Brokeroriginals. Die manuelle Vergleichseingabe wird nicht dauerhaft gespeichert.

## Nachweise und Grenzen

281 Backendtests bestanden, einschließlich elf neuer Accountingfälle und eines transaktional isolierten API-Ablaufs. Neue Fälle prüfen unbekannten Einstand, Verkauf, Gebühren/Steuern, Split/Dividende, ungültige Startbestände, Kennungskonflikte, erneuten Import, Korrekturen und stale Bewertung. Der API-Abgleich ergibt im gekennzeichneten Testfall CHF 503; dies sind ausschließlich synthetische Rechenbeispiele.

Der neue Browserfall prüft zusätzlich Onboarding, gleiche Ticker an unterschiedlichen MICs, bewusste Zuordnung, Wiederholungsimport, manuelle Kurse/FX, CHF-Bewertung, Auszugsvergleich und unbekannten Startbestand. Sein finaler Lauf wird im [Abnahmebericht](PR5_ACCEPTANCE_REPORT.md) festgehalten.

Es fehlen echte private Belege und der unabhängige Brokervergleich. Ein ausgefüllter manueller Vergleich ist kein Ersatz dafür. [Pilotanleitung](user/REAL_PORTFOLIO_PILOT.md).
