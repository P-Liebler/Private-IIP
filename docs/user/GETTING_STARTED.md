# Portfolio einrichten

Stand: 22.10.2026. Der lokale Beta-Workflow ist in Abnahme. **Echte private Finanzdaten sind noch nicht freigegeben.** Zunächst nur ausdrücklich synthetische Dateien verwenden. Die Erstinstallation, Benutzeranlage und spätere Security-/TLS-/Backupfreigabe übernimmt der Betreiber nach dem [Deploymentleitfaden](../operations/DEPLOYMENT_GUIDE.md).

## Ihr erster Ablauf

PR6 ergänzt unter **Portfolio → Portfolio anlegen** einen geführten Ablauf: Portfolio, Konto, optionales Cash, Transaktionsdatei, Kurse/FX und Bewertungsprüfung. Optionale Schritte lassen sich überspringen. Der bestehende manuelle Ablauf darunter bleibt verfügbar. Einzelbuchungen werden vor Übernahme bestätigt. Bei unklarem Netzwerkabschluss denselben Vorgang mit seinem erhaltenen Anfrageparameter wiederholen; ein neuer Schlüssel bezeichnet eine neue beabsichtigte Buchung. [Ausführliche Nutzerwege](../ux/USER_JOURNEYS.md).

1. Privat anmelden und **Portfolios verwalten** öffnen.
2. Einen Namen vergeben, **CHF** als Basiswährung wählen und erstellen. Die Basiswährung gehört zum Bewertungsvertrag; einen versehentlich falsch gewählten leeren Testbestand neu anlegen.
3. Das Portfolio öffnen. **Portfolio einrichten → Konto einrichten** führt zur Konto-/Depotanlage. Konten können mehrere unterstützte Währungen enthalten.
4. Vorhandenes Cash als belegten **DEPOSIT** zum gewählten Startpunkt erfassen. Bei fehlender Kaufhistorie eine **OPENING_POSITION** mit Stichtag, Instrument, Währung, Stückzahl und Herkunft erfassen. Optional den gesamten bekannten Einstandswert eingeben; unbekannte Kosten leer lassen. Das ist kein historischer Kauf und verbraucht kein Cash.
5. Über **CSV-Vorschau öffnen** rechtmäßige eigene Transaktionen importieren. Erst das Konto, dann Spalten und Instrumente prüfen und die Übernahme ausdrücklich bestätigen. [Transaktionsimport](IMPORT_TRANSACTIONS.md).
6. **Instrumente** prüfen: ISIN/FIGI, Börse/MIC, Währung und Typ. Einen Ticker nicht allein als sichere Identität behandeln. Ein mehrdeutiger Treffer benötigt eine bewusste Auswahl; widersprüchliche Kennungen bleiben gesperrt.
7. Belegte Kurse und tägliche FX-Referenzen unter **Kurs- oder FX-Datei importieren** übernehmen. [Marktdatenimport](IMPORT_MARKET_DATA.md).
8. **Datenqualität** öffnen, fehlende Daten bearbeiten und unter **Depotabgleich** mit dem Auszug vergleichen. [Abgleich](PORTFOLIO_RECONCILIATION.md).
9. Unter **Übersicht** Gesamtwert, Cash, Positionen, Erträge und Bewertungsdatum prüfen. Allokation und Performance sind eigene Bereiche. Historische Renditen benötigen vollständige Daten und nachgewiesene Corporate Actions.

## Was unbekannt bleibt

`PARTIAL` bedeutet, dass kein vollständiger Portfoliowert behauptet wird. Bekannte Teilwerte sind keine Ersatzsumme. Unbekannter Einstand erzeugt weder Nullkosten noch einen erfundenen Gewinn. Ein Startbestand ersetzt keine nachgewiesene frühere Kaufhistorie; Gesamtrenditen über diesen Beginn bleiben unbekannt. Kursstände sind Tages-Schlusskurse und keine handelbaren Livepreise.

P7 bleibt SHADOW, P9-Empfehlungen gesperrt. Das LLM darf fehlende Werte nicht ergänzen. Ohne Quellenfreigabe funktionieren manuelle zulässige Originale; automatische tägliche Aktualisierung ist dadurch nicht abgenommen.

Die spätere [echte Pilotabnahme](REAL_PORTFOLIO_PILOT.md) wird gesondert ausgelöst. Sie darf keine synthetischen Tests als reale Portfolioverifikation ausweisen.
