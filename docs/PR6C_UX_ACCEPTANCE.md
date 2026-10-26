# PR6C – Einrichtung und Import

Abgleich 26.10.2026. **LOCALLY_TESTED / PENDING_USER_TEST**. Vollständige Regression vom 23.10.; reale Depotabnahme weiterhin offen.

## Implementiert

`/portfolios/new` führt durch Portfolio, Konto, optionales Startguthaben, CSV-Buchungen, Marktdaten und Bewertungsprüfung. Fortschritt verweist im URL auf bereits gespeicherte eigene Ressourcen; keine Finanzentwürfe oder Authentifizierungstokens im Browserstorage. CHF ist voreingestellt. Cash und Importe können übersprungen werden. Besitzrechte und Ledgerprüfung liegen weiterhin im bestehenden Backend.

Der Transaktionsimport unterstützt UTF-8/BOM, eindeutige Komma-/Semikolon-/Tabulatorformate sowie explizite ISO-/Tag-Monat-/Monat-Tag- und Zahlenformatwahl einschließlich Schweizer Apostrophgruppierung. Mehrdeutige Daten verlangen eine neue Vorschau mit bestätigtem Format. Ungültige Gruppierungen werden verworfen. Originalbytes werden vor Erkennung/Parsing archiviert. Der Planhash bindet Format, Spalten und Instrumententscheidungen; der alte Hashvertrag ohne Format bleibt unverändert.

## Tatsächliche Nachweise

- Neuer API-Integrationstest: BOM/CH-Datei, Formatwahl, Datumsinterpretation 01/02 als 1. Februar bei DMY, exakte Dezimalzahl, Formatänderung beim Commit abgewiesen, kein Ledgerwrite bei Ablehnung, wiederholter Commit ohne Duplikat.
- Bestehender PR5-Import-/Korrektur-/Startbestands-/Abgleich-Integrationstest mit neuem Parser bestanden.
- Zwei neue Browserfälle gegen einen abgeschlossenen Standalone-Build bestanden: Navigation/Themes auf 360/390/768/1024/1440/1920 einschließlich Tastaturdialog sowie tatsächlicher Wizard mit CH-Datei und kontrolliertem Ledgerwert. Diese ersten Screenshots enthalten noch das frühere Dashboard; sie ersetzen keine finale visuelle Abnahme des neueren Gesamtstands.
- Ergänzende Unitfälle für mehrdeutige Formate, Gruppierung und Hashbindung bestanden.

## Wiederholungsschutz und Abnahmegrenzen

Einzelbuchungen besitzen einen Reviewdialog, Stornierungen eine ausdrückliche Bestätigung. Portfolio-/Kontoanlage nutzen atomare append-only Wiederholungsbelege (`0021_ui_requests`); Einzelbuchungen verwenden stabile UUID-Anfrageschlüssel. Schlüssel bleiben bei unklarem Netzwerkabschluss sowie Tab-/Schrittwechsel im URL erhalten. Ein verändertes Payload mit bereits abgeschlossener Anfrage wird abgewiesen. Wiederholung einer stornierten Buchung liefert deren alten Zustand und legt keine neue Buchung an. API-Integrationstests bestätigen diese Verträge. CSV-Übernahmen behalten ihre bestehende Duplikatkontrolle.

Die 26 unterschiedlichen Browserfälle sind bestanden (25 im finalen Gesamtlauf, der korrigierte Chart-/Theme-Selektor gezielt nachgeprüft, gleicher Anwendungsbuild). Geführtes Portfolio, CH-Import, Instrumentzuordnung, Bestätigung, FX-Bewertung, Provenienz, Depotabgleich, Startbestand und Datenqualitätsaktion sind im beschriebenen synthetischen Umfang verbunden. Ein zusätzlicher Normalmodus-Sichtlauf am 26.10. auf 390/1440 px verlief ohne Seitenfehler oder finanzielle Mutation. Nicht jede mögliche Form-/Netzwerkfehlerkombination ist browserseitig injiziert worden. Externe Anfängertests: **PENDING_USER_TEST**. Kein realer Brokerexport und keine reale Depotabnahme wurden geliefert. [Nutzerwege](ux/USER_JOURNEYS.md).
