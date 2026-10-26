# Nutzerwege und Abnahmegrenzen

Stand: 23.10.2026. Finanzwerte in automatisierten Nachweisen sind ausschließlich isolierte Testdaten. Der unabhängige Test durch eine unerfahrene Person steht aus: **PENDING_USER_TEST**.

## Erstes Portfolio

1. Anmelden und unter **Portfolio → Portfolio anlegen** den geführten Ablauf öffnen.
2. Namen und Berichtswährung bestätigen; CHF ist voreingestellt. Danach ein eigenes Konto wählen oder anlegen.
3. Optional Startguthaben eingeben und ausdrücklich bestätigen. Bei unsicherem Netzwerkabschluss dieselbe Anfrage wiederholen; den Anfrageparameter im URL erhalten. Ein neuer Schlüssel ist eine neue beabsichtigte Buchung.
4. Optional eine UTF-8-CSV hochladen. Vorschau lesen, Spalten und Instrumente bestätigen. Bei uneindeutigem Datum/Zahlenformat zunächst die explizite Interpretation wählen und die Vorschau erneut erstellen.
5. Zulässige Kurse, tägliche FX und Kapitalmaßnahmen über den bestehenden Importpfad ergänzen. Eine ISIN allein bestimmt weder Börse noch Handelswährung; mehrdeutige Zuordnungen müssen geprüft werden.
6. Bewertung prüfen. Fehlende oder veraltete Daten über die konkreten Hinweise bearbeiten. Ein bekannter Teilwert ist kein vollständiger Depotwert.

Portfolio- und Kontoanlage besitzen atomare Wiederholungsbelege. Einzelbuchungen und CSV-Übernahmen werden serverseitig gegen Duplikate geschützt. Bereits stornierte Buchungen werden durch Wiederholung nicht reaktiviert. Korrekturen erhalten ihre Historie.

## Datenlücke bearbeiten

Von **Übersicht** oder **Portfolio** dem Hinweis zu Kurs, FX oder Kapitalmaßnahme folgen. Datum und betroffene Position prüfen. Ein technischer Adapter ist erst nach genehmigter, aktivierter und sachlich passender Quelle nutzbar. Ohne Freigabe bleibt der manuelle Import mit vorhandenen Rechten der Ersatzweg. Monatliche Referenz-FX ersetzt keine tägliche Bewertungs-FX.

## Position verstehen

In der Positionstabelle suchen/sortieren und **Details** öffnen. Instrument, Menge, Kursdatum, Bewertungsstatus und Herkunft vergleichen. Fehlender Einstand bedeutet unbekannten Gewinn. Der vorläufige Positionsvergleich ist keine Tagesrendite oder Empfehlung. Auf Mobilgeräten stehen dieselben Angaben in beschrifteten Karten.

## Analysieren

**Analysen** führt zu Risiko, Szenarien und What-if eines eigenen Portfolios. Gespeicherte Risikoergebnisse bleiben unverändert. Rendite/Drawdown werden nur aus vollständigen gespeicherten Beobachtungen angezeigt; eine fehlende Benchmark wird als fehlend bezeichnet. What-if verändert das Buchungsjournal nicht. Prognosen und Empfehlungen benötigen weiterhin eigene fachliche Freigaben.

## Dokument zurückziehen

Unter **Aktivitäten → Dokumente** das eigene Dokument entfernen und den Aufbewahrungshinweis bestätigen. Es verschwindet aus aktiver Bibliothek und neuen Suchabrufen einschließlich historischer Suche. Originale und frühere Belege bleiben für die Nachvollziehbarkeit erhalten; dies ist keine physische Löschung.

## Assistent und Ausfälle

Der lokale Assistent erklärt vorhandene, freigegebene Evidenz. Er erfindet weder Werte noch Quellen und erteilt keine Handels- oder Betriebsfreigabe. Ohne LLM bleiben Daten, Buchungen, regelbasierte Warnungen und Berichte unabhängig nutzbar. Fehlende Modelle oder Quellen sind keine positiven Analyseergebnisse.

## Darstellung und Rechte

Light/Dark/System in der Kopfzeile oder den Einstellungen wählen. Die Präferenz enthält keine Zugangsdaten. Auf schmalen Bildschirmen öffnet die Navigation als Tastaturdialog; Escape schließt sie und führt den Fokus zurück. Erweiterte Daten-/ML-/Betriebsseiten erscheinen abhängig von getrennten Rollen. Backend-Berechtigungen bleiben maßgeblich.

## Noch erforderliche echte Abnahmen

- Fremder Anfängertest mit dokumentierten Aufgaben, Erfolgen und Schwierigkeiten.
- Zulässiger echter Brokerexport und reale Instrument-/FX-/Action-Abdeckung.
- Genehmigter Liveabruf einschließlich Originalbytes, Canonical-Verknüpfung, Wiederholung und Frontendwert.
- Unabhängige Security-, Zielhost-, Backupzeitplan- und Schlüsselwiederherstellungsabnahme.
